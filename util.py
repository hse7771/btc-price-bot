import logging
from datetime import datetime
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
