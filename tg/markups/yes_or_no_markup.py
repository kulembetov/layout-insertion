from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get():
    """Creating an inline keyboard with yes/no options."""
    builder = InlineKeyboardBuilder()

    yes_btn = InlineKeyboardButton(text="Да", callback_data="yes")
    no_btn = InlineKeyboardButton(text="Нет", callback_data="no")

    builder.row(
        yes_btn,
        no_btn,
    )
    builder.adjust(1)

    return builder.as_markup()
