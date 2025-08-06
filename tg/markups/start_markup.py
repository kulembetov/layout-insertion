from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get():
    """Creating an inline keyboard of the base menu."""
    builder = InlineKeyboardBuilder()

    insert_btn = InlineKeyboardButton(text="Добавить шаблон", callback_data="insert")
    update_btn = InlineKeyboardButton(text="Обновить шаблон", callback_data="update")
    delete_btn = InlineKeyboardButton(text="Удалить шаблон", callback_data="delete")

    builder.row(
        insert_btn,
        update_btn,
        delete_btn,
    )
    builder.adjust(1)

    return builder.as_markup()
