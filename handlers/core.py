from telegram import Update
from telegram.ext import CallbackContext

from keyboard import build_main_keyboard
from util import send_or_edit

# Handle /start command
async def start_command(update: Update, context: CallbackContext) -> None:
    """Handles the /start command and sends a welcome message with buttons."""
    welcome_message = (
        "👋 *Welcome to the Bitcoin Price Bot!*\n\n"
        "Here’s what I can help you with:\n"
        "🔹 Show real-time BTC prices\n"
        "🔹 Choose your preferred currencies\n"
        "🔹 Get automatic price updates\n"
        "   • Base Plan (UTC-based)\n"
        "   • Personal Plan (local time)\n\n"
        "👇 Use the buttons below to explore:"
    )

    reply_markup = build_main_keyboard()
    await send_or_edit(update, welcome_message, parse_mode="Markdown", reply_markup=reply_markup)


async def help_command(update: Update, context: CallbackContext) -> None:
    await send_or_edit(update,
                               "<b>ℹ️ Bot Commands:</b>\n\n"
                               
                                    "<b>📌 Essentials:</b>\n"
                                    "/start – Start the bot and show main menu\n"
                                    "/help – Show this help message\n"
                                    "/price – Show the current Bitcoin price\n"
                                    "/currency – Choose currencies you want to see\n\n"
                                
                                    "<b>🕑 Base Plan (UTC-timed):</b>\n"
                                    "/base – Manage your standard BTC updates\n"
                                    "Choose automatic updates every 15min, 30min, 1h, 4h, or daily.\n\n"

                                    "<b>📆 Personal Plans (local-time):</b>\n"
                                    "/personal – Manage your custom BTC alerts\n"
                                    "Set, view, or remove *local-time* subscriptions.\n\n"
                                
                                    "<b>💳 Account & Settings:</b>\n"
                                    "/upgrade – Learn about Pro/Ultra tiers\n"
                                    "/timezone – Set your local time zone\n"
                                    "/language – Change the interface language\n\n"
                                    
                                    "<b>💙 Support the Project:</b>\n"
                                    "/donate – Help keep this bot running\n"
                                    "Support the developer or help cover server costs.\n\n"
                               
                                    "<b>🛟 Need Help?</b>\n"
                                    "Contact support: @YourSupportUsername\n\n",
                                    parse_mode="HTML"
                                )


async def open_main_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = build_main_keyboard()

    await send_or_edit(update,
                       "🏠 <b>Main Menu</b>\n\n"
                       "Choose an action below:\n"
                       "• Check BTC price\n"
                       "• Manage subscriptions\n"
                       "• Customize time and currency settings\n"
                       "• Change language settings\n"
                       "• Support the developer\n",
                       reply_markup=reply_markup,
                       parse_mode="HTML"
                       )
