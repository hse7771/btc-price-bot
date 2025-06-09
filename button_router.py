from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from config import CURRENCIES, PREDEFINED_INTERVALS, TierConvertFromNumber, PROVIDERS
from handlers.donate import open_donate_menu
from handlers.price import get_price_command_click, refresh_price_click
from handlers.currency import (set_currency_command_click, toggle_currency, confirm_currency_selection,
                               clear_currency_selection)
from handlers.base_plan import (open_base_sub_menu_command_click, subscribe_base_command_click,
                                unsubscribe_base_command_click, confirm_base_sub, confirm_unbase_sub)
from handlers.personal_plan import open_personal_sub_menu, view_personal_plans_command_click, open_cancel_personal_menu
from handlers.core import open_main_menu
from handlers.timezone import open_time_settings_menu, view_time_settings
from handlers.upgrade import open_upgrade_menu, upgrade_to_pro, upgrade_to_ultra
from services.payment import send_invoice
from util import send_or_edit


def initialize_button_handlers():
    # Map callback_data to handlers
    handlers = {
        "get_price": get_price_command_click,
        "refresh_price": refresh_price_click,
        "open_currency_menu": set_currency_command_click,
        "close_menu": confirm_currency_selection,
        "currency_clear": clear_currency_selection,
        "open_main_menu": open_main_menu,
        "open_base_sub_menu": open_base_sub_menu_command_click,
        "subscribe_base": subscribe_base_command_click,
        "unsubscribe_base": unsubscribe_base_command_click,
        "open_personal_sub_menu": open_personal_sub_menu,
        "view_personal": view_personal_plans_command_click,
        "open_cancel_personal_menu": open_cancel_personal_menu,
        "open_time_settings_menu": open_time_settings_menu,
        "view_time_settings": view_time_settings,
        "open_upgrade_menu": open_upgrade_menu,
        "upgrade_pro": upgrade_to_pro,
        "upgrade_ultra": upgrade_to_ultra,
        "open_donate_menu": open_donate_menu,
    }
    # Dynamic handlers for currency toggles
    for currency in CURRENCIES:
        handlers[f"toggle_{currency}"] = lambda u, c, curr=currency: toggle_currency(u, c, curr)
    # Dynamic handlers for base/unbase subscription per interval
    for interval in PREDEFINED_INTERVALS:
        handlers[f"base_{interval}"] = lambda u, c, i=interval: confirm_base_sub(u, c, i)
        handlers[f"unbase_{interval}"] = lambda u, c, i=interval: confirm_unbase_sub(u, c, i)
    # Dynamic handlers for different providers and tiers (upgrade)
    for tier in TierConvertFromNumber:
        for provider, currency in PROVIDERS.items():
            key = f"pay_{tier.name.lower()}_{provider}"
            handlers[key] = lambda u, c, t=tier, p=provider, cur=currency, op_t="sub": (
                send_invoice(u, c, tier_type=t, provider=p, currency=cur, op_t=op_t))
    # Dynamic handlers for different providers (donate)
    for provider, currency in PROVIDERS.items():
        key = f"donate_{provider}"
        handlers[key] = lambda u, c, t=TierConvertFromNumber.FREE, p=provider, cur=currency, op_t="donate": (
            send_invoice(u, c, tier_type=t, provider=p, currency=cur, op_t=op_t))

    return handlers


BUTTON_HANDLERS = initialize_button_handlers()


async def button_click_handler(update: Update, context: CallbackContext) -> None:
    """Handles button press for 📊 Price."""
    query = update.callback_query
    await query.answer()  # Acknowledge button press to Telegram

    handler = BUTTON_HANDLERS.get(query.data)
    if handler:
        await handler(update, context)
    else:
        await send_or_edit(update,
                           "❓ Unknown action.",
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton("🏠 Main Menu", callback_data="open_main_menu")]
                           ])
                           )
