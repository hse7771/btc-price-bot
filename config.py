import os
from dataclasses import dataclass
from enum import IntEnum

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

@dataclass(frozen=True)
class TierLimit:
    amount: int      # max personal plans
    interval: int    # minimum interval (minutes)


class TierConvertFromNumber(IntEnum):
    FREE  = 0
    PRO   = 1
    ULTRA = 2


FREE_TIER = TierLimit(amount=1, interval=5)
PRO_TIER = TierLimit(amount=3, interval=1)
ULTRA_TIER = TierLimit(amount=5, interval=1)

TIER_LIMITS: dict[TierConvertFromNumber, TierLimit] = {
    TierConvertFromNumber.FREE: FREE_TIER,
    TierConvertFromNumber.PRO: PRO_TIER,
    TierConvertFromNumber.ULTRA: ULTRA_TIER,
}