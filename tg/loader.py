"""Loading bot and dispatcher."""

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from settings import BOT_TOKEN, CACHE_LOCATION

bot = Bot(token=BOT_TOKEN)
loop = asyncio.get_event_loop()
storage = RedisStorage.from_url(CACHE_LOCATION)
dp = Dispatcher(storage=storage, loop=loop)
