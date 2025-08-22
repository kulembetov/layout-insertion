"""
Configuration module for the layout insertion project.

This module contains all configuration constants, enums, and settings
used throughout the application including Figma API settings,
block types, slide layouts, and database configurations.
"""

import os
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

# ========================
#  Environment Variables
# ========================
FIGMA_FILE_ID: str = os.environ.get("FIGMA_FILE_ID", "")
FIGMA_TOKEN: str = os.environ.get("FIGMA_TOKEN", "")

# ========================
#  Figma Node/Block Constants
# ========================
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

# ========================
#  Figma Configuration
# ========================
FIGMA_CONFIG = {
    "TARGET_WIDTH": 1200,
    "TARGET_HEIGHT": 675,
    "OUTPUT_DIR": "figma_extract",
    "OUTPUT_FILE": "extracted_data",
}

# Valid font weights - ONLY these are allowed
VALID_FONT_WEIGHTS = [300, 400, 700]


# ========================
#  TypedDicts for Structured Configs
# ========================


class PrecompiledImagesConfig(TypedDict):
    base_url: str
    default_colors: list[str]
    prefix: list[str]


PRECOMPILED_IMAGES: PrecompiledImagesConfig = {
    "base_url": "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/sbermarketing/images",
    "default_colors": [
        "#030d1d", # темный
        "#eef3ff", # светлый
    ],
    "prefix": ["Dark", 'Light'],
}

# ========================
#  Defaults and Templates
# ========================
MINIATURES_BASE_PATH: str = "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/sbermarketing/miniatures"
DEFAULT_COLOR_SETTINGS_ID: str = "019565bd-99ce-792c-86fd-0188712beb9b"
DEFAULT_COLOR: str = "#ffffff"
MINIATURE_EXTENSION: str = ".png"

DEFAULT_VALUES: dict[str, object] = {
    "slide_layout_name": "grid_cards_horizontal",
    "slide_layout_number": 9,
    "presentation_layout_id": "01919910-cc3c-7404-bfce-a2ca8feb3538",
    "slide_layout_type": "classic",
    "num_blocks": 5,
}

# ========================
#  SQL Templates
# ========================
SQL_TEMPLATES: dict[str, str] = {
    "slide_layout": """-- Create SlideLayout
INSERT INTO "SlideLayout" (
    "id", "name", "number", "isActive", "presentationLayoutId",
    "imagesCount", "maxTokensPerBlock", "maxWordsPerSentence", "minWordsPerSentence", "sentences",
    "isLast", "forGeneration"
) VALUES (
    '{slide_layout_id}',
    '{slide_layout_name}',
    {slide_layout_number},
    true,
    '{presentation_layout_id}',
    {imagesCount},
    300,
    15,
    10,
    1,
    {is_last},
    {for_generation}
)
RETURNING *;""",
    "block_layout": """-- Create BlockLayouts
INSERT INTO "BlockLayout" ("id", "slideLayoutId", "blockLayoutType")
VALUES
{block_layout_values}
RETURNING *;""",
    "block_styles": """-- Create BlockLayoutStyles
INSERT INTO "BlockLayoutStyles" ("blockLayoutId", "textVertical", "textHorizontal", "fontSize", "weight", "zIndex", "color", "opacity", "textTransform", "borderRadius", "colorSettingsId")
VALUES
{styles_values}
RETURNING *;""",
    "block_dimensions": """-- Create BlockLayoutDimensions
INSERT INTO "BlockLayoutDimensions" ("blockLayoutId", "x", "y", "w", "h", "rotation")
VALUES
{dimension_values}
RETURNING *;""",
    "figure": """-- Create Figures
INSERT INTO "Figure" ("id", "blockLayoutId", "name")
VALUES
{figure_values}
RETURNING *;""",
    "precompiled_image": """-- Create PrecompiledImages
INSERT INTO "PrecompiledImage" ("id", "blockLayoutId", "url", "color")
VALUES
{precompiled_image_values}
RETURNING *;""",
    "slide_layout_additional_info": """-- Create SlideLayoutAdditionalInfo
INSERT INTO "SlideLayoutAdditionalInfo" (
    "slideLayoutId", "percentesCount", "maxSymbolsInBlock", "hasHeaders", "type", "iconUrl", "infographicsType"
) VALUES (
    '{slide_layout_id}',
    {percentesCount},
    {maxSymbolsInBlock},
    {hasHeaders},
    '{type}'::"SlideLayoutType",
    '{icon_url}',
    {infographics_type}
)
RETURNING *;""",
    "slide_layout_dimensions": """-- Create SlideLayoutDimensions
INSERT INTO "SlideLayoutDimensions" (
    "slideLayoutId", "x", "y", "w", "h"
) VALUES (
    '{slide_layout_id}',
    {x},
    {y},
    {w},
    {h}
)
RETURNING *;""",
    "slide_layout_styles": """-- Create SlideLayoutStyles
INSERT INTO "SlideLayoutStyles" (
    "slideLayoutId"
) VALUES (
    '{slide_layout_id}'
)
RETURNING *;""",
    "block_layout_index_config": """-- Create BlockLayoutIndexConfig
INSERT INTO "BlockLayoutIndexConfig" (
    "id", "blockLayoutId", "indexColorId", "indexFontId"
)
VALUES
{block_layout_index_config_values}
RETURNING *;""",
    "slide_layout_index_config": """-- Create SlideLayoutIndexConfig
INSERT INTO "SlideLayoutIndexConfig" (
    "id", "presentationPaletteId", "configNumber", "slideLayoutId", "blockLayoutIndexConfigId", "blockLayoutConfigId"
)
VALUES
{slide_layout_index_config_values}
RETURNING *;""",
    "block_layout_limit": """-- Create BlockLayoutLimit\nINSERT INTO "BlockLayoutLimit" ("minWords", "maxWords", "blockLayoutId")\nVALUES\n{block_layout_limit_values}\nRETURNING *;""",
}

# ========================
#  Mappings and Lookups
# ========================
SLIDE_LAYOUT_TYPES: dict[str, str] = {
    "classic": "classic",
    "many_text": "manyText",
    "few_text": "fewText",
    "optimal_text": "optimalText",
    "chart": "chart",
    "table": "table",
    "infographics": "infographics",
    "title": "title",
    "last": "last",
    "other": "other",
}

AUTO_BLOCKS: dict[str, object] = {
    "add_background": True,  # Always add background by default
    "add_watermark": False,  # Default to not adding watermark
    "background": {
        "color": "#ffffff",
        "dimensions": {"x": 0, "y": 0, "w": 1200, "h": 675},
    },
    "watermark": {"dimensions": {"x": 1065, "y": 636, "w": 118, "h": 26}},
    # Special configuration for last slide (slide number -1)
    "last_slide": {"watermark1": {"dimensions": {"x": 785, "y": 40, "w": 380, "h": 114}}},
}

BLOCK_TYPES: dict[str, list[str]] = {
    "null_style_types": [
        "infographik",
        "figure",
        "table",
        "background",
        "image",
        "icon",
    ],
    "z_index_types": [
        "text",
        "slideTitle",
        "blockTitle",
        "email",
        "date",
        "name",
        "percentage",
        "image",
        "infographik",
        "table",
        "figure",
        "background",
        "icon",
        "subTitle",
        "number",
        "chart",
    ],
    # Synced with schema.prisma BlockLayoutType enum
    "block_layout_type_options": [
        "text",
        "slideTitle",
        "blockTitle",
        "email",
        "date",
        "name",
        "percentage",
        "image",
        "infographik",
        "table",
        "figure",
        "icon",
        "background",
        "watermark",
        "subTitle",
        "number",
        "chart",
    ],
}

BLOCK_TYPE_MIN_WORDS: dict[str, int] = {
    "slideTitle": 3,
    "subTitle": 5,
    "blockTitle": 1,
    "text": 8,
    "percentage": 1,
    "number": 1,
    "date": 1,
    "name": 1,
    "email": 1,
}

Z_INDEX_DEFAULTS: dict[str, int] = {
    "background": 0,
    "watermark": 10,
    "figure": 1,
    "image": 2,
    "icon": 2,
    "infographik": 2,
    "table": 2,
    "text": 3,
    "slideTitle": 3,
    "subTitle": 3,
    "blockTitle": 3,
    "number": 3,
    "email": 3,
    "date": 3,
    "name": 3,
    "percentage": 3,
    "default": 1,
}

DEFAULT_DIMENSIONS: dict[str, dict[str, int]] = {
    "background": {"x": 0, "y": 0, "w": 1200, "h": 675},
    "slideTitle": {"x": 37, "y": 37, "w": 1125, "h": 85},
    "subTitle": {"x": 37, "y": 250, "w": 875, "h": 65},
    "blockTitle": {"x": 37, "y": 37, "w": 575, "h": 30},
    "text": {"x": 37, "y": 37, "w": 575, "h": 85},
    "number": {"x": 77, "y": 315, "w": 320, "h": 50},
    "default": {"x": 37, "y": 230, "w": 1125, "h": 405},
}

DEFAULT_STYLES: dict[str, dict[str, object]] = {
    "slideTitle": {
        "text_vertical": "top",
        "text_horizontal": "left",
        "font_size": 50,
        "weight": 700,
        "text_transform": "none",
    },
    "subTitle": {
        "text_vertical": "top",
        "text_horizontal": "left",
        "font_size": 25,
        "weight": 400,
        "text_transform": "none",
    },
    "blockTitle": {
        "text_vertical": "top",
        "text_horizontal": "left",
        "font_size": 25,
        "weight": 700,
        "text_transform": "none",
    },
    "text": {
        "text_vertical": "top",
        "text_horizontal": "left",
        "font_size": 20,
        "weight": 400,
        "text_transform": "none",
    },
    "number": {
        "text_vertical": "top",
        "text_horizontal": "center",
        "font_size": 50,
        "weight": 700,
        "text_transform": "none",
    },
    "default": {
        "text_vertical": "top",
        "text_horizontal": "left",
        "font_size": 20,
        "weight": 400,
        "text_transform": "none",
    },
}

# Default values for new tables
SLIDE_LAYOUT_ADDITIONAL_INFO = {
    "percentesCount": 0,
    "maxSymbolsInBlock": 0,
    "hasHeaders": False,
    "type": "classic",
    "infographicsType": None,
}

SLIDE_LAYOUT_DIMENSIONS = {"x": 0, "y": 0, "w": 1200, "h": 675}

# Output configuration
OUTPUT_CONFIG = {
    "output_dir": "my_sql_output",
    "filename_template": "{slide_layout_name}_{timestamp}.sql",
    "timestamp_format": "%b%d_%H-%M",  # e.g., Mar10_14-23
}

SLIDE_NUMBER_TO_FOLDER = {
    1: "title",
    2: "1cols",
    3: "2cols",
    4: "3cols",
    5: "infographics",
    6: "4cols",
    7: "divider",
    8: "table",
    9: "5cols",
    10: "6cols",
    11: "7cols",
    12: "8cols",
    13: "chart",
    14: "10cols",
    -1: "last",
}

SLIDE_NUMBER_TO_TYPE = {
    1: "title",  # title
    2: "fewText",  # 1cols
    3: "optimalText",  # 2cols
    4: "manyText",  # 3cols
    5: "infographics",  # infographics
    6: "extraText",  # 4cols
    7: "other",  # divider
    8: "table",  # table
    9: "other",  # 5 cols
    10: "other",  # 6cols
    11: "other",  # 7cols
    12: "other",  # 8cols
    13: "chart",  # chart
    14: "other",  # 10cols
    -1: "last",  # last
}


CONTAINER_NAME_TO_SLIDE_NUMBER = {
    "title": 1,
    "1cols": 2,
    "2cols": 3,
    "3cols": 4,
    "infographics": 5,
    "4cols": 6,
    "divider": 7,
    "table": 8,
    "5cols": 9,
    "6cols": 10,
    "7cols": 11,
    "8cols": 12,
    "chart": 13,
    "10cols": 14,
    "last": -1,
}

FIGMA_TO_SQL_BLOCK_MAPPING = {
    "text": "text",
    "slideTitle": "slideTitle",
    "slidetitle": "slideTitle",
    "slide_title": "slideTitle",
    "blockTitle": "blockTitle",
    "blocktitle": "blockTitle",
    "block_title": "blockTitle",
    "subTitle": "subTitle",
    "subtitle": "subTitle",
    "sub_title": "subTitle",
    "image": "image",
    "background": "background",
    "figure": "figure",
    "table": "table",
    "infographik": "infographik",
    "chart": "chart",
    "watermark": "watermark",
    "icon": "icon",
    "number": "number",
    "num": "number",
    "email": "email",
    "date": "date",
    "name": "name",
    "percentage": "percentage",
}

# Infographics type mapping based on slide layout name patterns
SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE = {
    "step_by_step": {"infographicsType": "grid_timeline"},
    "grid_cards_horizontal": {"infographicsType": "grid"},
    "grid_cards_vertical": {"infographicsType": "grid"},
    "timeline": {"infographicsType": "timeline"},
    "table_bottom": {"infographicsType": "table"},
    "center_horizontal_chart": {"infographicsType": "bar_horizontal"},
    "center_linear_chart": {"infographicsType": "line"},
    "center_circle_chart": {"infographicsType": "pie"},
    "center_ring_chart": {"infographicsType": "doughnut"},
    "center_bar_chart": {"infographicsType": "bar"},
}
