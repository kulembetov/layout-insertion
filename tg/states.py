from aiogram.fsm.state import State, StatesGroup


class OptionState(StatesGroup):
    choosing = State()


class FigmaLayoutState(StatesGroup):
    loading = State()


class MiniatureState(StatesGroup):
    choosing_path = State()
    choosing_extension = State()


class LoadingProcessState(StatesGroup):
    typing_name = State()
    updating = State()
    inserting = State()


class DeletingProcessState(StatesGroup):
    choosing = State()


class StartingProcessState(StatesGroup):
    inserting = State()
    updating = State()
    deleting = State()
