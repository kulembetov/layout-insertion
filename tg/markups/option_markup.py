from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get():
    """Creating an inline keyboard with available options."""
    builder = InlineKeyboardBuilder()

    load_btn = InlineKeyboardButton(text="Загрузить шаблон", callback_data="load")
    delete_btn = InlineKeyboardButton(text="Удалить шаблон", callback_data="delete")

    builder.row(
        load_btn,
        delete_btn,
    )
    builder.adjust(1)

    return builder.as_markup()
