from aiogram.fsm.state import State, StatesGroup


class FigmaLayoutState(StatesGroup):
    loading = State()


class OptionState(StatesGroup):
    choosing = State()


class StartingProcessState(StatesGroup):
    inserting = State()
    updating = State()


class LoadingProcessState(StatesGroup):
    name = State()
    updating = State()
    inserting = State()


class DeletingProcessState(StatesGroup):
    choosing = State()
