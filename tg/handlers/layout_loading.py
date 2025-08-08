from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.states import LayoutLoadingState, OptionState
from tg.utils import to_str_user

layout_loading_router = Router()

logger = setup_logger(__name__)


@layout_loading_router.message(LayoutLoadingState.loading)
async def layout_loading(message: Message, state: FSMContext) -> None:
    from tg.markups import start_markup

    figma_url_raw = message.text
    str_user = to_str_user(message.from_user)
    logger.info(f'Пользователь {str_user} якобы загрузил шаблон "{figma_url_raw}".')

    await message.answer("Выберите опцию:", reply_markup=start_markup.get())
    await state.set_state(OptionState.choosing)
