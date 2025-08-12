from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from log_utils import setup_logger
from tg.states import DeletingProcessState
from tg.utils import r_text, to_str_user

delete_router = Router()

logger = setup_logger(__name__)


@delete_router.callback_query(F.data, DeletingProcessState.choosing)
async def delete_logic(query: CallbackQuery, state: FSMContext):
    cb_data = query.data
    await query.message.edit_text(f"Выбран шаблон: *{r_text(cb_data)}*", reply_markup=None)

    str_user = to_str_user(query.from_user)
    logger.info(f"Пользователь {str_user} выбрал шаблон <{cb_data}> для удаления.")

    await query.message.answer("Опция удаления находится в разработке\\.")
    await state.clear()

    await query.answer()
