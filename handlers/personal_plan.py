from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from config import TIER_LIMITS, GET_INTERVAL, GET_START_TIME
from db.db import get_personal_plans, get_user_tier, count_personal_plans, add_personal_plan
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



async def add_personal_start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    # Validate tier
    tier = await get_user_tier(user_id)
    max_plans, min_interval = TIER_LIMITS.get(tier, (1, 5))
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
    await send_or_edit(update,
            "🕒 *Enter your desired interval in minutes (e.g. 15):*\n"
            "📌 Free tier: ≥5 min, 1 plan\n"
            "📌 Pro tier: ≥1 min, up to 3 plans\n"
            "📌 Ultra tier: ≥1 min, up to 5 plans",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
               [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add_process_personal_p")]
            ])
    )
    return GET_INTERVAL


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
    max_plans, min_interval = TIER_LIMITS.get(tier, (1, 5))

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
    try:
        hour, minute = map(int, text.split(":"))
        assert 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, AssertionError):
        await send_or_edit(update,
               "❌ Invalid time format. Please use *HH:MM* (e.g. *14:30*).",
                       parse_mode="Markdown",
                       reply_markup=reply_markup_cancel
        )
        return GET_START_TIME

    first_fire = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0)
    if first_fire <= datetime.utcnow():  # time already passed today
        first_fire += timedelta(days=1)

    await add_personal_plan(user_id, interval, first_fire)

    await send_or_edit(update,
        f"✅ Custom plan saved:\n"
        f"Every {interval} min, start time: {hour:02}:{minute:02}.",
                       reply_markup=build_personal_sub_keyboard()
    )
    return ConversationHandler.END


async def cancel_add_process_personal_p(update: Update, context: CallbackContext) -> int:
    await send_or_edit(update, "❌ Action cancelled.")
    await open_personal_sub_menu(update, context)
    return ConversationHandler.END