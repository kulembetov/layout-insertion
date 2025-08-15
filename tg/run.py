"""This file is intended to collect the entire tg project and run it"""

import asyncio

from loader import bot, dp

from log_utils import setup_logger
from tg.handlers.commands.start import start_router
from tg.handlers.figma_layout import figma_layout_router
from tg.handlers.miniature_options import miniature_router
from tg.handlers.option_choosing import option_router
from tg.handlers.sql_delete import delete_router
from tg.handlers.sql_load import load_router

logger = setup_logger(__name__)


async def run_main():
    routers = (start_router, option_router, figma_layout_router, miniature_router, load_router, delete_router)
    dp.include_routers(*routers)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting a bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_main())
