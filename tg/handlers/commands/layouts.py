"""Send menu with all layouts after typing /layouts command."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db_work.implemented import presentation_layout_manager
from log_utils import setup_logger
from tg.utils import has_access, to_str_user

layouts_router = Router()

logger = setup_logger(__name__)


@layouts_router.message(Command("layouts"))
async def get_layout_list(message: Message) -> None:

    str_user = to_str_user(message.from_user)
    if has_access(message.from_user.id):
        from tg.markups import layouts_markup

        logger.info(f"Пользователь {str_user} нажал /layouts.")

        await message.answer("Список всех шаблонов:", reply_markup=layouts_markup.get(presentation_layout_manager.get_presentation_layout_ids_names()))

    else:
        logger.warning(f"Пользователь {str_user} пытался воспользоваться ботом.")
        await message.answer("У Вас нет доступа пользоваться данным ботом\\.")
