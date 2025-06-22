from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import FREE_TIER, PRO_TIER, TIERS, ULTRA_TIER, TierConvertFromNumber
from db.db import (
    add_personal_plan,
    count_personal_plans,
    delete_personal_plan,
    get_personal_plans,
    get_user_tier,
    get_user_timezone,
)
from handlers.timezone import open_time_settings_menu
from keyboard import build_personal_sub_keyboard
from util import (
    convert_local_to_utc,
    convert_utc_to_local,
    delete_tracked_messages,
    safe_convo_step,
    send_or_edit,
    validate_time_hhmm,
)

GET_INTERVAL, GET_START_TIME = range(2)


async def open_personal_sub_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = build_personal_sub_keyboard()

    await send_or_edit(
        update,
        "📆 *Manage your personal BTC update plans:*\n\n"
        "⚙️ These are fully customizable local-time timers (e.g. every 7 min, start at 14:00).\n"
        "They always respect the timezone you set.\n\n"
        "Choose an option below:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
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


@safe_convo_step(menu_func=open_personal_sub_menu)
async def add_personal_start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    # Validate tier
    tier = await get_user_tier(user_id)
    tier_info = TIERS.get(TierConvertFromNumber(tier), FREE_TIER)
    max_plans = tier_info.mx_personal_plans

    existing = await count_personal_plans(user_id)

    if existing >= max_plans:
        await send_or_edit(update,
                           "❌ You’ve reached your plan limit or your subscription has expired.\n"
                           "Upgrade or renew your tier to add more.",
                           reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("💳 Upgrade", callback_data="open_upgrade_menu")],
                                    [InlineKeyboardButton("⬅️ Back", callback_data="open_personal_sub_menu")]
                           ])
                           )
        return ConversationHandler.END

    context.user_data["tier"] = tier
    buttons = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_add_process_personal_p")]]
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
    msg = await send_or_edit(update,
                             warning +
                             "🕒 *Enter your desired interval in minutes (e.g. 15):*\n"
                             f"📌 Free tier: ≥{FREE_TIER.mn_interval} min, {FREE_TIER.mx_personal_plans} plan\n"
                             f"📌 Pro tier: ≥{PRO_TIER.mn_interval} min, up to {PRO_TIER.mx_personal_plans} plans\n"
                             f"📌 Ultra tier: ≥{ULTRA_TIER.mn_interval} min, up to {ULTRA_TIER.mx_personal_plans} plans",
                             parse_mode="Markdown",
                             reply_markup=reply_markup
                             )
    context.user_data["wizard_msg_id"] = msg.message_id
    return GET_INTERVAL


async def open_time_settings_menu_wrapper(update: Update, context: CallbackContext) -> int:
    await open_time_settings_menu(update, context)
    return ConversationHandler.END


@safe_convo_step(menu_func=open_personal_sub_menu)
async def add_personal_interval(update: Update, context: CallbackContext) -> int:
    msg = update.message
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)

    try:
        interval = int(update.message.text.strip())
    except ValueError:
        msg = await send_or_edit(update, "❌ Please enter a valid number (e.g. 15).")
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        return GET_INTERVAL

    tier = context.user_data.get("tier", 0)
    tier_info = TIERS.get(TierConvertFromNumber(tier), FREE_TIER)
    min_interval = tier_info.mn_interval

    if interval < min_interval:
        msg = await send_or_edit(
            update,
            f"❌ Your minimum allowed interval is {min_interval} min.\n"
            f"Try again with a higher value.",
        )
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        return GET_INTERVAL

    # Valid → store in context
    context.user_data["interval"] = interval
    msg = await send_or_edit(update,
                             "📍 Now enter the start time in *HH:MM* format (e.g. 14:30):", parse_mode="Markdown")
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
    return GET_START_TIME


@safe_convo_step(menu_func=open_personal_sub_menu)
async def add_personal_start_time(update: Update, context: CallbackContext) -> int:
    msg = update.message
    context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)

    user_id = update.effective_user.id
    text = update.message.text.strip()
    interval = context.user_data["interval"]

    # Validate time format
    validated_time = validate_time_hhmm(text)
    if validated_time is None:
        msg = await send_or_edit(
            update,
            "❌ Invalid time format. Please use *HH:MM* (e.g. *14:30*).",
            parse_mode="Markdown",
        )
        context.user_data.setdefault("temporary_msg_ids", []).append(msg.message_id)
        return GET_START_TIME
    else:
        hour, minute = validated_time

    # 🔄 Load user tz & compute first_fire in UTC
    tz_data = await get_user_timezone(user_id)
    utc_now = datetime.now(timezone.utc)
    local_now = convert_utc_to_local(utc_now, tz_data)
    first_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if first_local <= local_now:  # already passed today → tomorrow
        first_local += timedelta(days=1)

    first_fire = convert_local_to_utc(first_local, tz_data)
    await add_personal_plan(user_id, interval, first_fire.isoformat(" "))

    await send_or_edit(
        update,
        f"✅ Custom plan saved:\n" f"Every *{interval}* min, start: *{hour:02}:{minute:02}*.",
        reply_markup=build_personal_sub_keyboard(),
        parse_mode="Markdown",
    )
    context.user_data.setdefault("temporary_msg_ids", []).append(context.user_data["wizard_msg_id"])
    await delete_tracked_messages(bot=context.bot, chat_id=update.effective_chat.id, user_data=context.user_data)
    return ConversationHandler.END


@safe_convo_step(menu_func=open_personal_sub_menu)
async def cancel_add_process_personal_p(update: Update, context: CallbackContext) -> int:
    await delete_tracked_messages(bot=context.bot, chat_id=update.effective_chat.id, user_data=context.user_data)
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
    tz_data = await get_user_timezone(user_id)
    for plan_id, interval, first_fire_time in plans:
        first_dt_utc = datetime.fromisoformat(first_fire_time)
        first_dt_local = convert_utc_to_local(first_dt_utc, tz_data)
        formatted_time = first_dt_local.strftime("%H:%M %d.%m.%y")
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
    entry_points=[
        CallbackQueryHandler(add_personal_start, pattern="^add_personal$"),
        CommandHandler("add_personal", add_personal_start),
    ],
    states={
        GET_INTERVAL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_personal_interval),
            CallbackQueryHandler(
                open_time_settings_menu_wrapper, pattern="^open_time_settings_menu_wrapper$"
            ),
        ],
        GET_START_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_personal_start_time),
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_add_process_personal_p, pattern="^cancel_add_process_personal_p$"),
    ],
)
