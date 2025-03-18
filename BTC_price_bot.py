import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Check if the token is loaded correctly
if not TOKEN:
    raise ValueError("ERROR: Telegram Bot Token is missing. Please check your .env file.")
