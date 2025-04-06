import os
import asyncio
import aiohttp
import logging
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
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP", "USDT"]
BLOCKCHAIN_API = "https://blockchain.info/ticker"
COINGECKO_API = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={','.join(CURRENCIES)}"

user_currency_preferences: dict[int, list[str]] = {}


async def fetch_json(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Helper function to fetch JSON data from an API asynchronously."""
    try:
        async with session.get(url, timeout=5) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        logging.error(f"API request failed: {url} | Error: {e}")
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
def format_price_message(price_data: dict) -> str:
    """Formats the BTC price message with timestamp."""
    message = "📊 *Current Bitcoin (BTC) Prices:*\n"
    for currency in CURRENCIES:
        if currency.lower() in price_data:
            message += f"💰 *{currency.upper()}:* {price_data[currency.lower()]:,}\n"

    # Add timestamp (HH:MM:SS)
    now = datetime.now().strftime("%H:%M:%S")
    message += f"\n🕒 Last updated at: `{now}`"
    return message

# Function-helper for price command and price button functions
async def send_price_message(target, context: CallbackContext):
    price_data = await get_btc_price()
    if not price_data:
        await target.reply_text("❌ Failed to fetch BTC price. Please try again later.")
        return

    message = format_price_message(price_data)
    keyboard = [[InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await target.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


# Function to handle /price command
async def price_command(update: Update, context: CallbackContext) -> None:
    await send_price_message(update.message, context)

# Function to handle price button click
async def price_button_click(update: Update, context: CallbackContext) -> None:
    await send_price_message(update.callback_query.message, context)


async def refresh_price_click(update: Update, context: CallbackContext) -> None:
    price_data = await get_btc_price()

    if not price_data:
        await update.callback_query.edit_message_text("❌ Failed to refresh BTC price.")
        return

    message = format_price_message(price_data)

    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)


def build_currency_keyboard(user_id: int) -> InlineKeyboardMarkup:
    selected = set(user_currency_preferences.get(user_id, []))
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
        InlineKeyboardButton("✅ Done", callback_data="currency_done"),
        InlineKeyboardButton("🗑️ Clear", callback_data="currency_clear")
    ])

    return InlineKeyboardMarkup(buttons)

# Handle /set_currency command
async def set_currency(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    # Initialize if not already
    user_currency_preferences.setdefault(user_id, [])

    await update.message.reply_text(
        "💱 Select your preferred currencies (toggle below):",
        reply_markup=build_currency_keyboard(user_id)
    )


# Handle /start command
async def start(update: Update, context: CallbackContext) -> None:
    """Handles the /start command and sends a welcome message with buttons."""
    welcome_message = (
        "👋 *Hello! Welcome to the Bitcoin Price Bot.*\n\n"
        "Here’s what I can do for you:\n"
        "🔹 Fetch live Bitcoin prices\n"
        "🔹 Support multiple currencies\n"
        "🔹 Support currency filter\n\n"
        "👇 Choose an option:"
    )

    keyboard = [
        [InlineKeyboardButton("📊 Price", callback_data="get_price")],
        [InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, parse_mode="Markdown", reply_markup=reply_markup)


# Map callback_data to handlers
BUTTON_HANDLERS = {
    "get_price": price_button_click,
    "refresh_price": refresh_price_click,
}


async def button_click_handler(update: Update, context: CallbackContext) -> None:
    """Handles button press for 📊 Price."""
    query = update.callback_query
    await query.answer()  # Acknowledge button press to Telegram

    handler = BUTTON_HANDLERS.get(query.data)
    if handler:
        await handler(update, context)
    else:
        await query.edit_message_text("❓ Unknown action.")


# Function to start the bot
def main():
    # Create application instance with the bot token
    app = Application.builder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("set_currency", set_currency))
    app.add_handler(CallbackQueryHandler(button_click_handler))

    # Start polling for messages
    print("🚀 Bot is running... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()