import pytz

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton, Message
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from timezonefinder import TimezoneFinder
from datetime import datetime, timedelta

from db.db import set_user_timezone, get_user_timezone
from keyboard import build_time_settings_keyboard
from util import send_or_edit, validate_time_hhmm, safe_delete_message, format_utc_offset, delete_tracked_messages

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

    # You need to implement this DB function if it doesn't exist yet
    tz_info = await get_user_timezone(user_id)  # returns (tz_name or None, offset, method) or None

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


async def request_location(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [KeyboardButton("📍 Share My Location", request_location=True)],
        [KeyboardButton("❌ Cancel")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    msg: Message = await send_or_edit(update,
                       "📡 Please share your location to detect your timezone.",
                       reply_markup=markup)
    context.user_data.setdefault("temporary_msg_ids", []).append(update.callback_query.message.message_id)
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
    return SET_TZ_LOCATION


async def handle_location(update: Update, context: CallbackContext) -> int:
    context.user_data.setdefault("temporary_msg_ids", []).append(update.message.message_id)
    user = update.effective_user
    location = update.message.location

    tf = TimezoneFinder()
    timezone_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)

    if timezone_name:
        offset = datetime.now(pytz.timezone(timezone_name)).utcoffset().total_seconds() // 60
        await set_user_timezone(user.id, timezone_name, int(offset), "location")

        msg: Message = await send_or_edit(update,
            f"✅ Timezone set to `{timezone_name}`.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        await open_time_settings_menu(update, context)
        await delete_tracked_messages(bot=context.bot, chat_id=update.effective_chat.id, user_data=context.user_data)
    else:

        await send_or_edit(update,"❌ Could not determine timezone from location.",
                                        reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def request_manual_time(update: Update, context: CallbackContext) -> int:
    msg: Message = await send_or_edit(update,
        "⌨️ Enter your *local time* in `HH:MM` (24-hour format):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_timezone_setup")]
        ])
    )
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
    return SET_MANUAL_TIME


async def process_manual_time(update: Update, context: CallbackContext) -> int:
    context.user_data.setdefault("temporary_msg_ids", []).append(update.message.message_id)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot = context.bot

    user_time = update.message.text.strip()
    validated_time = validate_time_hhmm(user_time)
    if validated_time is None:
        msg: Message = await send_or_edit(update,
            "❌ Invalid format. Use *HH:MM* (e.g. *14:30*).",
            parse_mode="Markdown"
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
    await delete_tracked_messages(bot, chat_id, context.user_data)
    await open_time_settings_menu(update, context)
    return ConversationHandler.END


def calculate_offset(hour: int, minute: int) -> int:
    now_utc = datetime.utcnow()
    local_candidate = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_candidate < now_utc:
        local_candidate += timedelta(days=1)
    seconds = (local_candidate - now_utc).total_seconds()
    minutes = seconds / 60.0
    offset_minutes = round(minutes / 5.0) * 5
    return offset_minutes - 1440 if offset_minutes > 720 else offset_minutes


async def cancel_timezone_setup(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
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
                CallbackQueryHandler(cancel_timezone_setup, pattern= "^cancel_timezone_setup$"),
            ],
        },
        fallbacks=[],
    )