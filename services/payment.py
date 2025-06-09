from time import time

from telegram import Update, LabeledPrice
from telegram.ext import CallbackContext, ContextTypes

from config import UKASSA_TEST_TOKEN, SMART_GLOCAL_TEST_TOKEN, EXPIRY_SECONDS, TierConvertFromNumber, TIER_NAMES, \
    PROVIDERS
from db.db import record_invoice, remove_invoice_from_db, get_expired_invoice_messages, record_payment
from handlers.upgrade import handle_successful_upgrade_payment, _handle_successful_upgrade_payment
from util import safe_delete_message, send_or_edit, parse_payload

PROVIDER_TOKENS = {
    "yoomoney":     UKASSA_TEST_TOKEN,
    "smart_glocal": SMART_GLOCAL_TEST_TOKEN,
}

async def send_invoice(update: Update, context: CallbackContext, provider: str, currency: str, title: str, desc: str,
                       payload: str, start_parameter: str, prices: list[LabeledPrice],
                       need_name: bool = True, max_tip: int | None = None, suggested_tips: list[int] | None = None) -> None:
    user_id = update.effective_user.id

    provider_token = PROVIDER_TOKENS.get(provider)
    if provider_token is None:
        raise RuntimeError(f"Invalid provider token for {provider!r}")

    msg = await context.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=desc,
        payload=payload,
        provider_token=provider_token,
        currency=currency,
        prices=prices,
        start_parameter=start_parameter,
        need_name=need_name,
        max_tip_amount=max_tip,
        suggested_tip_amounts=suggested_tips,
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


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    parsed = parse_payload(payment.invoice_payload)

    if not parsed:
        await send_or_edit(update,
                           "⚠️ Payment was processed, but the data was invalid. Please contact support.")
        return
    provider = parsed["provider"]
    user_id = parsed["user_id"]
    new_tier = TierConvertFromNumber[parsed["tier"].upper()]
    operation_type = parsed["operation_type"]

    msg_id = context.chat_data.get("invoice_msg_id")  # Optional, fallback if needed
    # 1. Cancel the scheduled auto-delete job
    if msg_id:
        for job in context.job_queue.get_jobs_by_name(f"del_{msg_id}"):
            job.schedule_removal()
        await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id, msg_id=msg_id)
        await remove_invoice_from_db(msg_id)

    # 2. Log the payment
    await record_payment(
        user_id=user_id,
        operation_type=operation_type,
        tier=new_tier,
        currency=payment.currency,
        amount=payment.total_amount,
        provider=provider,
        telegram_charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id,
    )

    if operation_type == "sub":
        await _handle_successful_upgrade_payment(update, context, user_id, new_tier)
    elif operation_type == "donate":
        await _handle_successful_donate_payment()


