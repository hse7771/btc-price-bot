import asyncio
import logging
from datetime import datetime

from telegram.ext import (Application, AIORateLimiter, CommandHandler, CallbackQueryHandler, ConversationHandler,
                          MessageHandler, filters)

from config import TOKEN, FETCH_INTERVAL, GET_INTERVAL, GET_START_TIME
from db.db import init_db
from util import close_http_session
from handlers.price import get_price_command_click, refresh_price_cache
from handlers.currency import set_currency_command_click
from handlers.base_plan import subscribe_base_command_click, unsubscribe_base_command_click
from handlers.personal_plan import (view_personal_plans_command_click, add_personal_start, add_personal_interval,
                                    add_personal_start_time, cancel_add_process_personal_p, open_cancel_personal_menu,
                                    cancel_personal_plan, open_time_settings_menu_wrapper)
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

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CommandHandler("price", get_price_command_click))
    app.add_handler(CommandHandler("set_currency", set_currency_command_click))

    app.add_handler(CommandHandler("subscribe_base", subscribe_base_command_click))
    app.add_handler(CommandHandler("unsubscribe_base", unsubscribe_base_command_click))

    app.add_handler(CommandHandler("view_personal", view_personal_plans_command_click))
    app.add_handler(CommandHandler("cancel_personal", open_cancel_personal_menu))

    add_personal_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_personal_start, pattern="^add_personal$"),
                      CommandHandler("add_personal", add_personal_start)],
        states={
            GET_INTERVAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_personal_interval),
                CallbackQueryHandler(cancel_add_process_personal_p, pattern= "^cancel_add_process_personal_p$"),
                CallbackQueryHandler(open_time_settings_menu_wrapper, pattern= "^open_time_settings_menu_wrapper$"),
            ],
            GET_START_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_personal_start_time),
                CallbackQueryHandler(cancel_add_process_personal_p, pattern= "^cancel_add_process_personal_p$"),
            ],
        },
        fallbacks=[],
    )
    app.add_handler(add_personal_conv)
    app.add_handler(CallbackQueryHandler(cancel_personal_plan, pattern=r"^cancel_personal_plan_\d+$"))

    app.add_handler(CallbackQueryHandler(button_click_handler))

    # Start polling for messages
    print("🚀 Bot is running... Press Ctrl+C to stop.")
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

