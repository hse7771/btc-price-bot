import os
import asyncio
import aiohttp
import logging
import db
from aiolimiter import AsyncLimiter
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, AIORateLimiter, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes
from typing import Any

# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Set up logging for debugging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# List of currencies we will support
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP", "CNY"]
BLOCKCHAIN_API = "https://blockchain.info/ticker"
COINGECKO_API = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={','.join(CURRENCIES)}"
PREDEFINED_INTERVALS = [15, 30, 60, 240, 1440]  # In minutes
FETCH_INTERVAL = 60   # seconds
CACHE_LOCK = asyncio.Lock()

USER_LIMIT = defaultdict(lambda: AsyncLimiter(1, 1))
USER_BURST = defaultdict(lambda: AsyncLimiter(30, 60))


@dataclass(slots=True)
class PriceCache:
    data: dict[str, Any]
    ts: datetime

PRICE_CACHE: PriceCache | None = None

HTTP_SESSION: aiohttp.ClientSession | None = None

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


async def refresh_price_cache(context: CallbackContext) -> None:
    session = await get_http_session()
    await _fetch_and_cache(session)


# Function to format the price response message
async def format_price_message(price_data: dict, user_id: int) -> str:
    """Formats the BTC price message with timestamp."""
    preferred = await db.load_user_currencies(user_id)
    currencies = preferred or CURRENCIES

    message = "📊 *Current Bitcoin (BTC) Prices:*\n"
    for currency in currencies:
        if currency.lower() in price_data:
            message += f"💰 *{currency.upper()}:* {price_data[currency.lower()]:,}\n"

    now = datetime.now().strftime("%H:%M:%S")
    message += f"\n🕒 Last updated at: `{now}`"
    return message


async def _show_price(update: Update, context: CallbackContext) -> None:
    """Fetch BTC price once and display it (new msg or edit-in-place)."""
    price_data = await get_btc_price()
    user_id = update.effective_user.id

    # target = update.message or update.callback_query.message # ✅ supports both command and button

    if not price_data:
        await send_or_edit(update, "❌ Failed to fetch BTC price. Please try again later.")
        return

    message = await format_price_message(price_data, user_id)
    reply_markup = build_main_action_keyboard("🔄 Refresh Price", "refresh_price")

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


# Function-helper for price command and price button functions
async def get_price_command_click(update: Update, context: CallbackContext):
    """Handles /price command or main “📊 Check Price” button."""
    await _show_price(update, context)


async def refresh_price_click(update: Update, context: CallbackContext) -> None:
    """Handles “🔄 Refresh Price” inline button."""
    await _show_price(update, context)


async def build_currency_keyboard(user_id: int) -> InlineKeyboardMarkup:
    selected = set(await db.load_user_currencies(user_id) or [])
    buttons = []

    # Currency toggle buttons (in rows of 2)
    for i in range(0, len(CURRENCIES), 2):
        row = []
        for currency in CURRENCIES[i:i+2]:
            label = "✅" if currency in selected else "☑️"
            row.append(InlineKeyboardButton(f"{label} {currency}", callback_data=f"toggle_{currency}"))
        buttons.append(row)

    # Done + Clear row
    buttons.append([
        InlineKeyboardButton("❌ Close", callback_data="close_menu"),
        InlineKeyboardButton("🗑️ Clear", callback_data="currency_clear")
    ])

    return InlineKeyboardMarkup(buttons)

# Handle /set_currency command
async def set_currency_command_click(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    #target = update.message or update.callback_query.message  # ✅ supports both command and button

    await send_or_edit(update,"💱 Select your preferred currencies (toggle below):",
        reply_markup=await build_currency_keyboard(user_id)
    )


async def toggle_currency(update: Update, context: CallbackContext, currency: str) -> None:
    user_id = update.effective_user.id

    preferences = await db.load_user_currencies(user_id) or []

    if currency in preferences:
        preferences.remove(currency)
    else:
        preferences.append(currency)
    await db.save_user_currencies(user_id, preferences)

    await send_or_edit(update, reply_markup=await build_currency_keyboard(user_id))


async def confirm_currency_selection(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    selected = await db.load_user_currencies(user_id)

    # If no currencies selected — default to all
    if not selected:
        await db.save_user_currencies(user_id, CURRENCIES.copy())
        msg = (
            "✅ *No currencies were selected.*\n"
            "All currencies have been selected by default.\n\n"
            "You can now check live BTC prices using these currencies."
        )
    else:
        msg = (
            f"✅ *Preferences saved!*\n"
            f"You selected: {', '.join(selected)}\n\n"
            "You can now check live BTC prices using these currencies."
        )

    # Add a 📊 Check Price button
    keyboard = [[
        InlineKeyboardButton("📊 Check Price", callback_data="get_price"),
        InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Replace the currency menu with confirmation + price button
    await send_or_edit(update, msg, parse_mode="Markdown", reply_markup=reply_markup)


async def clear_currency_selection(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    await db.clear_user_currencies(user_id)
    await send_or_edit(update, reply_markup=await build_currency_keyboard(user_id))


async def open_base_intervals(update: Update, message_text: str, callback_prefix: str):
    user_id = update.effective_user.id
    labels = {
        "base_": "⏰ Every {}",
        "unbase_": "❌ Cancel {} updates",
    }
    label_template = labels.get(callback_prefix, "⏰ Every {}")  # fallback for safety

    user_subs = await db.get_user_subscriptions(user_id)  # list of intervals
    intervals = PREDEFINED_INTERVALS

    if callback_prefix.startswith("unbase_"):
        if not user_subs:
            await send_or_edit(update,
            "🚫 You have no active subscriptions to cancel.",
                reply_markup=build_base_sub_keyboard()
            )
            return
        intervals = user_subs
    elif callback_prefix.startswith("base_"):
        if len(user_subs) >= len(PREDEFINED_INTERVALS):
            await send_or_edit(update,
            "✅ You are already subscribed to all available intervals!",
                reply_markup=build_base_sub_keyboard()
            )
            return
        intervals = [i for i in PREDEFINED_INTERVALS if i not in user_subs]

    keyboard = [[InlineKeyboardButton(
        label_template.format(format_interval(i)),
        callback_data=f"{callback_prefix}{i}"
    )] for i in intervals]
    keyboard.append([
        InlineKeyboardButton("⬅️ Back", callback_data="open_base_sub_menu")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit(update, message_text, reply_markup=reply_markup)


async def subscribe_base_command_click(update: Update, context: CallbackContext):
    await open_base_intervals(
        update,
        message_text="📅 Choose how often you want BTC price updates:",
        callback_prefix="base_"
    )


async def unsubscribe_base_command_click(update: Update, context: CallbackContext):
    await open_base_intervals(
        update,
        message_text="⚙️ Choose interval to unsubscribe:",
        callback_prefix="unbase_"
    )


async def open_base_sub_menu_command_click(update: Update, context: CallbackContext) -> None:
    reply_markup = build_base_sub_keyboard()

    await send_or_edit(update,
        "📅 *Manage your base BTC price subscriptions:*\n\n"
        "🕑 These are standard intervals: every 15, 30, 60 minutes, 4 hours, and 24 hours.\n\n"
        "Choose the options below:",
        parse_mode="Markdown",
        reply_markup=reply_markup)


def build_base_sub_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_base")],
        [InlineKeyboardButton("🛑 Unsubscribe", callback_data="unsubscribe_base")],
        [InlineKeyboardButton("⬅️ Back", callback_data="open_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def open_personal_sub_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("📋 View My Plans", callback_data="view_personal")],
        [InlineKeyboardButton("➕ Add Custom Plan", callback_data="add_personal")],
        [InlineKeyboardButton("❌ Cancel Plan", callback_data="cancel_personal")],
        [InlineKeyboardButton("💳 Upgrade", callback_data="upgrade")],
        [InlineKeyboardButton("⬅️ Back", callback_data="open_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit(update,
        "📆 *Manage your personal BTC update plans:*\n\n"
        "⚙️ These are fully customizable timers (e.g., every 7 min, daily at 14:00).\n\n"
        "Choose an option below:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def view_personal_plans_command_click(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    plans = await db.get_personal_plans(user_id)

    if not plans:
        message = (
            "ℹ️ You don’t have any personal BTC plans yet.\n\n"
            "Use ➕ *Add Custom Plan* to create one."
        )
    else:
        rows = []
        for idx, (interval, next_iso) in enumerate(plans, 1):
            next_dt = datetime.fromisoformat(next_iso)
            formatted_time = next_dt.strftime("%d:%m:%y %H:%M")
            rows.append(f"{idx}. ⏱ Every {interval} min, next: {formatted_time}")

        message = "📋 *Your Personal BTC Plans:*\n\n" + "\n".join(rows)

    # Show back to personal plan menu
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="open_personal_sub_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit(update,
        message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


def build_main_action_keyboard(label_first_button: str = "📊 Check Price", callback_first_button: str = "get_price") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(label_first_button, callback_data=callback_first_button),
            InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
        ],
        [
            InlineKeyboardButton("🔔 Base Plan", callback_data="open_base_sub_menu"),
            InlineKeyboardButton("📆 Personal Plan", callback_data="open_personal_sub_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def confirm_base_sub(update, context, interval):
    user_id = update.effective_user.id
    await db.add_base_subscription(user_id, interval)
    reply_markup = build_base_sub_keyboard()

    await send_or_edit(update,
    f"✅ Subscribed to updates every {format_interval(interval)}",
        parse_mode="Markdown",
        reply_markup=reply_markup)

async def confirm_unbase_sub(update, context, interval):
    user_id = update.effective_user.id
    await db.remove_base_subscription(user_id, interval)
    reply_markup = build_base_sub_keyboard()

    await send_or_edit(update,
    f"❌ Unsubscribed from {format_interval(interval)} updates",
        parse_mode="Markdown",
        reply_markup=reply_markup
        )


async def open_main_menu(update: Update, context: CallbackContext):
    await get_price_command_click(update, context)


def format_interval(interval: int) -> str:
    """Formats the interval for user-friendly display."""
    if interval % 1440 == 0:  # Full days
        days = interval // 1440
        return f"{days} day{'s' if days > 1 else ''}"
    elif interval % 60 == 0:  # Full hours
        hours = interval // 60
        return f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        return f"{interval} minutes"


def is_time_to_send(interval_minutes: int) -> bool:
    now = datetime.utcnow()
    return (now.minute % interval_minutes) == 0


async def notify_subscribers(context: ContextTypes.DEFAULT_TYPE):
    """Background task that checks base plan subscribers and sends updates."""

    app = context.application
    users_to_notify = set()

    for interval in PREDEFINED_INTERVALS:
        if is_time_to_send(interval):
            users = await db.get_base_subscribers(interval)
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


async def help_command(update: Update, context: CallbackContext) -> None:
    await send_or_edit(update,
        "ℹ️ *Bot Commands:*\n\n"
        "/start – Start the bot and show main menu\n"
        "/help – Show this help message\n"
        "/price – Show the current Bitcoin price\n"
        "/set_currency – Choose which currencies you want to see\n"
        
        "📅 *Base Plan Subscriptions:*\n"
        "/subscribe_base – Subscribe to regular BTC updates (e.g. every 15, 30, 60 min)\n"
        "/unsubscribe_base – Cancel your base plan subscriptions\n\n"
        
        "📆 *Personal Plans:*\n"
        "/add_personal – Add a custom BTC subscription\n"
        "/view_personal – View your custom subscriptions\n"
        "/cancel_personal – Remove a personal subscription\n\n"
                             
        "💳 *Account & Settings:*\n"
        "/upgrade – Learn about Pro/Ultra tiers\n"
        "/reset – Reset all your preferences\n"
        "/change_language – Change the interface language",
        parse_mode="Markdown"
    )


# Handle /start command
async def start_command(update: Update, context: CallbackContext) -> None:
    """Handles the /start command and sends a welcome message with buttons."""
    welcome_message = (
        "👋 *Hello! Welcome to the Bitcoin Price Bot.*\n\n"
        "Here’s what I can do for you:\n"
        "🔹 Show real-time BTC prices\n"
        "🔹 Let you choose preferred currencies\n"
        "🔹 Send regular price updates\n\n"
        "👇 Use the buttons below to get started:"
    )

    keyboard = [
        [InlineKeyboardButton("📊 Price", callback_data="get_price")],
        [InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")],
        [InlineKeyboardButton("🔔 Base Plan", callback_data="open_base_sub_menu")],
        [InlineKeyboardButton("📆 Personal Plan", callback_data="open_personal_sub_menu")],
        [InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit(update, welcome_message, parse_mode="Markdown", reply_markup=reply_markup)


def initialize_button_handlers():
    # Map callback_data to handlers
    handlers = {
        "get_price": get_price_command_click,
        "refresh_price": refresh_price_click,
        "open_currency_menu": set_currency_command_click,
        "close_menu": confirm_currency_selection,
        "currency_clear": clear_currency_selection,
        "open_main_menu": open_main_menu,
        "open_base_sub_menu": open_base_sub_menu_command_click,
        "subscribe_base": subscribe_base_command_click,
        "unsubscribe_base": unsubscribe_base_command_click,
        "open_personal_sub_menu": open_personal_sub_menu,
        "view_personal": view_personal_plans_command_click,
    }
    # Dynamic handlers for currency toggles
    for currency in CURRENCIES:
        handlers[f"toggle_{currency}"] = lambda u, c, curr=currency: toggle_currency(u, c, curr)
    # Dynamic handlers for base/unbase subscription per interval
    for interval in PREDEFINED_INTERVALS:
        handlers[f"base_{interval}"] = lambda u, c, i=interval: confirm_base_sub(u, c, i)
        handlers[f"unbase_{interval}"] = lambda u, c, i=interval: confirm_unbase_sub(u, c, i)

    return handlers

BUTTON_HANDLERS = initialize_button_handlers()

async def button_click_handler(update: Update, context: CallbackContext) -> None:
    """Handles button press for 📊 Price."""
    query = update.callback_query
    await query.answer()  # Acknowledge button press to Telegram

    handler = BUTTON_HANDLERS.get(query.data)
    if handler:
        await handler(update, context)
    else:
        await query.edit_message_text("❓ Unknown action.")


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


# Function to start the bot
async def main():
    # init DB
    await db.init_db()
    # Create application instance with the bot token
    app = (
        Application.builder()
        .token(TOKEN)
        .rate_limiter(AIORateLimiter(
            overall_max_rate=30,
            max_retries=3
        ))
        .build()
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", get_price_command_click))
    app.add_handler(CommandHandler("set_currency", set_currency_command_click))
    app.add_handler(CommandHandler("subscribe_base", subscribe_base_command_click))
    app.add_handler(CommandHandler("unsubscribe_base", unsubscribe_base_command_click))
    app.add_handler(CommandHandler("view_personal", view_personal_plans_command_click))
    app.add_handler(CallbackQueryHandler(button_click_handler))

    # Start polling for messages
    print("🚀 Bot is running... Press Ctrl+C to stop.")
    async with app:
        await app.start()
        await app.updater.start_polling()

        delay_subs = (60 - datetime.utcnow().second) % 60
        app.job_queue.run_repeating(notify_subscribers, interval=60, first=delay_subs)
        delay_cache = (delay_subs + 30) % 60
        app.job_queue.run_repeating(refresh_price_cache, interval=FETCH_INTERVAL, first=delay_cache)
        try:
            # This keeps the loop alive forever
            await asyncio.Event().wait()
        finally:
            if HTTP_SESSION and not HTTP_SESSION.closed:
                await HTTP_SESSION.close()

if __name__ == "__main__":
    asyncio.run(main())

