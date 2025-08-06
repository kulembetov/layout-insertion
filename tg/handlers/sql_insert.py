from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db_work.services import ColorSettingsManager, PresentationLayoutManager, PresentationLayoutStylesManager
from log_utils import setup_logger
from tg.states import InsertingState, UpdatingState
from tg.utils import to_str_user

insert_router = Router()

pl_manager = PresentationLayoutManager()
cs_manager = ColorSettingsManager()
pls_manager = PresentationLayoutStylesManager()

logger = setup_logger(__name__)


@insert_router.message(F.text, InsertingState.name)
async def insert_logic(message: Message, state: FSMContext):
    name = message.text
    is_exists: bool | None = pl_manager.find_layout_by_name(name)
    if is_exists:
        await message.answer("Такой шаблон уже существует. Запуск сценария 'update'.")
        await state.set_state(UpdatingState.name)

    else:
        str_user = to_str_user(message.from_user)

        pl_uid = pl_manager.insert_new_layout(name)
        logger.info(f"Пользователь {str_user} добавил шаблон с именем {name} в 'PresentationLayout'.")

        cs_uid = cs_manager.insert_new_color_settings()
        logger.info(f"Пользователь {str_user} добавил новые настройки в 'ColorSettings'.")

        pls_uid = pls_manager.insert_new_ids(pl_uid, cs_uid)
        logger.info(f"Пользователь {str_user} добавил новые ID в 'PresentationLayoutStyles'. " f"presentationLayoutId: {pl_uid}, colorSettingsId: {cs_uid}, presentationLayoutStyleId: {pls_uid}")

        await message.answer(f"Шаблон {name} был успешно добавлен.")
