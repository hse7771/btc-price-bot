import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict
from collections import defaultdict

import aiohttp
from aiolimiter import AsyncLimiter
from telegram import Update, InlineKeyboardMarkup

from config import CURRENCIES
from db.db import load_user_currencies


HTTP_SESSION: aiohttp.ClientSession | None = None
USER_LIMIT = defaultdict(lambda: AsyncLimiter(1, 1))
USER_BURST = defaultdict(lambda: AsyncLimiter(30, 60))


async def send_or_edit(update: Update, msg: str | None = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = None):
    """
    Handles sending or editing a message depending on whether it was triggered by a button click or a command.
    """
    uid = update.effective_user.id
    async with USER_LIMIT[uid], USER_BURST[uid]:
        if update.callback_query:
            # message editing
            if msg:
                await update.callback_query.edit_message_text(msg, parse_mode=parse_mode, reply_markup=reply_markup)
            # keyboard editing
            else:
                await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
        # new message sending
        else:
            await update.message.reply_text(msg, parse_mode=parse_mode, reply_markup=reply_markup)


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
    global HTTP_SESSION
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

    now = datetime.now().strftime("%H:%M:%S")
    message += f"\n🕒 Last updated at: `{now}`"
    return message


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