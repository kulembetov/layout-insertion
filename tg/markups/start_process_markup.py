from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get():
    """Creating an inline keyboard with start button."""
    builder = InlineKeyboardBuilder()

    start_btn = InlineKeyboardButton(text="Начать", callback_data="start")

    builder.row(
        start_btn,
    )
    builder.adjust(1)

    return builder.as_markup()
