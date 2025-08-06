"""Send menu with options after typing /start command."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from log_utils import setup_logger
from tg.states import InsertingState, OptionState
from tg.utils import has_access, to_str_user

start_router = Router()

logger = setup_logger(__name__)


@start_router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    from tg.markups import start_markup

    str_user = to_str_user(message.from_user)
    if has_access(message.from_user.id):
        logger.info(f"Пользователь {str_user} нажал /start.")

        await message.answer("Выберите опцию", reply_markup=start_markup.get())
        await state.set_state(OptionState.choosing)

    else:
        logger.warning(f"Пользователь {str_user} пытался воспользоваться ботом.")
        await message.answer("У Вас нет доступа пользоваться данным ботом.")


@start_router.callback_query(OptionState.choosing)
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
