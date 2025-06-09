import aiosqlite
import asyncio
import logging
from pathlib import Path

from config import TierConvertFromNumber


DB_PATH = Path("db", "database files", "BTC_bot_data.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)    # auto-create folders
DB_NAME = str(DB_PATH)

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
                CREATE TABLE IF NOT EXISTS user_time_settings (
                    user_id INTEGER PRIMARY KEY,
                    timezone TEXT NULL,
                    offset_minutes INTEGER NOT NULL DEFAULT 0,
                    tz_method TEXT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    await db.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    user_id INTEGER PRIMARY KEY,
                    tier INTEGER DEFAULT 0,           
                    subscription_end DATETIME,        -- if using expiring subscriptions
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    await db.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    operation_type TEXT NOT NULL,
                    tier INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    amount INTEGER NOT NULL,  -- in cents/kopecks
                    provider TEXT NOT NULL,
                    telegram_payment_charge_id TEXT UNIQUE NOT NULL,
                    provider_payment_charge_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    await db.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            message_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL
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

async def get_user_base_subscriptions(user_id: int) -> list[int]:
    """Returns a list of intervals the user is subscribed to."""
    db = await get_db()

    async with db.execute(
            "SELECT interval_minutes FROM base_subscribers WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_personal_plans(user_id: int) -> list[tuple[int, int, str]]:
    """
    Returns a list of tuples (interval_minutes, first_fire_time) for the given user.
    """
    db = await get_db()

    async with db.execute(
            "SELECT id, interval_minutes, first_fire_time FROM personal_subscribers WHERE user_id = ? ORDER BY created_at",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()


ADD_PERSONAL = """
INSERT INTO personal_subscribers (user_id, interval_minutes, first_fire_time)
VALUES (?, ?, ?)
"""

async def add_personal_plan(user_id: int, interval: int, first_fire_time: str) -> None:
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

    async with db.execute("SELECT tier FROM user_subscriptions WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


UPDATE_TIER = """
INSERT INTO user_subscriptions (user_id, tier, subscription_end, updated_at)
VALUES (?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(user_id) DO UPDATE SET
    tier             = excluded.tier,
    subscription_end = excluded.subscription_end,
    updated_at       = CURRENT_TIMESTAMP
"""

async def update_user_tier(user_id: int, new_tier: TierConvertFromNumber, expiry_date: str | None):
    db = await get_db()
    await execute_write(db, UPDATE_TIER,(user_id, new_tier, expiry_date,))


async def get_all_personal() -> list[tuple[int, int, str]]:
    """
    Returns [(user_id, interval_minutes, first_fire_iso)] for *all* rows.
    """
    db = await get_db()
    async with db.execute(
        "SELECT user_id, interval_minutes, first_fire_time FROM personal_subscribers"
    ) as cur:
        return await cur.fetchall()


REMOVE_PERSONAL_SUB = """DELETE FROM personal_subscribers WHERE id = ?"""
async def delete_personal_plan(plan_id: int):
    db = await get_db()
    await execute_write(db, REMOVE_PERSONAL_SUB, (plan_id, ))


SET_USER_TZ = """
INSERT INTO user_time_settings (user_id, timezone, offset_minutes, tz_method)
VALUES (?, ?, ?, ?)
ON CONFLICT(user_id) DO UPDATE SET
    timezone       = excluded.timezone,
    offset_minutes = excluded.offset_minutes,
    tz_method      = excluded.tz_method,
    updated_at     = CURRENT_TIMESTAMP
"""

async def set_user_timezone(user_id: int, timezone: str | None, offset_minutes: int, method: str):
    db = await get_db()
    await execute_write(db, SET_USER_TZ,(user_id, timezone, offset_minutes, method))


GET_USER_TZ = """
SELECT timezone, offset_minutes, tz_method FROM user_time_settings WHERE user_id = ?
"""

async def get_user_timezone(user_id: int) -> dict | None:
    db = await get_db()
    tz_data = {"timezone": None, "offset_minutes": 0, "method": None}
    async with db.execute(GET_USER_TZ, (user_id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            tz_data["timezone"], tz_data["offset_minutes"], tz_data["method"] = row[0], row[1], row[2]
        return tz_data


RECORD_PAYMENT = """
INSERT INTO payments (user_id, operation_type, tier, currency, amount, provider, telegram_payment_charge_id, provider_payment_charge_id) 
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""
async def record_payment(user_id: int, operation_type: str, tier: TierConvertFromNumber,
                        currency: str, amount: int, provider: str,
                        telegram_charge_id: str, provider_charge_id: str) -> None:
    db = await get_db()
    await execute_write(db, RECORD_PAYMENT,
                        (user_id, operation_type, int(tier),
                                    currency, amount, provider,
                                    telegram_charge_id, provider_charge_id))


RECORD_INVOICE = """
INSERT INTO invoices (message_id, chat_id, created_at)
VALUES (?, ?, ?)
"""

async def record_invoice(message_id: int, chat_id: int, created_at: int):
    db = await get_db()
    await execute_write(db, RECORD_INVOICE, (message_id, chat_id, created_at))


GET_EXPIRED = "SELECT message_id, chat_id FROM invoices WHERE created_at < ?"

async def get_expired_invoice_messages(cutoff: int) -> list[tuple[int, int]]:
    db = await get_db()

    async with db.execute(GET_EXPIRED, (cutoff,)) as cursor:
        return await cursor.fetchall()


DELETE_INVOICE = "DELETE FROM invoices WHERE message_id = ?"

async def remove_invoice_from_db(message_id: int):
    db = await get_db()
    await execute_write(db, DELETE_INVOICE, (message_id,))


GET_EXPIRED_SUBS = """
SELECT user_id, subscription_end, tier
FROM   user_subscriptions
WHERE  subscription_end IS NOT NULL AND  subscription_end < CURRENT_TIMESTAMP
"""

async def get_expired_subscriptions() -> list[tuple[int, str, int]]:
    db = await get_db()
    async with db.execute(GET_EXPIRED_SUBS) as cursor:
        return await cursor.fetchall()


async def downgrade_user(user_id: int, expiry_date: str | None = None) -> None:
   await update_user_tier(user_id, TierConvertFromNumber.FREE, expiry_date)
