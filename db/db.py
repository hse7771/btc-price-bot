from datetime import datetime

import aiosqlite
import asyncio
import logging

DB_NAME = "db/database files/BTC_bot_data.db"
MAX_RETRIES        = 2          # 1 original try + 1 retry
LOCK_RETRY_DELAY   = 0.05       # seconds (50ms)

_DB: aiosqlite.Connection | None = None
_LOCK = asyncio.Lock()          # to serialise open/close

async def get_db() -> aiosqlite.Connection:
    global _DB
    async with _LOCK:
        if _DB is None:  # closed / crashed
            _DB = await aiosqlite.connect(DB_NAME)
            await _DB.execute("PRAGMA journal_mode=WAL;")  # keeps readers concurrent
            await _DB.execute("PRAGMA busy_timeout=2000;")  # 2 s write wait
        return _DB


async def init_db():
    db = await get_db()

    await db.execute('''
            CREATE TABLE IF NOT EXISTS currency_preferences (
                user_id INTEGER PRIMARY KEY,
                currencies TEXT  -- Stored as comma-separated values
            )
        ''')

    await db.execute('''
                CREATE TABLE IF NOT EXISTS base_subscribers (
                    user_id INTEGER,
                    interval_minutes INTEGER,
                    PRIMARY KEY(user_id, interval_minutes)
                )
            ''')

    await db.execute('''
                CREATE TABLE IF NOT EXISTS personal_subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    first_fire_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    await db.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    tier INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    await db.commit()


async def execute_write(db: aiosqlite.Connection, sql: str, params: tuple):
    """
    Execute a single write with WAL + retry‑on‑lock.
    """
    for attempt in range(MAX_RETRIES):
        try:
            await db.execute(sql, params)
            await db.commit()
            return
        except aiosqlite.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt + 1 < MAX_RETRIES:
                logging.warning("Retrying DB write after lock")
                await asyncio.sleep(LOCK_RETRY_DELAY)
            else:
                logging.error("DB write failed: %s", e)
                raise

SAVE_USER_CUR = """
INSERT INTO currency_preferences (user_id, currencies)
VALUES (?, ?)
ON CONFLICT(user_id) DO UPDATE SET currencies = excluded.currencies
"""
async def save_user_currencies(user_id: int, currencies: list[str]):
    db = await get_db()
    currency_str = ",".join(currencies)

    await execute_write(db, SAVE_USER_CUR, (user_id, currency_str))

async def load_user_currencies(user_id: int) -> list[str] | None:
    db = await get_db()

    async with db.execute(
        "SELECT currencies FROM currency_preferences WHERE user_id = ?",
        (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row and row[0]:
            return row[0].split(",")
        return None

CLEAR_USER_CUR = "DELETE FROM currency_preferences WHERE user_id = ?"
async def clear_user_currencies(user_id: int):
    db = await get_db()
    await execute_write(db, CLEAR_USER_CUR, (user_id,))


ADD_BASE_SUB = """
INSERT INTO base_subscribers (user_id, interval_minutes)
VALUES (?, ?)
ON CONFLICT(user_id, interval_minutes) DO NOTHING
"""
async def add_base_subscription(user_id: int, interval: int):
    db = await get_db()
    await execute_write(db, ADD_BASE_SUB, (user_id, interval))


REMOVE_BASE_SUB = "DELETE FROM base_subscribers WHERE user_id = ? AND interval_minutes = ?"
async def remove_base_subscription(user_id: int, interval: int):
    db = await get_db()
    await execute_write(db, REMOVE_BASE_SUB, (user_id, interval))

async def get_base_subscribers(interval: int) -> list[int]:
    db = await get_db()

    async with db.execute(
            "SELECT user_id FROM base_subscribers WHERE interval_minutes = ?",
            (interval,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_user_subscriptions(user_id: int) -> list[int]:
    """Returns a list of intervals the user is subscribed to."""
    db = await get_db()

    async with db.execute(
            "SELECT interval_minutes FROM base_subscribers WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_personal_plans(user_id: int) -> list[tuple[int, str]]:
    """
    Returns a list of tuples (interval_minutes, first_fire_time) for the given user.
    """
    db = await get_db()

    async with db.execute(
            "SELECT interval_minutes, first_fire_time FROM personal_subscribers WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()


ADD_PERSONAL = """
INSERT INTO personal_subscribers (user_id, interval_minutes, first_fire_time)
VALUES (?, ?, ?)
"""

async def add_personal_plan(user_id: int, interval: int, first_fire_time: datetime) -> None:
    db = await get_db()                                        # 🟢 shared conn
    await execute_write(db, ADD_PERSONAL, (user_id, interval, first_fire_time))


async def count_personal_plans(user_id: int) -> int:
    db = await get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM personal_subscribers WHERE user_id = ?",
        (user_id,)
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_user_tier(user_id: int) -> int:
    db = await get_db()

    async with db.execute("SELECT tier FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0