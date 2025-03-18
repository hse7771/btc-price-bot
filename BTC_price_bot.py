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
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP"]

# Currency conversion API (Replace with a real API)
CURRENCY_CONVERSION_API = "https://api.exchangerate-api.com/v4/latest/USD"
BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
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


async def get_price_binance(session: aiohttp.ClientSession) -> dict | None:
    """Fetch BTC price from Binance (USD only)."""
    data = await fetch_json(session, BINANCE_API)

    if data and "price" in data:
        return {"usd": float(data["price"])}  # Binance returns only USD
    return None


async def get_price_coingecko(session: aiohttp.ClientSession) -> dict | None:
    """Fetch BTC price from CoinGecko (multiple currencies)."""
    data = await fetch_json(session, COINGECKO_API)

    if data and "bitcoin" in data:
        return data["bitcoin"]
    return None


async def get_currency_conversion_rates(session: aiohttp.ClientSession) -> dict | None:
    """Fetch latest exchange rates for USD to other currencies."""
    data = await fetch_json(session, CURRENCY_CONVERSION_API)

    if data and "rates" in data:
        return {currency: data["rates"].get(currency.upper(), None) for currency in CURRENCIES}
    return None


async def get_btc_price() -> dict | None:
    """Get BTC price from CoinGecko or Binance with failover. Fetch exchange rates in parallel."""
    async with aiohttp.ClientSession() as session:
        # Start fetching all data in parallel
        coingecko_task = asyncio.create_task(get_price_coingecko(session))
        binance_task = asyncio.create_task(get_price_binance(session))
        exchange_rates_task = asyncio.create_task(get_currency_conversion_rates(session))

        # Wait for CoinGecko result first
        coingecko_price = await coingecko_task
        if coingecko_price:
            return coingecko_price  # Return if CoinGecko succeeded

        # If CoinGecko failed, wait for Binance price
        binance_price = await binance_task
        exchange_rates = await exchange_rates_task  # Wait for exchange rates too

        if binance_price and exchange_rates:
            return {
                currency: binance_price["usd"] * exchange_rates[currency]
                if exchange_rates[currency] else None
                for currency in CURRENCIES
            }

    return None  # If both APIs fail, return None


# Function to handle /price command
async def price(update: Update, context: CallbackContext) -> None:
    price_data = await get_btc_price()

    if not price_data:
        await update.message.reply_text("❌ Failed to fetch BTC price. Please try again later.")
        return

    # Formatting the price response
    message = "📊 *Current Bitcoin (BTC) Prices:*\n"
    for currency, value in price_data.items():
        message += f"💰 *{currency}:* {value:,}\n"  # Adds thousands separator

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