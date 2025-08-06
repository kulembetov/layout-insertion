from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db_work.services import PresentationLayoutManager
from log_utils import setup_logger
from tg.states import InsertingState
from tg.utils import to_str_user

insert_router = Router()
manager = PresentationLayoutManager()

logger = setup_logger(__name__)


@insert_router.message(F.text, InsertingState.name)
async def insert_logic(message: Message, state: FSMContext):
    name = message.text
    is_exists: bool | None = manager.select_an_entry_from_presentation_layout(name)
    if is_exists:
        await message.answer("Такой шаблон уже существует. Запуск сценария 'update'.")
        await state.clear()

    else:
        manager.insert_an_entry_in_presentation_layout(name)

        str_user = to_str_user(message.from_user)
        logger.info(f"Пользователь {str_user} добавил шаблон с именем {name}.")
