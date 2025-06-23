from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from config import PREDEFINED_INTERVALS
from db.db import (
    add_base_subscription,
    get_user_base_subscriptions,
    remove_base_subscription,
)
from keyboard import build_base_sub_keyboard
from util import send_or_edit


async def open_base_sub_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = build_base_sub_keyboard()

    await send_or_edit(
        update,
        "📅 *Manage your base BTC price subscriptions:*\n\n"
        "🕑 These are standard intervals (15 min, 30 min, 60 min, 4 h, 24 h) sent on the *UTC* clock.\n\n"
        "Choose the options below:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def subscribe_base(update: Update, context: CallbackContext):
    await open_base_intervals(
        update,
        message_text="📅 Choose how often you want BTC price updates:",
        callback_prefix="base_",
    )


async def unsubscribe_base(update: Update, context: CallbackContext):
    await open_base_intervals(
        update, message_text="⚙️ Choose interval to unsubscribe:", callback_prefix="unbase_"
    )


async def open_base_intervals(update: Update, message_text: str, callback_prefix: str):
    user_id = update.effective_user.id
    labels = {
        "base_": "⏰ Every {}",
        "unbase_": "❌ Cancel {} updates",
    }
    label_template = labels.get(callback_prefix, "⏰ Every {}")  # fallback for safety

    user_subs = await get_user_base_subscriptions(user_id)  # list of intervals
    intervals = PREDEFINED_INTERVALS

    if callback_prefix.startswith("unbase_"):
        if not user_subs:
            await send_or_edit(
                update,
                "🚫 You have no active subscriptions to cancel.",
                reply_markup=build_base_sub_keyboard(),
            )
            return
        intervals = user_subs
    elif callback_prefix.startswith("base_"):
        if len(user_subs) >= len(PREDEFINED_INTERVALS):
            await send_or_edit(
                update,
                "✅ You are already subscribed to all available intervals!",
                reply_markup=build_base_sub_keyboard(),
            )
            return
        intervals = [i for i in PREDEFINED_INTERVALS if i not in user_subs]

    keyboard = [
        [InlineKeyboardButton(label_template.format(format_interval(i)), callback_data=f"{callback_prefix}{i}")]
        for i in intervals
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="open_base_sub_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_or_edit(update, message_text, reply_markup=reply_markup)


async def confirm_base_sub(update, context, interval):
    user_id = update.effective_user.id
    await add_base_subscription(user_id, interval)
    reply_markup = build_base_sub_keyboard()

    await send_or_edit(
        update,
        f"✅ Subscribed to updates every {format_interval(interval)}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def confirm_unbase_sub(update, context, interval):
    user_id = update.effective_user.id
    await remove_base_subscription(user_id, interval)
    reply_markup = build_base_sub_keyboard()

    await send_or_edit(
        update,
        f"❌ Unsubscribed from {format_interval(interval)} updates",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


def format_interval(interval: int) -> str:
    """Formats the interval for user-friendly display."""
    if interval % 1440 == 0:  # Full days
        days = interval // 1440
        return f"{days} day{'s' if days > 1 else ''}"
    elif interval % 60 == 0:  # Full hours
        hours = interval // 60
        return f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        return f"{interval} minutes"
