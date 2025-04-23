import aiosqlite

DB_NAME = "BTC_bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
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
        await db.commit()


async def save_user_currencies(user_id: int, currencies: list[str]):
    currency_str = ",".join(currencies)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "REPLACE INTO currency_preferences (user_id, currencies) VALUES (?, ?)",
            (user_id, currency_str)
        )
        await db.commit()

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

async def clear_user_currencies(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM currency_preferences WHERE user_id = ?", (user_id,))
        await db.commit()


async def add_base_subscription(user_id: int, interval: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "REPLACE INTO base_subscribers (user_id, interval_minutes) VALUES (?, ?)",
            (user_id, interval)
        )
        await db.commit()

async def remove_base_subscription(user_id: int, interval: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM base_subscribers WHERE user_id = ? AND interval_minutes = ?",
            (user_id, interval)
        )
        await db.commit()

async def get_base_subscribers(interval: int) -> list[int]:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM base_subscribers WHERE interval_minutes = ?",
            (interval,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
