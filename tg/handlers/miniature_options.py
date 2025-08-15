from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from log_utils import setup_logger
from tg.states import FigmaLayoutState, MiniatureState, StartingProcessState
from tg.utils import r_text, to_str_user

miniature_router = Router()

logger = setup_logger(__name__)


@miniature_router.callback_query(F.data, MiniatureState.choosing_path)
async def choose_path(query: CallbackQuery, state: FSMContext):
    from tg.markups import miniature_markup

    cb_data = query.data
    str_user = to_str_user(query.from_user)

    if cb_data in ("dev", "stage", "prod"):
        await state.update_data(miniature_path=cb_data)
        await query.message.edit_text(f"Выбран путь *{cb_data}*", reply_markup=None)

        logger.info(f"Пользователь {str_user} выбрал <{cb_data}> в качестве пути для миниатюр.")

        await query.message.answer("Выберите расширение для миниатюр:", reply_markup=miniature_markup.get_extensions())
        await state.set_state(MiniatureState.choosing_extension)

        await query.answer()

    else:
        await query.answer()
        raise ValueError(f"Unexpected callback query: {cb_data}")


@miniature_router.callback_query(F.data, MiniatureState.choosing_extension)
async def choose_extension(query: CallbackQuery, state: FSMContext):
    from tg.markups import start_process_markup

    cb_data = query.data
    str_user = to_str_user(query.from_user)

    if cb_data in ("png", "svg"):
        await state.update_data(miniature_extension=cb_data)
        ext = f".{cb_data}"
        await query.message.edit_text(f"Выбрано расширение *{r_text(ext)}*", reply_markup=None)

        logger.info(f"Пользователь {str_user} выбрал <{ext}> в качестве расширения для миниатюр.")

        query_from = await state.get_value("query_from")
        match query_from:
            case "insert":
                await query.message.answer("Пришлите ссылку на шаблон из Figma\\.")
                await state.set_state(FigmaLayoutState.loading)

                await query.answer()

            case "update":
                await query.message.answer("Нажмите *__Начать__* для обновления шаблона\\.", reply_markup=start_process_markup.get())
                await state.set_state(StartingProcessState.updating)

                await query.answer()

            case _:
                await query.answer()
                raise ValueError(f"Unexpected value from state: {query_from}")

    else:
        await query.answer()
        raise ValueError(f"Unexpected callback query: {cb_data}")
