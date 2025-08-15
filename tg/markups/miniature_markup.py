from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_paths():
    """Creating an inline keyboard with available paths."""
    builder = InlineKeyboardBuilder()

    dev_btn = InlineKeyboardButton(text="dev", callback_data="dev")
    stage_btn = InlineKeyboardButton(text="stage", callback_data="stage")
    prod_btn = InlineKeyboardButton(text="prod", callback_data="prod")

    builder.row(
        dev_btn,
        stage_btn,
        prod_btn,
    )
    builder.adjust(1)

    return builder.as_markup()


def get_extensions():
    """Creating an inline keyboard with available extensions."""
    builder = InlineKeyboardBuilder()

    png_btn = InlineKeyboardButton(text=".png", callback_data="png")
    svg_btn = InlineKeyboardButton(text=".svg", callback_data="svg")

    builder.row(
        png_btn,
        svg_btn,
    )
    builder.adjust(1)

    return builder.as_markup()
