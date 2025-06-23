from datetime import datetime, timedelta, timezone

import pytz
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from timezonefinder import TimezoneFinder

from db.db import get_user_timezone, set_user_timezone
from keyboard import build_time_settings_keyboard
from util import (
    delete_tracked_messages,
    format_utc_offset,
    safe_convo_step,
    send_or_edit,
    validate_time_hhmm,
)

SETUP_METHOD, SET_MANUAL_TIME, SET_TZ_LOCATION = range(3)


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


async def view_time_settings(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    tz_info = await get_user_timezone(user_id)

    if not tz_info["method"]:
        message = "❌ You haven’t set your timezone yet."
    else:
        tz, offset, method = tz_info["timezone"], tz_info["offset_minutes"], tz_info["method"]
        method_display = "shared location 🌍" if method == "location" else "manual input ⌨️"
        offset_caption = format_utc_offset(offset)

        message = (
            f"🕒 *Current Time Settings:*\n\n"
            f"• Method: {method_display}\n"
            f"• Timezone: `{tz or 'N/A'}`\n"
            f"• Offset: {offset_caption}"
        )

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="open_time_settings_menu")]
    ])
    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


@safe_convo_step(menu_func=open_time_settings_menu)
async def request_location(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📍 Share My Location", request_location=True)],
        [KeyboardButton("❌ Cancel")],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    msg: Message = await send_or_edit(update,
                                      "📡 Please share your location to detect your timezone.",
                                      reply_markup=markup)
    context.user_data.setdefault("temporary_msg_ids", []).append(update.callback_query.message.message_id)
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
    return SET_TZ_LOCATION


@safe_convo_step(menu_func=open_time_settings_menu)
async def handle_location(update: Update, context: CallbackContext) -> int:
    context.user_data.setdefault("temporary_msg_ids", []).append(update.message.message_id)
    user = update.effective_user
    location = update.message.location

    tf = TimezoneFinder()
    timezone_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)

    if timezone_name:
        offset = datetime.now(pytz.timezone(timezone_name)).utcoffset().total_seconds() // 60
        await set_user_timezone(user.id, timezone_name, int(offset), "location")

        msg: Message = await send_or_edit(
            update,
            f"✅ Timezone set to `{timezone_name}`.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        await open_time_settings_menu(update, context)
        await delete_tracked_messages(bot=context.bot, chat_id=update.effective_chat.id, user_data=context.user_data)
    else:
        await send_or_edit(
            update,
            "❌ Could not determine timezone from location.",
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


@safe_convo_step(menu_func=open_time_settings_menu)
async def request_manual_time(update: Update, context: CallbackContext) -> int:
    msg: Message = await send_or_edit(
        update,
        "⌨️ Enter your *local time* in `HH:MM` (24-hour format):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_timezone_setup")]]
        ),
    )
    context.user_data["wizard_time_msg_id"] = msg.message_id
    return SET_MANUAL_TIME


@safe_convo_step(menu_func=open_time_settings_menu)
async def process_manual_time(update: Update, context: CallbackContext) -> int:
    context.user_data.setdefault("temporary_msg_ids", []).append(update.message.message_id)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot = context.bot

    user_time = update.message.text.strip()
    validated_time = validate_time_hhmm(user_time)
    if validated_time is None:
        msg: Message = await send_or_edit(
            update, "❌ Invalid format. Use *HH:MM* (e.g. *14:30*).", parse_mode="Markdown"
        )
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        return SET_MANUAL_TIME
    else:
        hour, minute = validated_time

    offset_minutes = calculate_offset(hour, minute)
    await set_user_timezone(user_id, None, offset_minutes, "manual")

    offset_caption = format_utc_offset(offset_minutes)
    msg: Message = await send_or_edit(update, f"✅ Offset set: {offset_caption}")
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)

    # Cleanup previous messages on success
    context.user_data.setdefault("temporary_msg_ids", []).append(context.user_data["wizard_time_msg_id"])
    await delete_tracked_messages(bot, chat_id, context.user_data)
    await open_time_settings_menu(update, context)
    return ConversationHandler.END


def calculate_offset(hour: int, minute: int) -> int:
    now_utc = datetime.now(timezone.utc)
    local_candidate = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_candidate < now_utc:
        local_candidate += timedelta(days=1)
    seconds = (local_candidate - now_utc).total_seconds()
    minutes = seconds / 60.0
    offset_minutes = round(minutes / 5.0) * 5
    return offset_minutes - 1440 if offset_minutes > 720 else offset_minutes


@safe_convo_step(menu_func=open_time_settings_menu)
async def cancel_timezone_setup(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        await delete_tracked_messages(bot=context.bot, chat_id=update.effective_chat.id, user_data=context.user_data)
        await send_or_edit(update, "❌ Action cancelled.")
        await open_time_settings_menu(update, context)
    else:
        context.user_data.setdefault("temporary_msg_ids", []).append(update.message.message_id)
        msg: Message = await send_or_edit(update, "❌ Action cancelled.", reply_markup=ReplyKeyboardRemove())
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        await delete_tracked_messages(bot=context.bot, chat_id=update.effective_chat.id, user_data=context.user_data)

        await open_time_settings_menu(update, context)
    return ConversationHandler.END


timezone_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(request_location, pattern="^set_timezone_location$"),
        CallbackQueryHandler(request_manual_time, pattern="^set_timezone_manual$"),
    ],
    states={
        SET_TZ_LOCATION: [
            MessageHandler(filters.LOCATION, handle_location),
            MessageHandler(filters.TEXT & filters.Regex("^❌ Cancel$"), cancel_timezone_setup),
        ],
        SET_MANUAL_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_manual_time),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_timezone_setup, pattern="^cancel_timezone_setup$")
    ],
)
