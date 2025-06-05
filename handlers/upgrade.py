from telegram import Update
from telegram.ext import CallbackContext
from db.db import get_user_tier
from keyboard import build_upgrade_keyboard
from util import send_or_edit
from config import TIERS, TierConvertFromNumber



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
            f"{tier.emoji} *{tier.name} Tier* – {tier.price}\n"
            f"  • {tier.mx_personal_plans} personal plans\n"
            f"  • Min interval: {tier.mn_interval} min\n"
        )
    message_lines.append("⏳ Subscriptions are *manual* and expire after 30 days.\nYou can renew at any time.")

    message = "\n".join(message_lines)
    reply_markup = build_upgrade_keyboard()

    await send_or_edit(update, message, parse_mode="Markdown", reply_markup=reply_markup)


