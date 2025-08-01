"""Send menu with options after typing /start command."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from log_utils import setup_logger
from tg.utils import has_access, to_str_user

start_router = Router()

logger = setup_logger(__name__)


@start_router.message(CommandStart())
async def start(message: Message) -> None:
    from tg.markups import start_markup

    str_user = to_str_user(message.from_user)
    if has_access(message.from_user.id):
        logger.info(f'Пользователь {str_user} нажал /start.')
        await message.answer("Выберите опцию", reply_markup=start_markup.get())

    else:
        logger.warning(f'Пользователь {str_user} пытался воспользоваться ботом.')
        await message.answer("У Вас нет доступа пользоваться данным ботом.")
