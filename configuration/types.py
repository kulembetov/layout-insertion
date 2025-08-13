# pyright: strict
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TextVertical(StrEnum):
    top = "top"
    center = "center"  # type: ignore[assignment]
    middle = "middle"
    bottom = "bottom"


class TextHorizontal(StrEnum):
    left = "left"
    center = "center"  # type: ignore[assignment]
    middle = "middle"
    right = "right"


class TextTransform(StrEnum):
    none = "none"
    uppercase = "uppercase"
    lowercase = "lowercase"
    capitalize = "capitalize"  # type: ignore[assignment]


class SlideLayoutType(StrEnum):
    classic = "classic"
    manyText = "manyText"
    fewText = "fewText"
    optimalText = "optimalText"
    chart = "chart"
    table = "table"
    infographics = "infographics"
    title = "title"  # type: ignore[assignment]
    last = "last"
    other = "other"
    extraText = "extraText"  # для 4cols


class BlockLayoutType(StrEnum):
    text = "text"
    slideTitle = "slideTitle"
    blockTitle = "blockTitle"
    email = "email"
    date = "date"
    name = "name"
    percentage = "percentage"
    image = "image"
    infographik = "infographik"
    table = "table"
    figure = "figure"
    icon = "icon"
    background = "background"
    watermark = "watermark"
    subTitle = "subTitle"
    number = "number"
    chart = "chart"


@dataclass(frozen=True, slots=True)
class Dimensions:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True, slots=True)
class Style:
    text_vertical: TextVertical
    text_horizontal: TextHorizontal
    font_size: int
    weight: int
    text_transform: TextTransform
    # опционально:
    color: str | None = None
    opacity: float | None = None
    border_radius: int | None = None
    color_settings_id: str | None = None
    z_index: int | None = None
