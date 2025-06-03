from time import time

from telegram import Update, LabeledPrice
from telegram.ext import CallbackContext

from db.db import get_user_tier, remove_invoice_from_db, record_invoice, get_expired_invoice_messages
from keyboard import build_upgrade_keyboard, build_payment_keyboard
from util import send_or_edit, safe_delete_message
from config import TIERS, TierConvertFromNumber, UKASSA_TEST_TOKEN, SMART_GLOCAL_TEST_TOKEN

EXPIRY_SECONDS = 300


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

    for tier_key in (TierConvertFromNumber.PRO, TierConvertFromNumber.ULTRA):
        tier = TIERS[tier_key]
        if tier_key == TierConvertFromNumber(tier_name):
            continue  # Skip showing current tier as an upgrade option

        message_lines.append(
            f"{tier.emoji} *{tier.name} Tier* – {tier.price['USD'].currency}{tier.price['USD'].amount} / month\n"
            f"  • {tier.mx_personal_plans} personal plans\n"
            f"  • Min interval: {tier.mn_interval} min\n"
        )
    message_lines.append("⏳ Subscriptions are *manual* and expire after 30 days.\nYou can renew at any time.")

    message = "\n".join(message_lines)
    reply_markup = build_upgrade_keyboard()

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


async def upgrade_to_pro(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    current_tier = await get_user_tier(user_id)

    if current_tier == TierConvertFromNumber.PRO:
        await send_or_edit(update, "✅ You are already on *Pro* tier.", parse_mode="Markdown")
        await open_upgrade_menu(update, context)
        return

    # Proceed to send payment invoice (next step)
    reply_markup = build_payment_keyboard(tier_type="pro")
    await send_or_edit(
        update,
        "💳 Choose a payment method for *Pro* tier:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def upgrade_to_ultra(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    current_tier = await get_user_tier(user_id)

    if current_tier == TierConvertFromNumber.ULTRA:
        await send_or_edit(update, "✅ You are already on *Ultra* tier.", parse_mode="Markdown")
        await open_upgrade_menu(update, context)
        return

    # Proceed to send payment invoice (next step)
    reply_markup = build_payment_keyboard(tier_type="ultra")
    await send_or_edit(
        update,
        "💳 Choose a payment method for *Ultra* tier:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


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
