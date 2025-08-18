"""This file is intended to collect the entire tg project and run it"""

import asyncio

from loader import bot, dp

from log_utils import setup_logger
from tg.handlers import delete_router, figma_layout_router, layouts_router, load_router, miniature_router, option_router, start_router

logger = setup_logger(__name__)


async def run_main():
    dp.include_routers(start_router, layouts_router, option_router, figma_layout_router, miniature_router, load_router, delete_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting a bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_main())
