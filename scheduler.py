import asyncio
import logging
from datetime import datetime

from telegram.ext import ContextTypes

from config import PREDEFINED_INTERVALS
from db.db import get_base_subscribers
from handlers.price import get_btc_price, format_price_message


async def notify_subscribers(context: ContextTypes.DEFAULT_TYPE):
    """Background task that checks base plan subscribers and sends updates."""

    app = context.application
    users_to_notify = set()

    for interval in PREDEFINED_INTERVALS:
        if is_time_to_send(interval):
            users = await get_base_subscribers(interval)
            users_to_notify.update(users)  # set() automatically removes duplicates

    if users_to_notify:
        logging.info(f"📤 Sending BTC update to {len(users_to_notify)} users.")

        price_data = await get_btc_price()
        if price_data:
            tasks, user_ids = [], []
            for user_id in users_to_notify:
                message = await format_price_message(price_data, user_id)
                user_ids.append(user_id)
                tasks.append(
                    app.bot.send_message(
                        chat_id=user_id,
                        text=f"📢 *BTC Update* 📢\n\n{message}",
                        parse_mode="Markdown"
                    )
                )
            # Run all send tasks in parallel, safely
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for uid, result in zip(user_ids, results):
                if isinstance(result, Exception):
                    logging.error(
                        f"❌ Failed to send message to user {uid} | {type(result).__name__}: {result}"
                    )



def is_time_to_send(interval_minutes: int) -> bool:
    now = datetime.utcnow()
    return (now.minute % interval_minutes) == 0
