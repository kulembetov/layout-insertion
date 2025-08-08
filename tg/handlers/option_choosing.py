from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from log_utils import setup_logger
from tg.states import InsertingState, OptionState
from tg.utils import to_str_user

option_router = Router()

logger = setup_logger(__name__)


@option_router.callback_query(OptionState.choosing)
async def option_callback(query: CallbackQuery, state: FSMContext) -> None:
    cb_data = query.data
    str_user = to_str_user(query.from_user)
    logger.info(f'Пользователь {str_user} выбрал опцию "{cb_data}".')

    match cb_data:
        case "insert":
            await query.message.answer("Введите имя шаблона.\nПример: sber_marketing")
            await state.set_state(InsertingState.name)

        case "update":
            await query.message.answer('В настоящий момент кнопка "Обновить шаблон" не работает.')
            await state.set_state(OptionState.choosing)
            # await state.set_state(UpdatingState.name)

        case "delete":
            await query.message.answer('В настоящий момент кнопка "Удалить шаблон" не работает.')
            await state.set_state(OptionState.choosing)
            # await state.set_state(DeletingState.name)

        case _:
            raise Exception(f"Unexpected callback query: {cb_data}")
