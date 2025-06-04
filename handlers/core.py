from telegram import Update
from telegram.ext import CallbackContext

from keyboard import build_main_keyboard
from util import send_or_edit
from handlers.price import get_price_command_click

# Handle /start command
async def start_command(update: Update, context: CallbackContext) -> None:
    """Handles the /start command and sends a welcome message with buttons."""
    welcome_message = (
        "👋 *Hello! Welcome to the Bitcoin Price Bot.*\n\n"
        "Here’s what I can do for you:\n"
        "🔹 Show real-time BTC prices\n"
        "🔹 Let you choose preferred currencies\n"
        "🔹 Send regular price updates\n\n"
        "👇 Use the buttons below to get started:"
    )

    reply_markup = build_main_keyboard()
    await send_or_edit(update, welcome_message, parse_mode="Markdown", reply_markup=reply_markup)


async def help_command(update: Update, context: CallbackContext) -> None:
    await send_or_edit(update,
                               "<b>ℹ️ Bot Commands:</b>\n\n"
                                    "/start – Start the bot and show main menu\n"
                                    "/help – Show this help message\n"
                                    "/price – Show the current Bitcoin price\n"
                                    "/set_currency – Choose which currencies you want to see\n\n"
                                
                                    "<b>📅 Base Plan Subscriptions:</b>\n"
                                    "/subscribe_base – Subscribe to regular BTC updates (e.g. every 15, 30, 60 min)\n"
                                    "/unsubscribe_base – Cancel your base plan subscriptions\n\n"
                                
                                    "<b>📆 Personal Plans:</b>\n"
                                    "/add_personal – Add a custom BTC subscription\n"
                                    "/view_personal – View your custom subscriptions\n"
                                    "/cancel_personal – Remove a personal subscription\n\n"
                                
                                    "<b>💳 Account & Settings:</b>\n"
                                    "/upgrade – Learn about Pro/Ultra tiers\n"
                                    "/reset – Reset all your preferences\n"
                                    "/change_language – Change the interface language",
                                    parse_mode="HTML"
                                )


async def open_main_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = build_main_keyboard()

    await send_or_edit(update,
                       "🏠 <b>Main Menu</b>\n\n"
                       "Choose an action below:\n"
                       "• Check BTC price\n"
                       "• Manage subscriptions\n"
                       "• Customize time and currency settings",
                       reply_markup=reply_markup,
                       parse_mode="HTML"
                       )
