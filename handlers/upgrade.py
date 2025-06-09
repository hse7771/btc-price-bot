import logging
from datetime import datetime, timedelta
from time import time

from telegram import Update, LabeledPrice
from telegram.ext import CallbackContext, ContextTypes

from db.db import get_user_tier, update_user_tier, get_expired_subscriptions, downgrade_user, get_personal_plans, delete_personal_plan
from handlers.personal_plan import open_personal_sub_menu
from keyboard import build_upgrade_keyboard, build_upgrade_payment_keyboard
from util import send_or_edit, safe_delete_message
from config import TIERS, TierConvertFromNumber, EXPIRY_SECONDS

SUB_DURATION_DAYS = 30
GRACE_PERIOD = 24 * 3600

async def open_upgrade_menu(update: Update, context: CallbackContext) -> None:
    """Displays the upgrade menu with available tiers and user’s current status."""

    user_id = update.effective_user.id
    tier_name = await get_user_tier(user_id)
    tier = TIERS[TierConvertFromNumber(tier_name)]

    message_lines = [
        "💳 *Upgrade Your Plan*\n",
        f"You're currently on: *{tier.name} Tier*\n",
        "Here are the available upgrades:\n"
    ]
    tier_suggestion_lines = []
    for tier_key in (TierConvertFromNumber.PRO, TierConvertFromNumber.ULTRA):
        tier = TIERS[tier_key]
        if tier_key <= TierConvertFromNumber(tier_name):
            continue  # Skip showing current tier as an upgrade option

        tier_suggestion_lines.append(
            f"{tier.emoji} *{tier.name} Tier* – {tier.price['USD'].currency}{tier.price['USD'].amount} / month\n"
            f"  • {tier.mx_personal_plans} personal plans\n"
            f"  • Min interval: {tier.mn_interval} min\n"
        )
    if not tier_suggestion_lines:
        tier_suggestion_lines.append("\n*🚀 You’re already on the highest tier. Thank you! 🙏*\n\n")
    message_lines.extend(tier_suggestion_lines)
    message_lines.append("⏳ Subscriptions are *manual* and expire after 30 days.\nYou can renew at any time.")

    message = "\n".join(message_lines)
    reply_markup = build_upgrade_keyboard()

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


async def upgrade_to_pro(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    current_tier = await get_user_tier(user_id)

    if current_tier == TierConvertFromNumber.PRO or current_tier == TierConvertFromNumber.ULTRA:
        await send_or_edit(update,
                           f"✅ You are already on *{TIERS[TierConvertFromNumber(current_tier)].name}* tier.",
                           parse_mode="Markdown")
        await open_upgrade_menu(update, context)
        return

    # Proceed to send payment invoice (next step)
    reply_markup = build_upgrade_payment_keyboard(tier_type="pro")
    msg = await send_or_edit(
        update,
        "💳 Choose a payment method for *Pro* tier:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.chat_data["previous_upgrade_menu_msg_id"] = msg.message_id


async def upgrade_to_ultra(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    current_tier = await get_user_tier(user_id)

    if current_tier == TierConvertFromNumber.ULTRA:
        await send_or_edit(update, "✅ You are already on *Ultra* tier.", parse_mode="Markdown")
        await open_upgrade_menu(update, context)
        return

    # Proceed to send payment invoice (next step)
    reply_markup = build_upgrade_payment_keyboard(tier_type="ultra")
    msg = await send_or_edit(
        update,
        "💳 Choose a payment method for *Ultra* tier:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.chat_data["previous_upgrade_menu_msg_id"] = msg.message_id


async def send_invoice_upgrade(update: Update, context: CallbackContext, tier_type: TierConvertFromNumber,
                               provider: str, currency: str, provider_token: str) -> int:
    user_id = update.effective_user.id
    tier = TIERS[tier_type]

    operation_type = "sub"
    payload = f"operation_type={operation_type}&tier={tier.name.lower()}&provider={provider}&user={user_id}&timestamp={int(time())}"
    description = (
            f"{tier.name} features will be unlocked for 30 days.\n"
            f"Invoice is valid for {EXPIRY_SECONDS // 60} minutes and will automatically expire after that."
        )
    msg = await context.bot.send_invoice(
        chat_id         = user_id,
        title           = f"{tier.name} Tier Subscription",
        description     = description,
        payload         = payload,
        provider_token  = provider_token,
        currency        = currency,
        prices          = [LabeledPrice(f"{tier.name} Tier – Monthly", int(100 * tier.price[currency].amount))],
        start_parameter = f"{tier.name.lower()}{user_id}",
        need_name       = True,
    )
    return msg.message_id


async def handle_successful_upgrade_payment(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                            user_id: int, new_tier: TierConvertFromNumber) -> None:
    # 3. Upgrade the user tier
    expiry_dt = datetime.utcnow() + timedelta(days=SUB_DURATION_DAYS)
    expiry_iso = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
    await update_user_tier(user_id, new_tier, expiry_iso)

    # 4. Confirm to user
    msg = await send_or_edit(update,
                             "✅ Payment successful! Your subscription has been activated.")
    await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id, msg_id=msg.message_id, delay=5)
    await open_personal_sub_menu(update, context)
    prev_id = context.chat_data.get("previous_upgrade_menu_msg_id")
    if prev_id:
        await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id,
                                  msg_id=prev_id)


async def downgrade_expired_subscriptions(context: CallbackContext) -> None:
    now = datetime.utcnow()
    expired_users = await get_expired_subscriptions()

    for user_id, expiry_iso, tier in expired_users:
        expiry_dt = datetime.fromisoformat(expiry_iso)
        seconds_since_expiry = (now - expiry_dt).total_seconds()
        seconds_left = GRACE_PERIOD - seconds_since_expiry

        if tier != TierConvertFromNumber.FREE:
            await downgrade_user(user_id, expiry_iso)
            logging.info(f"🔻 Downgraded user {user_id} (expired on {expiry_iso}).")
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "⚠️ Your paid subscription has expired.\n"
                    "You have *24 hours* since your expiration date to renew. "
                    "After that, extra personal plans will be removed."
                ),
                parse_mode="Markdown",
            )

        if seconds_left <= 0:
            seconds_left = 0
        job_name = f"grace_prune_{user_id}"
        existing = context.job_queue.get_jobs_by_name(job_name)
        if not existing:
            context.job_queue.run_once(
                prune_after_grace,
                when=seconds_left,
                data=user_id,
                name=job_name
            )


async def prune_after_grace(context: CallbackContext) -> None:
    user_id: int = context.job.data
    current_tier = TierConvertFromNumber(await get_user_tier(user_id))
    tier_config = TIERS[current_tier]

    # Enforce plan count and interval based on CURRENT tier limits
    await prune_personal_plans_for_tier(
        user_id=user_id,
        max_plans=tier_config.mx_personal_plans,
        min_interval=tier_config.mn_interval,
    )

    await context.bot.send_message(
        chat_id=user_id,
        text=f"ℹ️ Grace period ended.\n"
             f"If you did not renew your subscription or proceeded with lower tier, "
             f"some personal plans could be disabled to match your current tier limits."
    )

    # 3) Finally clear subscription_end so this row is never seen again
    if current_tier == TierConvertFromNumber.FREE:
        await update_user_tier(user_id, current_tier, expiry_date=None)
    logging.info(f"✅ Pruned and cleared expiry for user {user_id}.")


async def prune_personal_plans_for_tier(user_id: int, max_plans: int, min_interval: int) -> None:

    # Fetch all personal plans for the user
    plans = await get_personal_plans(user_id)
    valid_plans = []

    # Step 1: Filter by min_interval
    for plan_id, interval, _ in plans:
        if interval < min_interval:
            await delete_personal_plan(plan_id)
        else:
            valid_plans.append((plan_id, interval))

    # Step 2: Enforce max plan count
    if len(valid_plans) > max_plans:
        # Keep earliest plans, remove the rest
        to_remove = valid_plans[max_plans:]
        for plan_id, _ in to_remove:
            await delete_personal_plan(plan_id)
