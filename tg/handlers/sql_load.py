from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db_work.executor import Executor
from db_work.implemented import presentation_layout_manager, slide_layout_manager
from log_utils import setup_logger
from tg.states import LoadingProcessState, MiniatureState, OptionState, StartingProcessState
from tg.utils import r_text, to_str_user

load_router = Router()

logger = setup_logger(__name__)


@load_router.message(F.text, LoadingProcessState.typing_name)
async def define_layout_name(message: Message, state: FSMContext):
    from tg.markups import yes_or_no_markup

    layout_name = message.text
    layout = presentation_layout_manager.select_layout_by_name(layout_name)
    if layout is not None:
        await state.update_data(layout_name=layout_name, layout_id=str(layout.id))

        await message.answer(f"Нашелся шаблон *{r_text(layout_name)}* в базе данных\\. Хотите обновить шаблон?", reply_markup=yes_or_no_markup.get())
        await state.set_state(LoadingProcessState.updating)

    else:
        await state.update_data(layout_name=layout_name)

        await message.answer(
            f"Шаблон *{r_text(layout_name)}* не был найден в базе данных\\. Хотите добавить шаблон?",
            reply_markup=yes_or_no_markup.get(),
        )
        await state.set_state(LoadingProcessState.inserting)


@load_router.callback_query(F.data, LoadingProcessState.inserting)
async def insert_choice(query: CallbackQuery, state: FSMContext):
    from tg.markups import miniature_markup

    cb_data = query.data
    str_user = to_str_user(query.from_user)

    match cb_data:
        case "yes":
            logger.info(f"Пользователь {str_user} хочет добавить шаблон.")
            await query.message.edit_text("Добавление одобрено\\.", reply_markup=None)

            await state.update_data(query_from="insert")
            await query.message.answer("Выберите путь для миниатюр:", reply_markup=miniature_markup.get_paths())
            await state.set_state(MiniatureState.choosing_path)

            await query.answer()

        case "no":
            from tg.markups import option_markup

            logger.info(f"Пользователь {str_user} отказался от добавления.")
            await query.message.edit_text("Добавление отклонено\\.", reply_markup=None)

            await query.message.answer("Выберите опцию:", reply_markup=option_markup.get())
            await state.set_state(OptionState.choosing)

            await query.answer()

        case _:
            await query.answer()
            raise ValueError(f"Unexpected callback query: {cb_data}")


@load_router.callback_query(F.data, LoadingProcessState.updating)
async def update_choice(query: CallbackQuery, state: FSMContext):
    from tg.markups import miniature_markup

    cb_data = query.data
    str_user = to_str_user(query.from_user)

    match cb_data:
        case "yes":
            logger.info(f"Пользователь {str_user} хочет обновить шаблон.")
            await query.message.edit_text("Обновление одобрено\\.", reply_markup=None)

            await state.update_data(query_from="update")
            await query.message.answer("Выберите путь для миниатюр:", reply_markup=miniature_markup.get_paths())
            await state.set_state(MiniatureState.choosing_path)

            await query.answer()

        case "no":
            from tg.markups import option_markup

            logger.info(f"Пользователь {str_user} отказался от обновления.")
            await query.message.edit_text("Обновление отклонено\\.", reply_markup=None)

            await query.message.answer("Выберите опцию:", reply_markup=option_markup.get())
            await state.set_state(OptionState.choosing)

            await query.answer()

        case _:
            await query.answer()
            raise ValueError(f"Unexpected callback query: {cb_data}")


@load_router.callback_query(F.data, StartingProcessState.inserting)
async def insert_logic(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(r_text("Шаблон загружен. Идет процесс добавления..."), reply_markup=None)

    str_user = to_str_user(query.from_user)
    logger.info(f"Пользователь {str_user} начал процесс добавления.")

    data = await state.get_data()
    miniature_path = data.get("miniature_path")
    miniature_extension = data.get("miniature_extension")
    layout_name = data.get("layout_name")

    executor = Executor(
        path=miniature_path,
        extension=miniature_extension,
        layout_name=layout_name,
    )
    executor.insert(layout_name, user_role="USER")

    await query.message.answer(f"Шаблон *{r_text(layout_name)}* успешно добавлен\\.")

    await state.clear()
    await query.answer()


@load_router.callback_query(F.data, StartingProcessState.updating)
async def update_logic(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(r_text("Идет процесс обновления..."), reply_markup=None)

    str_user = to_str_user(query.from_user)
    logger.info(f"Пользователь {str_user} начал процесс обновления.")

    layout_name, layout_id = await state.get_value("layout_name"), await state.get_value("layout_id")

    res = slide_layout_manager.insert_or_update(layout_id)

    await query.message.answer(f"Шаблон *{r_text(layout_name)}* успешно обновлен\\.")
    await query.message.answer(f"Результаты обновления: {r_text(str(res))}")

    await state.clear()
    await query.answer()
