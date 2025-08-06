from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.states import OptionState, UpdatingState

update_router = Router()

logger = setup_logger(__name__)


@update_router.message(F.text, UpdatingState.name)
async def update_logic(message: Message, state: FSMContext):
    await message.answer('В настоящий момент кнопка "Обновить шаблон" не работает.')
    await state.set_state(OptionState.choosing)
