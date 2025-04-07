import aiosqlite
import os

DB_NAME = "BTC_bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS currency_preferences (
                user_id INTEGER PRIMARY KEY,
                currencies TEXT  -- Stored as comma-separated values
            )
        ''')
        await db.commit()
