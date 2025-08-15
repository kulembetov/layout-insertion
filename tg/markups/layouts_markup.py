from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get(layouts: list[tuple[str, str]] | None):
    """Creating an inline keyboard with layout names."""
    builder = InlineKeyboardBuilder()

    buttons = [InlineKeyboardButton(text=layout[1], callback_data=layout[0]) for layout in layouts] if layouts else []

    builder.row(*buttons)
    builder.adjust(1)

    return builder.as_markup()
