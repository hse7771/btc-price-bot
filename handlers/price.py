import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Any

import aiohttp
from telegram import Update
from telegram.ext import CallbackContext

from config import CURRENCIES, COINGECKO_API, BLOCKCHAIN_API, FETCH_INTERVAL
from util import send_or_edit, format_price_message, get_http_session, fetch_json
from keyboard import build_price_keyboard


@dataclass(slots=True)
class PriceCache:
    data: dict[str, Any]
    ts: datetime

PRICE_CACHE: PriceCache | None = None
CACHE_LOCK = asyncio.Lock()


# Function-helper for price command and price button functions
async def get_price_command_click(update: Update, context: CallbackContext):
    """Handles /price command or main “📊 Check Price” button."""
    await _show_price(update, context)


async def refresh_price_click(update: Update, context: CallbackContext) -> None:
    """Handles “🔄 Refresh Price” inline button."""
    await _show_price(update, context)


async def _show_price(update: Update, context: CallbackContext) -> None:
    """Fetch BTC price once and display it (new msg or edit-in-place)."""
    price_data = await get_btc_price()
    user_id = update.effective_user.id

    # target = update.message or update.callback_query.message # ✅ supports both command and button

    if not price_data:
        await send_or_edit(update, "❌ Failed to fetch BTC price. Please try again later.")
        return

    message = await format_price_message(price_data, user_id)
    reply_markup = build_price_keyboard("🔄 Refresh Price", "refresh_price")

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


async def get_btc_price() -> dict | None:
    """Return cached BTC price if fresh, otherwise refetch"""
    session = await get_http_session()
    return await _fetch_and_cache(session)


async def _fetch_and_cache(session: aiohttp.ClientSession) -> dict | None:
    """
    Return cached price if it is still fresh; otherwise fetch a new one and
    update the global cache.  A lock guarantees that only ONE coroutine performs
    the slow network fetch, even under heavy concurrent load.
    """
    global PRICE_CACHE
    # FAST PATH – no locking if data is already fresh
    if PRICE_CACHE and (datetime.utcnow() - PRICE_CACHE.ts).total_seconds() < FETCH_INTERVAL:
        return PRICE_CACHE.data

        # SLOW PATH – may need to refresh; take the lock
    async with CACHE_LOCK:  # suspend until lock is free
        #      re-check staleness because another coroutine might have refreshed
        #      while we were waiting.
        if PRICE_CACHE and (datetime.utcnow() - PRICE_CACHE.ts).total_seconds() < FETCH_INTERVAL:
            return PRICE_CACHE.data

        coingecko_task = asyncio.create_task(get_price_coingecko(session))
        blockchain_task = asyncio.create_task(get_price_blockchain(session))
        coingecko_data, blockchain_data = await asyncio.gather(
            coingecko_task, blockchain_task, return_exceptions=True
        )

        data = None
        if coingecko_data and not isinstance(coingecko_data, Exception):
            data = coingecko_data
        elif blockchain_data and not isinstance(blockchain_data, Exception):
            data = blockchain_data

        if data:
            PRICE_CACHE = PriceCache(data, datetime.utcnow())

        # leaving the `async with` block automatically releases the lock.
        return data


async def get_price_blockchain(session: aiohttp.ClientSession) -> dict | None:
    """Fetch BTC price from Blockchain (multiple currencies)."""
    data = await fetch_json(session, BLOCKCHAIN_API)

    if data:
        prices = {currency.lower(): round(info['last']) for currency, info in data.items() if
                  currency in CURRENCIES}
        return prices
    return None


async def get_price_coingecko(session: aiohttp.ClientSession) -> dict | None:
    """Fetch BTC price from CoinGecko (multiple currencies)."""
    data = await fetch_json(session, COINGECKO_API)

    if data and "bitcoin" in data:
        return data["bitcoin"]
    return None


async def refresh_price_cache(context: CallbackContext) -> None:
    session = await get_http_session()
    await _fetch_and_cache(session)
