from datetime import datetime

import aiosqlite
import asyncio
import logging

DB_NAME = "BTC_bot_data.db"
MAX_RETRIES        = 2          # 1 original try + 1 retry
LOCK_RETRY_DELAY   = 0.05       # seconds (50ms)

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA journal_mode=WAL;")  # keeps readers concurrent
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
    currency_str = ",".join(currencies)
    async with aiosqlite.connect(DB_NAME) as db:
        await execute_write(db, SAVE_USER_CUR, (user_id, currency_str))

async def load_user_currencies(user_id: int) -> list[str] | None:
    async with aiosqlite.connect(DB_NAME) as db:
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
    async with aiosqlite.connect(DB_NAME) as db:
        await execute_write(db, CLEAR_USER_CUR, (user_id,))


ADD_BASE_SUB = """
INSERT INTO base_subscribers (user_id, interval_minutes)
VALUES (?, ?)
ON CONFLICT(user_id, interval_minutes) DO NOTHING
"""
async def add_base_subscription(user_id: int, interval: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await execute_write(db, ADD_BASE_SUB, (user_id, interval))


REMOVE_BASE_SUB = "DELETE FROM base_subscribers WHERE user_id = ? AND interval_minutes = ?"
async def remove_base_subscription(user_id: int, interval: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await execute_write(db, REMOVE_BASE_SUB, (user_id, interval))

async def get_base_subscribers(interval: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM base_subscribers WHERE interval_minutes = ?",
            (interval,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_user_subscriptions(user_id: int) -> list[int]:
    """Returns a list of intervals the user is subscribed to."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT interval_minutes FROM base_subscribers WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
