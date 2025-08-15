from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from db_work.implemented import presentation_layout_manager
from log_utils import setup_logger
from tg.states import DeletingProcessState
from tg.utils import r_text, to_str_user

delete_router = Router()

logger = setup_logger(__name__)


@delete_router.callback_query(F.data, DeletingProcessState.choosing)
async def delete_logic(query: CallbackQuery, state: FSMContext):
    cb_data = query.data
    layout = presentation_layout_manager.select_layout_by_uid(cb_data)
    if layout is not None:
        layout_name: str = layout.name
        await query.message.edit_text(f"Выбран шаблон: *{r_text(layout_name)}*", reply_markup=None)

        str_user = to_str_user(query.from_user)
        logger.info(f"Пользователь {str_user} выбрал шаблон <{(cb_data, layout_name)}> для удаления.")

        await query.message.answer("Опция удаления находится в разработке\\.")
        await state.clear()

        await query.answer()
    else:
        raise Exception(f"Unexpected callback query or layout: {cb_data, layout}")
