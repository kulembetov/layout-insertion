from enum import Enum
from typing import TypedDict

"""
========================
 Figma Node/Block Constants
========================
"""

# FK - FIGMA_KEY
# FT - FIGMA_TYPE
# BT - BLOCK_TYPE
FK_ABS_BOX = "absoluteBoundingBox"
FK_CHILDREN = "children"
FK_NAME = "name"
FK_TYPE = "type"
FT_TEXT = "TEXT"
FT_RECTANGLE = "RECTANGLE"
FT_FRAME = "FRAME"
FT_GROUP = "GROUP"
FK_STYLE = "style"
FK_BORDER_RADIUS = "cornerRadius"
FK_RECT_CORNER_RADII = "rectangleCornerRadii"
FK_VISIBLE = "visible"
FK_CHARACTERS = "characters"
FK_SLIDE_COLORS = "slideColors"
FK_FONT_FAMILY = "fontFamily"
BT_FIGURE = "figure"
BT_IMAGE = "image"
BT_BACKGROUND = "background"

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
