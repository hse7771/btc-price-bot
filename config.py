import os
from dataclasses import dataclass
from enum import IntEnum

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RU_TEST_TOKEN = os.getenv("UKASSA_TEST_TOKEN")
RU_REAL_TOKEN = os.getenv("UKASSA_REAL_TOKEN")
INTERNATIONAL_TEST_TOKEN = os.getenv("AMMER_PAY_TEST_TOKEN")
INTERNATIONAL_REAL_TOKEN = os.getenv("AMMER_PAY_REAL_TOKEN")

# List of currencies we will support
CURRENCIES = ["USD", "RUB", "EUR", "CAD", "GBP", "CNY"]
BLOCKCHAIN_API = "https://blockchain.info/ticker"
COINGECKO_API = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={','.join(CURRENCIES)}"
PREDEFINED_INTERVALS = [15, 30, 60, 240, 1440]  # In minutes
FETCH_INTERVAL = 60  # seconds
EXPIRY_SECONDS = 300


@dataclass(frozen=True)
class Provider:
    region: str
    currency: str
    provider: str


@dataclass(frozen=True)
class PriceInfo:
    currency: str  # Symbol like "$"
    amount: float


@dataclass(frozen=True)
class Tier:
    name: str
    price: dict[str, PriceInfo]  # Free tier has no price
    mx_personal_plans: int
    mn_interval: int
    emoji: str


class TierConvertFromNumber(IntEnum):
    FREE = 0
    PRO = 1
    ULTRA = 2


FREE_TIER = Tier(
    name="Free",
    price={
        "RUB": PriceInfo(currency="₽", amount=0),
        "USD": PriceInfo(currency="$", amount=0)
    },
    mx_personal_plans=1,
    mn_interval=5,
    emoji=""
)

PRO_TIER = Tier(
    name="Pro",
    price={
        "RUB": PriceInfo(currency="₽", amount=150),
        "USD": PriceInfo(currency="$", amount=1.99)
    },
    mx_personal_plans=3,
    mn_interval=1,
    emoji="⚡"
)
ULTRA_TIER = Tier(name="Ultra",
                  price={
                      "RUB": PriceInfo(currency="₽", amount=350),
                      "USD": PriceInfo(currency="$", amount=4.99)
                  },
                  mx_personal_plans=5,
                  mn_interval=1,
                  emoji="🚀"
                  )

TIERS: dict[TierConvertFromNumber, Tier] = {
    TierConvertFromNumber.FREE: FREE_TIER,
    TierConvertFromNumber.PRO: PRO_TIER,
    TierConvertFromNumber.ULTRA: ULTRA_TIER,
}

PROVIDERS = {
    "yoomoney": Provider(region="RU", currency="RUB", provider="yoomoney"),
    "ammer_pay": Provider(region="INT", currency="USD", provider="ammer_pay"),
}

TIER_NAMES = {"pro", "ultra"}
