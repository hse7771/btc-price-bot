from time import time

from telegram import LabeledPrice, Update
from telegram.ext import CallbackContext, ContextTypes

from config import TIERS, TierConvertFromNumber
from handlers.core import open_main_menu
from keyboard import build_donate_keyboard
from util import safe_delete_message, send_or_edit

BASE_PRICES = {
    "RUB": 100,
    "USD": 1,
}
DONATE_AMOUNTS = [5_000, 10_000, 20_000, 50_000]


async def open_donate_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = build_donate_keyboard()
    msg = await send_or_edit(
        update,
        "🙏 *Support the bot*\n\n" "Please select the service you want to use for the donation.",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    context.chat_data["previous_upgrade_menu_msg_id"] = msg.message_id


async def send_invoice_donate(update: Update, context: CallbackContext, tier_type: TierConvertFromNumber,
                              provider: str, currency: str, provider_token: str) -> int:

    user_id = update.effective_user.id
    tier = TIERS[tier_type]

    operation_type = "donation"
    payload = (f"operation_type={operation_type}&tier={tier.name.lower()}&provider={provider}"
               f"&user={user_id}&timestamp={int(time())}")

    msg = await context.bot.send_invoice(
        chat_id=user_id,
        title="Donation ❤️",
        description="Thank you for supporting development!",
        payload=payload,
        provider_token=provider_token,
        currency=currency,
        prices=[LabeledPrice("Donation", 100 * BASE_PRICES[currency])],
        start_parameter=f"donate{user_id}",
        need_name=False,
        max_tip_amount=100_000,
        suggested_tip_amounts=DONATE_AMOUNTS,
    )
    return msg.message_id


async def handle_successful_donate_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 4. Confirm to user
    msg = await send_or_edit(update, "✅ Donation successful! Your support is appreciated.")
    prev_id = context.chat_data.get("previous_upgrade_menu_msg_id")
    await safe_delete_message(bot=context.bot, chat_id=update.effective_chat.id, msg_id=prev_id)

    await safe_delete_message(
        bot=context.bot, chat_id=update.effective_chat.id, msg_id=msg.message_id, delay=5
    )
    await open_main_menu(update, context)
