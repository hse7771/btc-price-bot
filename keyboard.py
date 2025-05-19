from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import CURRENCIES
from db.db import load_user_currencies


def build_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 Price", callback_data="get_price")],
        [InlineKeyboardButton("💱 Change Currency", callback_data="open_currency_menu")],
        [InlineKeyboardButton("🔔 Base Plan", callback_data="open_base_sub_menu")],
        [InlineKeyboardButton("📆 Personal Plan", callback_data="open_personal_sub_menu")],
        [InlineKeyboardButton("🌍 Time Settings", callback_data="open_time_settings_menu")],
        [InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def build_currency_keyboard(user_id: int) -> InlineKeyboardMarkup:
    selected = set(await load_user_currencies(user_id) or [])
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


def build_price_keyboard(label_first_button: str = "📊 Check Price", callback_first_button: str = "get_price") -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(label_first_button, callback_data=callback_first_button)],
        [InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")],
        [InlineKeyboardButton("⬅️ Back", callback_data="open_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_base_sub_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔔 Subscribe", callback_data="subscribe_base")],
        [InlineKeyboardButton("🛑 Unsubscribe", callback_data="unsubscribe_base")],
        [InlineKeyboardButton("⬅️ Back", callback_data="open_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_personal_sub_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📋 View My Plans", callback_data="view_personal")],
        [InlineKeyboardButton("➕ Add Custom Plan", callback_data="add_personal")],
        [InlineKeyboardButton("❌ Cancel Plan", callback_data="open_cancel_personal_menu")],
        [InlineKeyboardButton("💳 Upgrade", callback_data="upgrade")],
        [InlineKeyboardButton("⬅️ Back", callback_data="open_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
