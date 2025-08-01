"""Send menu with options after typing /start command."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from log_utils import setup_logger
from tg.utils import has_access, str_user

start_router = Router()

logger = setup_logger(__name__)


@start_router.message(CommandStart())
async def start(message: Message) -> None:
    from tg.markups import start_markup

    user_str = str_user(message.from_user)
    if has_access(message.from_user.id):
        logger.info(f'Пользователь {user_str} нажал /start.')
        await message.answer("Выберите опцию", reply_markup=start_markup.get())

    else:
        logger.warning(f'Пользователь {user_str} пытался воспользоваться ботом.')
        await message.answer("У Вас нет доступа пользоваться данным ботом.")
