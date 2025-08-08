from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.states import LayoutLoadingState, OptionState
from tg.utils import extract_file_id, is_valid_figma_url, to_str_user

layout_loading_router = Router()

logger = setup_logger(__name__)


@layout_loading_router.message(LayoutLoadingState.loading)
async def layout_loading(message: Message, state: FSMContext) -> None:
    from tg.markups import start_markup

    figma_url_raw = message.text
    if is_valid_figma_url(figma_url_raw):
        file_id = extract_file_id(figma_url_raw)
        if file_id:
            logger.info(f"Extracted file id: {file_id}")

            # call request to django app

            str_user = to_str_user(message.from_user)
            logger.info(f"Пользователь {str_user} якобы загрузил шаблон '{figma_url_raw}'.")

            await message.answer("Выберите опцию:", reply_markup=start_markup.get())
            await state.set_state(OptionState.choosing)

        else:
            logger.error(f"file_id={file_id}, raw_url={figma_url_raw}")
            await message.answer("Некорректный 'file_id'. Попробуйте загрузить ссылку еще раз.")
            await state.set_state(LayoutLoadingState.loading)
    else:
        await message.answer("Неверная ссылка. Попробуйте загрузить ссылку еще раз.")
        await state.set_state(LayoutLoadingState.loading)
