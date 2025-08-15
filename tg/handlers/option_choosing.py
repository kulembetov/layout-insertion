from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from db_work.implemented import presentation_layout_manager
from log_utils import setup_logger
from tg.states import DeletingProcessState, LoadingProcessState, OptionState
from tg.utils import r_text, to_str_user

option_router = Router()

logger = setup_logger(__name__)


@option_router.callback_query(F.data, OptionState.choosing)
async def option_callback(query: CallbackQuery, state: FSMContext) -> None:
    cb_data = query.data
    str_user = to_str_user(query.from_user)
    logger.info(f"Пользователь {str_user} выбрал опцию <{cb_data}>.")

    match cb_data:
        case "load":
            await query.message.edit_text("Выбрана опция: *Загрузить шаблон*", reply_markup=None)

            escaped_sample = r_text("sber_marketing")
            await query.message.answer(f"Введите имя шаблона\\.\n_Пример: {escaped_sample}_")
            await state.set_state(LoadingProcessState.name)

            await query.answer()

        case "delete":
            from tg.markups import layouts_markup

            await query.message.edit_text("Выбрана опция: *Удалить шаблон*", reply_markup=None)

            await query.message.answer("Список всех шаблонов:", reply_markup=layouts_markup.get(presentation_layout_manager.get_presentation_layout_ids_names()))
            await state.set_state(DeletingProcessState.choosing)

            await query.answer()

        case _:
            await query.answer()
            raise ValueError(f"Unexpected callback query: {cb_data}")
