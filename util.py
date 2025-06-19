import asyncio
import functools
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

import aiohttp
from aiolimiter import AsyncLimiter
from telegram import (
    Bot,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ConversationHandler

from config import CURRENCIES
from db.db import get_user_timezone, load_user_currencies

HTTP_SESSION: aiohttp.ClientSession | None = None
USER_LIMIT = defaultdict(lambda: AsyncLimiter(1, 1))
USER_BURST = defaultdict(lambda: AsyncLimiter(30, 60))


async def send_or_edit(update: Update, msg: str | None = None,
                       reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove = None,
                       parse_mode: str = None) -> Optional[Message]:
    """
    Handles sending or editing a message depending on whether it was triggered by a button click or a command.
    """
    uid = update.effective_user.id
    async with USER_LIMIT[uid], USER_BURST[uid]:
        is_reply_markup = isinstance(reply_markup, (ReplyKeyboardMarkup, ReplyKeyboardRemove))

        if update.callback_query and not is_reply_markup:
            # Edit message from a button press
            if msg:
                await update.callback_query.edit_message_text(msg, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
            return update.callback_query.message
        else:
            # Safe fallback — new message (works with ReplyKeyboardMarkup or text command)
            return await update.effective_message.reply_text(msg, parse_mode=parse_mode, reply_markup=reply_markup)


async def get_http_session() -> aiohttp.ClientSession:
    """Return a singleton aiohttp session, creating it on first use."""
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        HTTP_SESSION = aiohttp.ClientSession()
    return HTTP_SESSION


async def fetch_json(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Helper function to fetch JSON data from an API asynchronously."""
    try:
        async with session.get(url, timeout=5) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        logging.error(f"API request failed: {url} | Error: {e}")
    except Exception as e:
        logging.exception(f"Unexpected error in fetch_json({url}): {e}")
    return None


async def close_http_session():
    if HTTP_SESSION and not HTTP_SESSION.closed:
        await HTTP_SESSION.close()


# Function to format the price response message
async def format_price_message(price_data: dict, user_id: int) -> str:
    """Formats the BTC price message with timestamp."""
    preferred = await load_user_currencies(user_id)
    currencies = preferred or CURRENCIES

    message = "📊 *Current Bitcoin (BTC) Prices:*\n"
    for currency in currencies:
        if currency.lower() in price_data:
            message += f"💰 *{currency.upper()}:* {price_data[currency.lower()]:,}\n"

    utc_now = datetime.now(timezone.utc)
    tz_data = await get_user_timezone(user_id)
    if tz_data and (tz_data.get("timezone") or tz_data.get("method")):
        local_now = convert_utc_to_local(utc_now, tz_data)
        stamp = local_now.strftime("%H:%M:%S")
    else:
        stamp = utc_now.strftime("%H:%M:%S UTC")
    message += f"\n🕒 Last updated at: `{stamp}`"
    return message


async def safe_delete_message(bot: Bot, chat_id: int, msg_id: int, delay: float = 0):
    """
    Tries to delete a message silently. Fails silently if message is already gone or not deletable.
    """
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, msg_id)
    except Exception as e:
        logging.debug(f"Delete failed for message {msg_id} in chat {chat_id}: {e}")


async def delete_tracked_messages(bot: Bot, chat_id: int, user_data: dict[str, int]) -> None:
    ids = user_data.pop("temporary_msg_ids", [])
    for msg_id in ids:
        await safe_delete_message(bot, chat_id, msg_id)
    user_data.clear()


def validate_time_hhmm(text: str) -> tuple[int, int] | None:
    """Parses HH:MM time string. Returns (hour, minute) or None if invalid."""
    try:
        hour, minute = map(int, text.strip().split(":"))
        assert 0 <= hour < 24 and 0 <= minute < 60
        return hour, minute
    except (ValueError, AssertionError):
        return None


def convert_local_to_utc(local_dt: datetime, tz_data: Dict) -> datetime:
    """
    Convert *naive* local_dt (user clock) → *naive* UTC datetime
    """
    tz_name, offset, method = tz_data["timezone"], tz_data["offset_minutes"], tz_data["method"]
    if method == "location" and tz_name:
        zone = ZoneInfo(tz_name)
        # Attach local zone, then convert to UTC
        aware_local = local_dt.replace(tzinfo=zone)
        return aware_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    else:
        # manual or no-setting ⇒ fixed offset
        return local_dt - timedelta(minutes=offset)


def convert_utc_to_local(utc_dt: datetime, tz_data: Dict) -> datetime:
    """
    Convert *naive* UTC datetime → *naive* local datetime
    """
    tz_name, offset, method = tz_data["timezone"], tz_data["offset_minutes"], tz_data["method"]
    if method == "location" and tz_name:
        zone = ZoneInfo(tz_name)
        aware_utc = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
        return aware_utc.astimezone(zone).replace(tzinfo=None)
    else:
        return utc_dt + timedelta(minutes=offset)


def format_utc_offset(offset_minutes: int) -> str:
    """
    Return a string like  'UTC-05:00'  or  'UTC+05:30'
    for the signed integer offset (minutes).
    """
    sign = "+" if offset_minutes >= 0 else "-"
    abs_min = abs(offset_minutes)
    hours, mm = divmod(abs_min, 60)
    return f"UTC{sign}{hours:02}:{mm:02}"


def safe_convo_step(menu_func=None):
    """
    Decorator for Telegram ConversationHandler steps.
    On exception: logs, sends error message, returns user to menu, ends conversation.
    Usage:
        @safe_convo_step(menu_func=open_personal_sub_menu)
        async def step(...): ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logging.exception(f"Exception in {func.__name__}: {e}")
                try:
                    # Try to send a simple message. If send_or_edit available, use it
                    if hasattr(context, "bot") and hasattr(update, "effective_chat"):
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="⚠️ An error occurred. Use slash commands to return to the menu."
                        )
                        # await menu_func(update, context)
                except Exception as sub_e:
                    logging.error(f"Failed to show error UI: {sub_e}")
                return ConversationHandler.END
        return wrapper
    return decorator


def parse_payload(payload: str) -> dict[str, str | int] | None:
    try:
        parts = parse_qs(payload)
        return {
            "tier": parts["tier"][0],
            "provider": parts["provider"][0],
            "user_id": int(parts["user"][0]),
            "ts": int(parts["timestamp"][0]),
            "operation_type": parts["operation_type"][0],
        }
    except (KeyError, ValueError, IndexError):
        return None
