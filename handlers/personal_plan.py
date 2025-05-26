from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, \
    filters

from db.db import get_personal_plans, get_user_tier, count_personal_plans, add_personal_plan, delete_personal_plan, \
    get_user_timezone
from config import TIER_LIMITS, FREE_TIER, PRO_TIER, ULTRA_TIER, TierConvertFromNumber
from handlers.timezone import open_time_settings_menu
from util import send_or_edit, convert_utc_to_local, convert_local_to_utc, validate_time_hhmm
from keyboard import build_personal_sub_keyboard


GET_INTERVAL, GET_START_TIME = range(2)

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
        tz_data = await get_user_timezone(user_id)
        rows = []
        for idx, (plan_id, interval, next_iso) in enumerate(plans, 1):
            first_dt_utc = datetime.fromisoformat(next_iso)
            first_dt_local = convert_utc_to_local(first_dt_utc, tz_data)
            formatted_time = first_dt_local.strftime("%H:%M %d.%m.%y")
            rows.append(f"{idx}. ⏱ Every {interval} min, start: {formatted_time}")

        message = "📋 *Your Personal BTC Plans:*\n\n" + "\n".join(rows)

    # Show back to personal plan menu
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="open_personal_sub_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)



async def add_personal_start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id

    # Validate tier
    tier = await get_user_tier(user_id)
    tier_limit = TIER_LIMITS.get(TierConvertFromNumber(tier), FREE_TIER)
    max_plans, min_interval = tier_limit.amount, tier_limit.interval

    existing = await count_personal_plans(user_id)

    if existing >= max_plans:
        await send_or_edit(update,
                           f"❌ You’ve reached your plan limit ({max_plans}).\n"
                           f"Upgrade your tier to add more.",
                           reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton("💳 Upgrade", callback_data="upgrade")],
                                            [InlineKeyboardButton("⬅️ Back", callback_data="open_personal_sub_menu")]
                           ])
                           )
        return ConversationHandler.END

    context.user_data["tier"] = tier
    buttons = [
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add_process_personal_p")]
    ]
    # ⚠️ Warn if no timezone configured
    tz_data = await get_user_timezone(user_id)
    warning = ""
    if tz_data["method"] is None:
        warning = (
                    "⚠️ *Heads up!* You haven’t set your timezone yet.\n"
                    "Notifications may fire at the wrong local time.\n\n"
        )
        buttons.insert(0,
            [InlineKeyboardButton("🌍 Time Settings", callback_data="open_time_settings_menu_wrapper")]
        )
    reply_markup = InlineKeyboardMarkup(buttons)
    await send_or_edit(update,
            warning +
            "🕒 *Enter your desired interval in minutes (e.g. 15):*\n"
            f"📌 Free tier: ≥{FREE_TIER.interval} min, {FREE_TIER.amount} plan\n"
            f"📌 Pro tier: ≥{PRO_TIER.interval} min, up to {PRO_TIER.amount} plans\n"
            f"📌 Ultra tier: ≥{ULTRA_TIER.interval} min, up to {ULTRA_TIER.amount} plans",
            parse_mode="Markdown",
            reply_markup=reply_markup
    )
    return GET_INTERVAL


async def open_time_settings_menu_wrapper(update: Update, context: CallbackContext) -> int:
    await open_time_settings_menu(update, context)
    return ConversationHandler.END


async def add_personal_interval(update: Update, context: CallbackContext) -> int:
    reply_markup_cancel = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add_process_personal_p")]
    ])
    try:
        interval = int(update.message.text.strip())
    except ValueError:
        await send_or_edit(update,
               "❌ Please enter a valid number (e.g. 15).",
               reply_markup=reply_markup_cancel
        )
        return GET_INTERVAL

    tier = context.user_data.get("tier", 0)
    tier_limit = TIER_LIMITS.get(TierConvertFromNumber(tier), FREE_TIER)
    max_plans, min_interval = tier_limit.amount, tier_limit.interval

    if interval < min_interval:
        await send_or_edit(update,
                           f"❌ Your minimum allowed interval is {min_interval} min.\n"
                           f"Try again with a higher value.",
                           reply_markup=reply_markup_cancel
                           )
        return GET_INTERVAL


    # Valid → store in context
    context.user_data["interval"] = interval
    await send_or_edit(update,
                       "📍 Now enter the start time in *HH:MM* format (e.g. 14:30):",
                       reply_markup=reply_markup_cancel,
                       parse_mode="Markdown"
                       )
    return GET_START_TIME


async def add_personal_start_time(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    interval = context.user_data["interval"]

    reply_markup_cancel = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add_process_personal_p")]
    ])

    # Validate time format
    validated_time = validate_time_hhmm(text)
    if validated_time is None:
        await send_or_edit(update,
                           "❌ Invalid time format. Please use *HH:MM* (e.g. *14:30*).",
                           parse_mode="Markdown",
                           reply_markup=reply_markup_cancel
                           )
        return GET_START_TIME
    else:
        hour, minute = validated_time


    # 🔄 Load user tz & compute first_fire in UTC
    tz_data = await get_user_timezone(user_id)
    utc_now = datetime.utcnow()
    local_now = convert_utc_to_local(utc_now, tz_data)
    first_local = local_now.replace(hour=hour, minute=minute,
                                    second=0, microsecond=0)
    if first_local <= local_now:  # already passed today → tomorrow
        first_local += timedelta(days=1)

    first_fire = convert_local_to_utc(first_local, tz_data)
    await add_personal_plan(user_id, interval, first_fire.isoformat(" "))

    await send_or_edit(update,
        f"✅ Custom plan saved:\n"
        f"Every *{interval}* min, start: *{hour:02}:{minute:02}*.",
                       reply_markup=build_personal_sub_keyboard(),
                       parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel_add_process_personal_p(update: Update, context: CallbackContext) -> int:
    await send_or_edit(update, "❌ Action cancelled.")
    await open_personal_sub_menu(update, context)
    return ConversationHandler.END


async def open_cancel_personal_menu(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    plans = await get_personal_plans(user_id)

    if not plans:
        await send_or_edit(update, "📭 You don’t have any personal plans to cancel.")
        await open_personal_sub_menu(update, context)
        return

    message = "🗑️ Select a plan to cancel:"
    buttons = []

    for plan_id, interval, first_fire_time in plans:
        next_dt = datetime.fromisoformat(first_fire_time)
        formatted_time = next_dt.strftime("%H:%M %d.%m.%y")
        buttons.append([
            InlineKeyboardButton(
                f"❌ ⏱ Every {interval} min, {formatted_time} ",
                callback_data=f"cancel_personal_plan_{plan_id}"
            )
        ])

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="open_personal_sub_menu")])
    reply_markup = InlineKeyboardMarkup(buttons)

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


async def cancel_personal_plan(update: Update, context: CallbackContext):
    plan_id = int(update.callback_query.data.split("_")[-1])

    await delete_personal_plan(plan_id)

    await send_or_edit(update, "✅ Plan cancelled.")
    await open_personal_sub_menu(update, context)


add_personal_conversation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_personal_start, pattern="^add_personal$"),
                      CommandHandler("add_personal", add_personal_start)],
        states={
            GET_INTERVAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_personal_interval),
                CallbackQueryHandler(cancel_add_process_personal_p, pattern= "^cancel_add_process_personal_p$"),
                CallbackQueryHandler(open_time_settings_menu_wrapper, pattern= "^open_time_settings_menu_wrapper$"),
            ],
            GET_START_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_personal_start_time),
                CallbackQueryHandler(cancel_add_process_personal_p, pattern= "^cancel_add_process_personal_p$"),
            ],
        },
        fallbacks=[],
    )