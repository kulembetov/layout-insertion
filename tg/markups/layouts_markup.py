from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get():
    """Creating an inline keyboard with layout names."""
    builder = InlineKeyboardBuilder()

    btn_1 = InlineKeyboardButton(text="Шаблон №1", callback_data="1")
    btn_2 = InlineKeyboardButton(text="Шаблон №2", callback_data="2")
    btn_3 = InlineKeyboardButton(text="Шаблон №3", callback_data="3")

    builder.row(
        btn_1,
        btn_2,
        btn_3,
    )
    builder.adjust(1)

    return builder.as_markup()
