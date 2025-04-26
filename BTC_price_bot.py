import os
import asyncio
import aiohttp
import logging
import db
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

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
PREDEFINED_INTERVALS = [10, 30, 60, 240, 1440]  # In minutes


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
    """Get BTC price from CoinGecko or Blockchain with failover. Fetch exchange rates in parallel."""
    async with aiohttp.ClientSession() as session:
        # Start fetching all data in parallel
        coingecko_task = asyncio.create_task(get_price_coingecko(session))
        blockchain_task = asyncio.create_task(get_price_blockchain(session))

        # Wait for CoinGecko result first
        coingecko_price = await coingecko_task
        if coingecko_price:
            return coingecko_price  # Return if CoinGecko succeeded

        # If CoinGecko failed, wait for Blockchain price
        blockchain_price = await blockchain_task
        if blockchain_price:
            return blockchain_price

    return None  # If both APIs fail, return None


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


# Function-helper for price command and price button functions
async def get_price_command_click(update: Update, context: CallbackContext):
    price_data = await get_btc_price()
    user_id = update.effective_user.id

    #target = update.message or update.callback_query.message # ✅ supports both command and button

    if not price_data:
        await handle_button_command_dif(update).reply_text("❌ Failed to fetch BTC price. Please try again later.")
        return

    message = await format_price_message(price_data, user_id)
    keyboard = [[
        InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price"),
        InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
    ],
    [
        InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_base"),
        InlineKeyboardButton("🛑 Unsubscribe", callback_data="unsubscribe_base")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await handle_button_command_dif(update).reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


async def refresh_price_click(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    price_data = await get_btc_price()

    if not price_data:
        await update.callback_query.edit_message_text("❌ Failed to refresh BTC price.")
        return

    message = await format_price_message(price_data, user_id)

    keyboard = [[
        InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price"),
        InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
    ],
    [
        InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_base"),
        InlineKeyboardButton("🛑 Unsubscribe", callback_data="unsubscribe_base")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)


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

    await handle_button_command_dif(update).reply_text(
        "💱 Select your preferred currencies (toggle below):",
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

    await update.callback_query.edit_message_reply_markup(reply_markup=await build_currency_keyboard(user_id))


async def confirm_currency_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
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

    await query.answer()

    # Add a 📊 Check Price button
    keyboard = [[
        InlineKeyboardButton("📊 Check Price", callback_data="get_price"),
        InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Replace the currency menu with confirmation + price button
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)


async def clear_currency_selection(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    await db.clear_user_currencies(user_id)
    await update.callback_query.answer("🗑️ Cleared!")
    await update.callback_query.edit_message_reply_markup(reply_markup=await build_currency_keyboard(user_id))


async def open_base_subscription_menu(update: Update, message_text: str, callback_prefix: str):
    labels = {
        "base_": "⏰ Every {}",
        "unbase_": "❌ Cancel {} updates",
    }
    label_template = labels.get(callback_prefix, "⏰ Every {}")  # fallback for safety
    keyboard = [[InlineKeyboardButton(
        label_template.format(format_interval(i)),
        callback_data=f"{callback_prefix}{i}"
    )] for i in PREDEFINED_INTERVALS]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await handle_button_command_dif(update).reply_text(
        message_text,
        reply_markup=reply_markup
    )


async def subscribe_base_command_click(update: Update, context: CallbackContext):
    await open_base_subscription_menu(
        update,
        message_text="📅 Choose how often you want BTC price updates:",
        callback_prefix="base_"
    )


async def unsubscribe_base_command_click(update: Update, context: CallbackContext):
    await open_base_subscription_menu(
        update,
        message_text="⚙️ Choose interval to unsubscribe:",
        callback_prefix="unbase_"
    )


def build_main_action_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Check Price", callback_data="get_price"),
            InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
        ],
        [
            InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_base"),
            InlineKeyboardButton("🛑 Unsubscribe", callback_data="unsubscribe_base")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def confirm_base_sub(update, context, interval):
    user_id = update.effective_user.id
    await db.add_base_subscription(user_id, interval)
    reply_markup = build_main_action_keyboard()

    await update.callback_query.edit_message_text(
        f"✅ Subscribed to updates every {format_interval(interval)}!",
        parse_mode="Markdown",
        reply_markup=reply_markup)

async def confirm_unbase_sub(update, context, interval):
    user_id = update.effective_user.id
    await db.remove_base_subscription(user_id, interval)
    reply_markup = build_main_action_keyboard()

    await update.callback_query.edit_message_text(
        f"❌ Unsubscribed from {format_interval(interval)} updates.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


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


async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "ℹ️ *Bot Commands:*\n\n"
        "/start – Start the bot and show main menu\n"
        "/help – Show this help message\n"
        "/price – Show the current Bitcoin price\n"
        "/set_currency – Choose which currencies you want to see\n"
        "/subscribe – Subscribe to regular BTC updates (e.g. every 15, 30, 60 min)\n"
        "/unsubscribe – Cancel your base update subscriptions\n"
        "/reset – Reset all your preferences and subscriptions\n"
        "/change_language – Change the language",
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
        [InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_base")],
        [InlineKeyboardButton("🛑 Unsubscribe", callback_data="unsubscribe_base")],
        [InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, parse_mode="Markdown", reply_markup=reply_markup)

def initialize_button_handlers():
    # Map callback_data to handlers
    handlers = {
        "get_price": get_price_command_click,
        "refresh_price": refresh_price_click,
        "open_currency_menu": set_currency_command_click,
        "close_menu": confirm_currency_selection,
        "currency_clear": clear_currency_selection,
        "subscribe_base": subscribe_base_command_click,
        "unsubscribe_base": unsubscribe_base_command_click,
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


def handle_button_command_dif(update: Update):
    """
    Returns the appropriate message target from the Update object.

    This handles both cases:
    - update.message: when the user sends a regular command (e.g., /price)
    - update.callback_query.message: when the user interacts via an inline button

    Use this to reply or edit messages without needing to check which type of interaction triggered the update.
    """
    return update.message or update.callback_query.message


# Function to start the bot
async def main():
    # init DB
    await db.init_db()
    # Create application instance with the bot token
    app = Application.builder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", get_price_command_click))
    app.add_handler(CommandHandler("set_currency", set_currency_command_click))
    app.add_handler(CommandHandler("subscribe", subscribe_base_command_click))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_base_command_click))
    app.add_handler(CallbackQueryHandler(button_click_handler))

    # Start polling for messages
    print("🚀 Bot is running... Press Ctrl+C to stop.")
    async with app:
        await app.start()
        await app.updater.start_polling()
        # This keeps the loop alive forever
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

