"""This file is intended to collect the entire project and run it"""

import asyncio

from loader import bot, dp
from log_utils import setup_logger


logger = setup_logger(__name__)

async def run_main():
    # include routers there

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info('Starting a bot...')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(run_main())
