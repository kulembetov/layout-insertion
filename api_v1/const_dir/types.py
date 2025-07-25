from enum import Enum
from typing import TypedDict

"""
========================
 Figma Node/Block Constants
========================
"""

FIGMA_KEY_ABS_BOX = "absoluteBoundingBox"
FIGMA_KEY_CHILDREN = "children"
FIGMA_KEY_NAME = "name"
FIGMA_KEY_TYPE = "type"
FIGMA_TYPE_TEXT = "TEXT"
FIGMA_TYPE_RECTANGLE = "RECTANGLE"
FIGMA_TYPE_FRAME = "FRAME"
FIGMA_TYPE_GROUP = "GROUP"
FIGMA_KEY_STYLE = "style"
FIGMA_KEY_CORNER_RADIUS = "cornerRadius"
FIGMA_KEY_RECT_CORNER_RADII = "rectangleCornerRadii"
FIGMA_KEY_VISIBLE = "visible"
FIGMA_KEY_CHARACTERS = "characters"
FIGMA_KEY_SLIDE_COLORS = "slideColors"
FIGMA_KEY_FONT_FAMILY = "fontFamily"
BLOCK_TYPE_FIGURE = "figure"
BLOCK_TYPE_IMAGE = "image"
BLOCK_TYPE_BACKGROUND = "background"

"""
========================
 Enums for Types
========================
"""

class SlideLayoutType(str, Enum):
    CLASSIC = "classic"
    MANY_TEXT = "manyText"
    FEW_TEXT = "fewText"
    OPTIMAL_TEXT = "optimalText"
    CHART = "chart"
    TABLE = "table"
    INFOGRAPHICS = "infographics"
    TITLE = "title"
    LAST = "last"
    OTHER = "other"

class BlockType(str, Enum):
    TEXT = "text"
    SLIDE_TITLE = "slideTitle"
    BLOCK_TITLE = "blockTitle"
    EMAIL = "email"
    DATE = "date"
    NAME = "name"
    PERCENTAGE = "percentage"
    IMAGE = "image"
    INFOGRAPHIK = "infographik"
    TABLE = "table"
    FIGURE = "figure"
    ICON = "icon"
    BACKGROUND = "background"
    WATERMARK = "watermark"
    SUBTITLE = "subTitle"
    NUMBER = "number"
    CHART = "chart"

"""
========================
 TypedDicts for Structured Configs
========================
"""
class PrecompiledImagesConfig(TypedDict):
    base_url: str
    default_colors: list[str]
    prefix: list[str]
