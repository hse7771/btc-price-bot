import os
import requests
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Set up logging for debugging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# List of currencies we will support
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP"]


# Function to fetch BTC price from Binance
def get_price_binance():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP failures
        data = response.json()
        return float(data["price"])  # Return BTC price in USD
    except requests.exceptions.RequestException as e:
        logging.error(f"Binance API failed: {e}")
        return None  # Return None if Binance API is unavailable


# Function to fetch BTC price from CoinGecko (supports multiple currencies)
def get_price_coingecko():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,rub,eur,cad,gbp"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["bitcoin"]  # Returns a dictionary with multiple currency values
    except requests.exceptions.RequestException as e:
        logging.error(f"CoinGecko API failed: {e}")
        return None  # Return None if CoinGecko API is unavailable


# Function to get BTC price with failover mechanism
def get_btc_price():
    coingecko_data = get_price_coingecko()
    if coingecko_data:
        return coingecko_data  # If CoinGecko works, return its data

    binance_price = get_price_binance()
    if binance_price:
        return {"USD": binance_price}  # Binance provides only USD price

    return None  # Return None if both APIs fail