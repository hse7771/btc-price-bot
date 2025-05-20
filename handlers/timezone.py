from telegram import Update
from telegram.ext import CallbackContext

from keyboard import build_time_settings_keyboard
from util import send_or_edit


async def open_time_settings_menu(update: Update, context: CallbackContext) -> None:
    """Displays the time settings menu with options to share location or enter local time manually."""

    message = (
        "🕒 *Time Settings*\n\n"
        "Choose how you'd like to configure your local time:\n\n"
        "📍 Share location – to determine accurate timezone with DST support\n"
        "⌨️ Enter your local time manually – confidential location, but DST may be inaccurate"
    )

    reply_markup = build_time_settings_keyboard()

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)
