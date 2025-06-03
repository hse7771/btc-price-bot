from datetime import datetime, timedelta
from time import time
from urllib.parse import parse_qs

from telegram import Update, LabeledPrice
from telegram.ext import CallbackContext, ContextTypes

from db.db import get_user_tier, remove_invoice_from_db, record_invoice, get_expired_invoice_messages, record_payment, \
    update_user_tier
from handlers.personal_plan import open_personal_sub_menu
from keyboard import build_upgrade_keyboard, build_payment_keyboard
from util import send_or_edit, safe_delete_message
from config import TIERS, TierConvertFromNumber, UKASSA_TEST_TOKEN, SMART_GLOCAL_TEST_TOKEN, TIER_NAMES, PROVIDERS

EXPIRY_SECONDS = 300
SUB_DURATION_DAYS = 30

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
    reply_markup = build_payment_keyboard(tier_type="pro")
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
    reply_markup = build_payment_keyboard(tier_type="ultra")
    msg = await send_or_edit(
        update,
        "💳 Choose a payment method for *Ultra* tier:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.chat_data["previous_upgrade_menu_msg_id"] = msg.message_id


async def send_invoice(update: Update, context: CallbackContext, tier_type: TierConvertFromNumber, provider: str,
                       currency: str) -> None:
    user_id = update.effective_user.id
    tier = TIERS[tier_type]
    payload = f"tier={tier.name.lower()}&provider={provider}&user={user_id}&timestamp={int(time())}"
    start_parameter = f"{tier.name.lower()}{user_id}"

    provider_token = {
        "yoomoney": UKASSA_TEST_TOKEN,
        "smart_glocal": SMART_GLOCAL_TEST_TOKEN
    }.get(provider)

    msg = await context.bot.send_invoice(
        chat_id=user_id,
        title=f"{tier.name} Tier Subscription",
        description=(
            f"{tier.name} features will be unlocked for 30 days.\n"
            f"Invoice is valid for {EXPIRY_SECONDS // 60} minutes and will automatically expire after that."
        ),
        payload=payload,
        provider_token=provider_token,
        currency=currency,
        prices=[LabeledPrice(f"{tier.name} Tier – Monthly", int(100 * tier.price[currency].amount))],
        start_parameter=start_parameter,
        need_name=True,
    )
    context.chat_data["invoice_msg_id"] = msg.message_id

    await record_invoice(message_id=msg.message_id, chat_id=msg.chat.id, created_at=int(time()))
    context.job_queue.run_once(delete_invoice_msg_record, when=EXPIRY_SECONDS,
                               data=(update.effective_chat.id, msg.message_id), name=f"del_{msg.message_id}")


async def delete_invoice_msg_record(context: CallbackContext) -> None:
    chat_id, msg_id = context.job.data
    await safe_delete_message(context.bot, chat_id, msg_id)
    await remove_invoice_from_db(msg_id)


async def cleanup_expired_invoices(context: CallbackContext) -> None:
    expired = await get_expired_invoice_messages(int(time()) - EXPIRY_SECONDS)
    for message_id, chat_id in expired:
        await safe_delete_message(context.bot, chat_id, message_id)
        await remove_invoice_from_db(message_id)


async def handle_precheckout_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query

    parsed = parse_payload(query.invoice_payload)
    if not parsed:
        await query.answer(ok=False, error_message="❌ Invalid payment payload.")
        return

    tier = parsed["tier"]
    provider = parsed["provider"]
    if tier not in TIER_NAMES or provider not in PROVIDERS.keys():
        await query.answer(ok=False, error_message="Invalid plan or payment provider.")
        return
    user_id = parsed["user_id"]
    ts = parsed["ts"]

    # Expired invoice
    if time() - ts > EXPIRY_SECONDS:
        await query.answer(ok=False, error_message="This payment link has expired.")
        return

    # Attempted misuse from another user
    if user_id != query.from_user.id:
        await query.answer(ok=False, error_message="This invoice was not issued for you.")
        return

    # ✅ All checks passed
    await query.answer(ok=True)


def parse_payload(payload: str) -> dict[str, str | int] | None:
    try:
        parts = parse_qs(payload)
        return {
            "tier": parts["tier"][0],
            "provider": parts["provider"][0],
            "user_id": int(parts["user"][0]),
            "ts": int(parts["timestamp"][0]),
        }
    except (KeyError, ValueError, IndexError):
        return None


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    parsed = parse_payload(payment.invoice_payload)

    if not parsed:
        await send_or_edit(update,
                           "⚠️ Payment was processed, but the data was invalid. Please contact support.")
        return

    tier_name = parsed["tier"]
    provider = parsed["provider"]
    user_id = parsed["user_id"]
    msg_id = context.chat_data.get("invoice_msg_id")  # Optional, fallback if needed

    # 1. Cancel the scheduled auto-delete job
    if msg_id:
        for job in context.job_queue.get_jobs_by_name(f"del_{msg_id}"):
            job.schedule_removal()
        await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id, msg_id=msg_id)
        await remove_invoice_from_db(msg_id)

    new_tier = TierConvertFromNumber[tier_name.upper()]
    # 2. Log the payment
    await record_payment(
        user_id=user_id,
        tier=new_tier,
        currency=payment.currency,
        amount=payment.total_amount,
        provider=provider,
        telegram_charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id,
    )

    # 3. Upgrade the user tier
    expiry_dt = datetime.utcnow() + timedelta(days=SUB_DURATION_DAYS)
    expiry_iso = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
    await update_user_tier(user_id, new_tier, expiry_iso)

    # 4. Confirm to user
    msg = await send_or_edit(update,
                       "✅ Payment successful! Your subscription has been activated.")
    await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id, msg_id=msg.message_id, delay=5)
    await open_personal_sub_menu(update, context)
    await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id,
                              msg_id=context.chat_data["previous_upgrade_menu_msg_id"])
