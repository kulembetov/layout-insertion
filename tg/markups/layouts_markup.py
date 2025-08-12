from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get(layout_names: list[str] | None):
    """Creating an inline keyboard with layout names."""
    builder = InlineKeyboardBuilder()

    buttons = [InlineKeyboardButton(text=name, callback_data=name) for name in layout_names] if layout_names else []

    builder.row(*buttons)
    builder.adjust(1)

    return builder.as_markup()
