from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from config import CURRENCIES
from db.db import load_user_currencies, save_user_currencies, clear_user_currencies
from util import send_or_edit
from keyboard import build_currency_keyboard

# Handle /set_currency command
async def set_currency_command_click(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    #target = update.message or update.callback_query.message  # ✅ supports both command and button

    await send_or_edit(update,"💱 Select your preferred currencies (toggle below):",
        reply_markup=await build_currency_keyboard(user_id)
    )


async def toggle_currency(update: Update, context: CallbackContext, currency: str) -> None:
    user_id = update.effective_user.id

    preferences = await load_user_currencies(user_id) or []

    if currency in preferences:
        preferences.remove(currency)
    else:
        preferences.append(currency)
    await save_user_currencies(user_id, preferences)

    await send_or_edit(update, reply_markup=await build_currency_keyboard(user_id))


async def confirm_currency_selection(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    selected = await load_user_currencies(user_id)

    # If no currencies selected — default to all
    if not selected:
        await save_user_currencies(user_id, CURRENCIES.copy())
        msg = (
            "✅ *No currencies were selected.*\n"
            "All currencies have been selected by default.\n\n"
            "You can now check live BTC prices using these currencies."
        )
    else:
        msg = (
            f"✅ *Preferences saved!*\n"
            f"You selected: {', '.join(selected)}\n\n"
            "You can now check live BTC prices using these currencies."
        )

    # Add a 📊 Check Price button
    keyboard = [[
        InlineKeyboardButton("📊 Check Price", callback_data="get_price"),
        InlineKeyboardButton("🌐 Change Currency", callback_data="open_currency_menu")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Replace the currency menu with confirmation + price button
    await send_or_edit(update, msg, parse_mode="Markdown", reply_markup=reply_markup)


async def clear_currency_selection(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    await clear_user_currencies(user_id)
    await send_or_edit(update, reply_markup=await build_currency_keyboard(user_id))
