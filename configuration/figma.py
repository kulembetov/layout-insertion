# pyright: strict
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class FigmaKey(StrEnum):
    ABSOLUTE_BOUNDING_BOX = "absoluteBoundingBox"
    CHILDREN = "children"
    NAME = "name"
    TYPE = "type"
    STYLE = "style"
    BORDER_RADIUS = "cornerRadius"
    RECT_CORNER_RADII = "rectangleCornerRadii"
    VISIBLE = "visible"
    CHARACTERS = "characters"
    SLIDE_COLORS = "slideColors"
    FONT_FAMILY = "fontFamily"


class FigmaNodeType(StrEnum):
    TEXT = "TEXT"
    RECTANGLE = "RECTANGLE"
    FRAME = "FRAME"
    GROUP = "GROUP"


class BlockType(StrEnum):
    FIGURE = "figure"
    IMAGE = "image"
    BACKGROUND = "background"


@dataclass(frozen=True, slots=True)
class FigmaExtractConfig:
    TARGET_WIDTH: int
    TARGET_HEIGHT: int
    OUTPUT_DIR: str
    OUTPUT_FILE: str


FIGMA_CONFIG: Final[FigmaExtractConfig] = FigmaExtractConfig(
    TARGET_WIDTH=1200,
    TARGET_HEIGHT=675,
    OUTPUT_DIR="figma_extract",
    OUTPUT_FILE="extracted_data",
)

# Valid font weights - ONLY these are allowed
VALID_FONT_WEIGHTS: Final[tuple[int, ...]] = (300, 400, 700)
