import asyncio
import logging
from datetime import datetime, timezone

from telegram.ext import ContextTypes

from config import PREDEFINED_INTERVALS
from db.db import get_all_personal, get_base_subscribers
from handlers.price import format_price_message, get_btc_price


async def notify_subscribers(context: ContextTypes.DEFAULT_TYPE):
    """Background task that checks base plan subscribers and sends updates."""

    app = context.application
    now = datetime.now(timezone.utc)
    users_to_notify = set()

    # base plans
    for interval in PREDEFINED_INTERVALS:
        if is_time_to_send_base(interval):
            users = await get_base_subscribers(interval)
            users_to_notify.update(users)  # set() automatically removes duplicates

    # personal plans
    rows = await get_all_personal()  # [(uid, interval, iso), …]
    for uid, interval, first_iso in rows:
        first_fire = datetime.fromisoformat(first_iso)
        first_fire = first_fire.replace(tzinfo=timezone.utc)
        if is_time_to_send_personal(first_fire, interval, now):
            users_to_notify.add(uid)

    if not users_to_notify:
        return

    logging.info(f"📤 Sending BTC update to {len(users_to_notify)} users.")

    price_data = await get_btc_price()
    if not price_data:
        return

    tasks, user_ids = [], []
    for user_id in users_to_notify:
        message = await format_price_message(price_data, user_id)
        user_ids.append(user_id)
        tasks.append(
            app.bot.send_message(
                chat_id=user_id, text=f"📢 *BTC Update* 📢\n\n{message}", parse_mode="Markdown"
            )
        )
    # Run all send tasks in parallel, safely
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for uid, result in zip(user_ids, results):
        if isinstance(result, Exception):
            logging.error(
                f"❌ Failed to send message to user {uid} | {type(result).__name__}: {result}"
            )


def is_time_to_send_base(interval_minutes: int) -> bool:
    now = datetime.now(timezone.utc)
    total_minutes = now.hour * 60 + now.minute  # 0-1439 UTC
    return (total_minutes % interval_minutes) == 0


def is_time_to_send_personal(first_fire: datetime, interval: int, now: datetime) -> bool:
    if now < first_fire:
        return False
    elapsed_min = int((now - first_fire).total_seconds() // 60)
    return elapsed_min % interval == 0
