"""This file is intended to collect the entire tg project and run it"""

import asyncio

from loader import bot, dp

from log_utils import setup_logger
from tg.handlers.commands.start import start_router
from tg.handlers.layout_loading import layout_loading_router
from tg.handlers.option_choosing import option_router
from tg.handlers.sql_delete import delete_router
from tg.handlers.sql_insert import insert_router
from tg.handlers.sql_update import update_router

logger = setup_logger(__name__)


async def run_main():
    dp.include_router(start_router)
    dp.include_router(option_router)
    dp.include_router(layout_loading_router)

    dp.include_router(insert_router)
    dp.include_router(update_router)
    dp.include_router(delete_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting a bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_main())
