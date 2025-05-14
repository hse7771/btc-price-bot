from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from db.db import get_personal_plans
from util import send_or_edit
from keyboard import build_personal_sub_keyboard


async def open_personal_sub_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = build_personal_sub_keyboard()

    await send_or_edit(update,
        "📆 *Manage your personal BTC update plans:*\n\n"
        "⚙️ These are fully customizable timers (e.g., every 7 min, start at 14:00).\n\n"
        "Choose an option below:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def view_personal_plans_command_click(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    plans = await get_personal_plans(user_id)

    if not plans:
        message = (
            "ℹ️ You don’t have any personal BTC plans yet.\n\n"
            "Use ➕ *Add Custom Plan* to create one."
        )
    else:
        rows = []
        for idx, (interval, next_iso) in enumerate(plans, 1):
            next_dt = datetime.fromisoformat(next_iso)
            formatted_time = next_dt.strftime("%H:%M %d.%m.%y")
            rows.append(f"{idx}. ⏱ Every {interval} min, start: {formatted_time}")

        message = "📋 *Your Personal BTC Plans:*\n\n" + "\n".join(rows)

    # Show back to personal plan menu
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="open_personal_sub_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)
