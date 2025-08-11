from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.states import FigmaLayoutState, StartingProcessState
from tg.utils import extract_file_id, is_valid_figma_url, to_str_user

figma_layout_router = Router()

logger = setup_logger(__name__)


@figma_layout_router.message(F.text, FigmaLayoutState.loading)
async def layout_loading(message: Message, state: FSMContext) -> None:
    from tg.markups import start_process_markup

    figma_url = message.text

    if is_valid_figma_url(figma_url):
        file_id = extract_file_id(figma_url)

        if file_id:
            logger.info(f"Extracted file id: {file_id}")

            # call request to django app

            str_user = to_str_user(message.from_user)
            logger.info(f"Пользователь {str_user} якобы загрузил шаблон '{figma_url}'.")

            await message.answer("Шаблон успешно загружен. Нажмите 'Начать' для добавления шаблона.", reply_markup=start_process_markup.get())
            await state.set_state(StartingProcessState.inserting)

        else:
            logger.error(f"file_id={file_id}, raw_url={figma_url}")
            await message.answer("Некорректный 'file_id'. Попробуйте загрузить ссылку еще раз.")
            await state.set_state(FigmaLayoutState.loading)
    else:
        await message.answer("Неверная ссылка. Попробуйте загрузить ссылку еще раз.")
        await state.set_state(FigmaLayoutState.loading)
