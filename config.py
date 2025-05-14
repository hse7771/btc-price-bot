import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# List of currencies we will support
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP", "CNY"]
BLOCKCHAIN_API = "https://blockchain.info/ticker"
COINGECKO_API = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={','.join(CURRENCIES)}"
PREDEFINED_INTERVALS = [15, 30, 60, 240, 1440]  # In minutes
FETCH_INTERVAL = 60   # seconds
