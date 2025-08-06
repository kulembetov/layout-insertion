from aiogram.fsm.state import State, StatesGroup


class OptionState(StatesGroup):
    choosing = State()


class InsertingState(StatesGroup):
    name = State()


class UpdatingState(StatesGroup):
    name = State()


class DeletingState(StatesGroup):
    name = State()
