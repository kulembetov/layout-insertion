"""Loading bot and dispatcher."""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from settings import BOT_REDIS_URL, BOT_TOKEN

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
loop = asyncio.get_event_loop()
storage = RedisStorage.from_url(BOT_REDIS_URL)
dp = Dispatcher(storage=storage, loop=loop)
