import os
from dataclasses import dataclass
from enum import IntEnum

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
UKASSA_TEST_TOKEN = os.getenv("UKASSA_TEST_TOKEN")
UKASSA_REAL_TOKEN = os.getenv("UKASSA_REAL_TOKEN")
SMART_GLOCAL_TEST_TOKEN = os.getenv("SMARTGLOCAL_TEST_TOKEN")
SMART_GLOCAL_REAL_TOKEN = os.getenv("SMARTGLOCAL_REAL_TOKEN")

# List of currencies we will support
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP", "CNY"]
BLOCKCHAIN_API = "https://blockchain.info/ticker"
COINGECKO_API = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={','.join(CURRENCIES)}"
PREDEFINED_INTERVALS = [15, 30, 60, 240, 1440]  # In minutes
FETCH_INTERVAL = 60   # seconds

@dataclass(frozen=True)
class Tier:
    name: str
    price: str | None  # Free tier has no price
    mx_personal_plans: int
    mn_interval: int
    emoji: str



class TierConvertFromNumber(IntEnum):
    FREE  = 0
    PRO   = 1
    ULTRA = 2


FREE_TIER = Tier(name="Free", price=None, mx_personal_plans=1, mn_interval=5, emoji="")
PRO_TIER = Tier(name="Pro", price="$1.99 / month", mx_personal_plans=3, mn_interval=1, emoji="⚡")
ULTRA_TIER = Tier(name="Ultra", price="$4.99 / month", mx_personal_plans=5, mn_interval=1, emoji="🚀")

TIERS: dict[TierConvertFromNumber, Tier] = {
    TierConvertFromNumber.FREE: FREE_TIER,
    TierConvertFromNumber.PRO: PRO_TIER,
    TierConvertFromNumber.ULTRA: ULTRA_TIER,
}
