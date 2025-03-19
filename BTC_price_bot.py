import os
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

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
def format_price_message(price_data):
    """Formats the BTC price message."""
    message = "📊 *Current Bitcoin (BTC) Prices:*\n"
    for currency in CURRENCIES:
        if currency.lower() in price_data:
            message += f"💰 *{currency.upper()}:* {price_data[currency.lower()]:,}\n"  # Adds thousands separator
    return message


# Function to handle /price command
async def price(update: Update, context: CallbackContext) -> None:
    price_data = await get_btc_price()

    if not price_data:
        await update.message.reply_text("❌ Failed to fetch BTC price. Please try again later.")
        return
    # Formatting the price response
    message = format_price_message(price_data)

    await update.message.reply_text(message, parse_mode="Markdown")


# Function to start the bot
def main():
    # Create application instance with the bot token
    app = Application.builder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("price", price))

    # Start polling for messages
    print("🚀 Bot is running... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()