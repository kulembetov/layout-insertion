"""Send menu with options after typing /start command."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.states import OptionState
from tg.utils import has_access, to_str_user

start_router = Router()

logger = setup_logger(__name__)


@start_router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()

    str_user = to_str_user(message.from_user)
    if has_access(message.from_user.id):
        from tg.markups import option_markup

        logger.info(f"Пользователь {str_user} нажал '/start'.")

        await message.answer("Выберите опцию:", reply_markup=option_markup.get())
        await state.set_state(OptionState.choosing)

    else:
        logger.warning(f"Пользователь {str_user} пытался воспользоваться ботом.")
        await message.answer("У Вас нет доступа пользоваться данным ботом.")
