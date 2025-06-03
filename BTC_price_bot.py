import asyncio
import logging
from datetime import datetime

from telegram.ext import (Application, AIORateLimiter, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
                          PreCheckoutQueryHandler)

from config import TOKEN, FETCH_INTERVAL
from db.db import init_db
from handlers.timezone import timezone_conversation_handler, cancel_timezone_setup, open_time_settings_menu
from handlers.upgrade import open_upgrade_menu, cleanup_expired_invoices, handle_precheckout_query, \
    handle_successful_payment
from util import close_http_session
from handlers.price import get_price_command_click, refresh_price_cache
from handlers.currency import set_currency_command_click
from handlers.base_plan import open_base_sub_menu_command_click
from handlers.personal_plan import (cancel_personal_plan, add_personal_conversation_handler, open_personal_sub_menu)
from handlers.core import start_command, help_command
from button_router import button_click_handler
from scheduler import notify_subscribers


# Set up logging for debugging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Function to start the bot
async def main():
    # init DB
    await init_db()
    # Create application instance with the bot token
    app = (
        Application.builder()
        .token(TOKEN)
        .rate_limiter(AIORateLimiter(
            overall_max_rate=30,
            max_retries=3
        ))
        .build()
    )
    app.job_queue.run_once(cleanup_expired_invoices, when=0)

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", get_price_command_click))
    app.add_handler(CommandHandler("currency", set_currency_command_click))

    app.add_handler(CommandHandler("base", open_base_sub_menu_command_click))
    app.add_handler(CommandHandler("personal", open_personal_sub_menu))

    app.add_handler(CommandHandler("upgrade", open_upgrade_menu))
    app.add_handler(CommandHandler("timezone", open_time_settings_menu))
    # app.add_handler(CommandHandler("language", open_language_change_menu))

    # app.add_handler(CommandHandler("donate", open_donate_menu))

    app.add_handler(add_personal_conversation_handler)
    app.add_handler(CallbackQueryHandler(cancel_personal_plan, pattern=r"^cancel_personal_plan_\d+$"))

    app.add_handler(timezone_conversation_handler)
    app.add_handler(MessageHandler(filters.Regex("^❌ Cancel$"), cancel_timezone_setup))

    app.add_handler(PreCheckoutQueryHandler(handle_precheckout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

    app.add_handler(CallbackQueryHandler(button_click_handler))

    # Start polling for messages
    logging.info("🚀 Bot is running... Press Ctrl+C to stop.")
    async with app:
        await app.start()
        await app.updater.start_polling()

        delay_subs = (60 - datetime.utcnow().second) % 60
        app.job_queue.run_repeating(notify_subscribers, interval=60, first=delay_subs)
        delay_cache = (delay_subs + 30) % 60
        app.job_queue.run_repeating(refresh_price_cache, interval=FETCH_INTERVAL, first=delay_cache)
        try:
            # This keeps the loop alive forever
            await asyncio.Event().wait()
        finally:
            await close_http_session()

if __name__ == "__main__":
    asyncio.run(main())

