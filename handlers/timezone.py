import pytz

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton, Message
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from timezonefinder import TimezoneFinder
from datetime import datetime, timedelta

from db.db import set_user_timezone
from keyboard import build_time_settings_keyboard
from util import send_or_edit, validate_time_hhmm, safe_delete_message

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


async def request_location(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("📍 Share My Location", request_location=True)],
        [KeyboardButton("❌ Cancel")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    next_msg: Message = await send_or_edit(update,
                       "📡 Please share your location to detect your timezone.",
                       reply_markup=markup)
    if next_msg:
        context.user_data["msg_to_delete_id"] = next_msg.message_id

    previous_msg = update.callback_query.message

    await safe_delete_message(context.bot, previous_msg.chat.id, previous_msg.message_id)
    return SET_TZ_LOCATION


async def handle_location(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    location = update.message.location
    chat_id = update.effective_chat.id
    bot = context.bot
    await safe_delete_message(bot, chat_id, context.user_data["msg_to_delete_id"])

    tf = TimezoneFinder()
    timezone_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)

    if timezone_name:
        offset = datetime.now(pytz.timezone(timezone_name)).utcoffset().total_seconds() // 60
        await set_user_timezone(user.id, timezone_name, int(offset), "location")

        confirm_msg: Message = await send_or_edit(update,
            f"✅ Timezone set to `{timezone_name}`.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await safe_delete_message(bot, chat_id, update.message.message_id, 2)
        await safe_delete_message(bot, chat_id, confirm_msg.message_id, 1)
        await open_time_settings_menu(update, context)
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
    context.user_data["manual_time_prompt_id"] = msg.message_id
    return SET_MANUAL_TIME


async def process_manual_time(update: Update, context: CallbackContext) -> int:
    user_time = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    bot = context.bot
    user_msg_id = update.message.message_id

    validated_time = validate_time_hhmm(user_time)
    if validated_time is None:
        context.user_data.setdefault("manual_time_errors", []).append(user_msg_id)
        error_msg: Message = await send_or_edit(update,
            "❌ Invalid format. Use *HH:MM* (e.g. *14:30*).",
            parse_mode="Markdown"
        )
        context.user_data["manual_time_errors"].append(error_msg.message_id)
        return SET_MANUAL_TIME
    else:
        hour, minute = validated_time

    # Cleanup previous messages on success
    for msg_id in context.user_data.get("manual_time_errors", []):
        await safe_delete_message(bot, chat_id, msg_id)
    context.user_data.pop("manual_time_errors", None)

    await safe_delete_message(bot, chat_id, user_msg_id)
    await safe_delete_message(bot, chat_id, context.user_data["manual_time_prompt_id"])
    context.user_data.pop("manual_time_prompt_id", None)

    now_utc = datetime.utcnow()
    local_candidate = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_candidate < now_utc:
        local_candidate += timedelta(days=1)

    seconds = (local_candidate - now_utc).total_seconds()
    offset_minutes = calculate_offset(seconds)

    await set_user_timezone(user_id, None, offset_minutes, "manual")

    prev_msg: Message = await send_or_edit(update, f"✅ Offset set: UTC{offset_minutes:+} min.")
    await open_time_settings_menu(update, context)
    await safe_delete_message(bot, chat_id, prev_msg.message_id, 1.75)
    return ConversationHandler.END


def calculate_offset(seconds: float) -> int:
    minutes = seconds / 60.0
    offset_minutes = round(minutes / 5.0) * 5
    return offset_minutes - 1440 if offset_minutes > 720 else offset_minutes


async def cancel_timezone_setup(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        await send_or_edit(update, "❌ Action cancelled.")
        await open_time_settings_menu(update, context)
    else:
        chat_id = update.effective_chat.id
        bot = context.bot

        await safe_delete_message(bot, chat_id, update.message.message_id)
        prev_msg: Message = await send_or_edit(update, "❌ Action cancelled.", reply_markup=ReplyKeyboardRemove())
        await safe_delete_message(bot, chat_id, context.user_data["msg_to_delete_id"])
        context.user_data.pop("msg_to_delete_id", None)

        await open_time_settings_menu(update, context)
        await safe_delete_message(bot, chat_id, prev_msg.message_id)
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