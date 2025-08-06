from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.states import DeletingState, OptionState

delete_router = Router()

logger = setup_logger(__name__)


@delete_router.message(F.text, DeletingState.name)
async def delete_logic(message: Message, state: FSMContext):
    await message.answer('В настоящий момент кнопка "Удалить шаблон" не работает.')
    await state.set_state(OptionState.choosing)
