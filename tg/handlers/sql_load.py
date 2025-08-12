from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db_work.implemented import color_settings_manager, presentation_layout_manager, presentation_layout_styles_manager, slide_layout_manager
from log_utils import setup_logger
from tg.states import FigmaLayoutState, LoadingProcessState, OptionState, StartingProcessState
from tg.utils import r_text, to_str_user

load_router = Router()

logger = setup_logger(__name__)


@load_router.message(F.text, LoadingProcessState.name)
async def define_layout_name(message: Message, state: FSMContext):
    from tg.markups import yes_or_no_markup

    layout = presentation_layout_manager.select_layout_by_name(message.text)
    await state.update_data(layout=layout)
    if layout:
        await message.answer(f"Нашелся шаблон *{r_text(layout.name)}* в базе данных\\. Хотите обновить шаблон?", reply_markup=yes_or_no_markup.get())
        await state.set_state(LoadingProcessState.updating)

    else:
        await message.answer(
            f"Шаблон *{r_text(layout.name)}* не был найден в базе данных\\. Хотите добавить шаблон?",
            reply_markup=yes_or_no_markup.get(),
        )
        await state.set_state(LoadingProcessState.inserting)


@load_router.callback_query(F.data, LoadingProcessState.inserting)
async def insert_choice(query: CallbackQuery, state: FSMContext):
    cb_data = query.data
    str_user = to_str_user(query.from_user)

    match cb_data:
        case "yes":
            logger.info(f"Пользователь {str_user} начал процесс добавления.")
            await query.message.edit_text("Добавление одобрено\\.", reply_markup=None)

            await query.message.answer("Пришлите ссылку на шаблон из Figma\\.")
            await state.set_state(FigmaLayoutState.loading)

            await query.answer()

        case "no":
            from tg.markups import option_markup

            logger.info(f"Пользователь {str_user} прервал процесс добавления.")
            await query.message.edit_text("Добавление отклонено\\.", reply_markup=None)

            await query.message.answer("Выберите опцию:", reply_markup=option_markup.get())
            await state.set_state(OptionState.choosing)

            await query.answer()

        case _:
            await query.answer()
            raise ValueError(f"Unexpected callback query: {cb_data}")


@load_router.callback_query(F.data, LoadingProcessState.updating)
async def update_choice(query: CallbackQuery, state: FSMContext):
    cb_data = query.data
    str_user = to_str_user(query.from_user)

    match cb_data:
        case "yes":
            from tg.markups import start_process_markup

            logger.info(f"Пользователь {str_user} начал процесс обновления.")
            await query.message.edit_text("Обновление одобрено\\.", reply_markup=None)

            await query.message.answer("Нажмите *__Начать__* для обновления шаблона\\.", reply_markup=start_process_markup.get())
            await state.set_state(StartingProcessState.updating)

            await query.answer()

        case "no":
            from tg.markups import option_markup

            logger.info(f"Пользователь {str_user} прервал процесс процесс обновления.")
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

    layout = await state.get_value("layout")
    str_user = to_str_user(query.from_user)

    pl_uid = presentation_layout_manager.insert_new_layout(layout.name)
    logger.info(f"Пользователь {str_user} добавил шаблон с именем <{layout.name}> в PresentationLayout.")

    cs_uid = color_settings_manager.select_color_id()
    logger.info(f"Пользователь {str_user} добавил настройки в ColorSettings.")

    pls_uid = presentation_layout_styles_manager.insert_new_ids(pl_uid, cs_uid)
    logger.info(f"Пользователь {str_user} добавил новые ID в PresentationLayoutStyles. " f"presentationLayoutId: {pl_uid}, colorSettingsId: {cs_uid}, presentationLayoutStyleId: {pls_uid}")

    await query.message.answer(f"Шаблон *{r_text(layout.name)}* успешно добавлен\\.")
    await query.message.answer(f"Шаблон *{r_text(layout.name)}* успешно добавлен\\.")

    await state.clear()
    await query.answer()


@load_router.callback_query(F.data, StartingProcessState.updating)
async def update_logic(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(r_text("Идет процесс обновления..."), reply_markup=None)

    layout_name, layout_id = await state.get_value("layout_name"), await state.get_value("layout_id")

    res = slide_layout_manager.update_slide_layout_data(layout_id)

    await query.message.answer(f"Шаблон *{r_text(layout_name)}* успешно обновлен\\.")
    await query.message.answer(f"Результаты обновления: {res}")

    await state.clear()
    await query.answer()
