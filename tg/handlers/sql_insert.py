from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from log_utils import setup_logger
from tg.utils import generate_uuid
from tg.states import InsertingState

insert_router = Router()

logger = setup_logger(__name__)

@insert_router.message(F.text, InsertingState.name)
async def insert_logic(message: Message, state: FSMContext):
    # wait for check func
    if message.text and (already_exists := False):
        # check if layout with this name already exists or not
        # start 'update_logic' if it's True
        # W.I.P
        ...

    uid = generate_uuid()
    await state.update_data(name=message.text, uid=uid)

    logger.info(f'name={message.text}, uid={uid}')
    # do request to db and create new row with name and id
