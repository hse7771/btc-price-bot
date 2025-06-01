from telegram import Update
from telegram.ext import CallbackContext
from db.db import get_user_tier
from keyboard import build_upgrade_keyboard, build_payment_keyboard
from util import send_or_edit
from config import TIERS, TierConvertFromNumber, UKASSA_TEST_TOKEN, SMART_GLOCAL_TEST_TOKEN


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
