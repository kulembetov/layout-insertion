import os
from dotenv import load_dotenv
load_dotenv()

"""
Configuration file for the SQL Generator
Contains all default values, templates, and configurations
"""

FIGMA_FILE_ID = os.environ.get("FIGMA_FILE_ID", "")
FIGMA_TOKEN = os.environ.get("FIGMA_TOKEN", "")

# Base path for slide layout miniatures
MINIATURES_BASE_PATH = "/assets/miniatures/rfs"

# Default ColorSettings ID to use for all blocks
DEFAULT_COLOR_SETTINGS_ID = "019565bd-99ce-792c-86fd-0188712beb9b"

# Default color
DEFAULT_COLOR = "#ffffff"

# Precompiled Images configuration
PRECOMPILED_IMAGES = {
    "base_url": "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/raiffeisen",
    "default_colors": [
        "#e9eaea",
        "#d7cdf5",
        "#f1dddd",
        "#fad2be",
        "#d2def0",
        "#adc5ed",
        "#9cd8d8"

    ],
    "prefix": [
        "Gray",
        "Purple",
        "Pink",
        "Orange",
        "Sky",
        "Blue"
        "Green"
    ]
}

# Slide layout types enum
SLIDE_LAYOUT_TYPES = {
    "classic": "classic",
    "many_text": "manyText",
    "few_text": "fewText",
    "optimal_text": "optimalText",
    "chart": "chart",
    "table": "table",
    "infographics": "infographics",
    "title": "title",
    "last": "last",
    "other": "other"
}

# Automatic blocks configuration
AUTO_BLOCKS = {
    "add_background": True,  # Always add background by default
    "add_watermark": False,  # Default to not adding watermark
    "background": {
        "color": "#ffffff",
        "dimensions": {
            "x": 0,
            "y": 0,
            "w": 1200,
            "h": 675
        },
        "z_index": 0
    },
    "watermark": {
        "dimensions": {
            "x": 1065,
            "y": 636,
            "w": 118,
            "h": 26
        }
    },
    # Special configuration for last slide (slide number -1)
    "last_slide": {
        "watermark1": {
            "dimensions": {
                "x": 785,
                "y": 40,
                "w": 380,
                "h": 114
            }
        }
    }
}

# Default values for user inputs
DEFAULT_VALUES = {
    "slide_layout_name": "grid_cards_horizontal",
    "slide_layout_number": 9,
    "presentation_layout_id": "0197c55e-1c1b-7760-9525-f51752cf23e2",
    "slide_layout_type": SLIDE_LAYOUT_TYPES["classic"],
    "num_blocks": 5,
}

# Block type groups
BLOCK_TYPES = {
    "null_style_types": ['infographik', 'figure', 'table', 'background', 'image', 'icon'],
    "z_index_types": [
        'text', 'slideTitle', 'blockTitle', 'email', 'date', 'name',
        'percentage', 'image', 'infographik', 'table', 'figure', 'background', 'icon', 'subTitle', 'number'
    ],
    "block_layout_type_options": [
        'text', 'slideTitle', 'blockTitle', 'email', 'date', 'name',
        'percentage', 'image', 'infographik', 'table', 'figure', 'background', 'watermark', 'icon', 'subTitle', 'number'
    ],
}

# Default Z-index mappings
Z_INDEX_DEFAULTS = {
    'background': 0,
    'watermark': 10,
    'figure': 1,
    'image': 2,
    'icon': 2,
    'infographik': 2,
    'table': 2,
    'text': 3,
    'slideTitle': 3,
    'subTitle': 3,
    'blockTitle': 3,
    'number': 3,
    'email': 3,
    'date': 3,
    'name': 3,
    'percentage': 3,
    'default': 1,
}

# Default dimensions for different block types
DEFAULT_DIMENSIONS = {
    'background': {
        'x': 0,
        'y': 0,
        'w': 1200,
        'h': 675
    },
    'slideTitle': {
        'x': 37,
        'y': 37,
        'w': 1125,
        'h': 85
    },
    'subTitle': {
        'x': 37,
        'y': 250,
        'w': 875,
        'h': 65
    },
    'blockTitle': {
        'x': 37,
        'y': 37,
        'w': 575,
        'h': 30
    },
    'text': {
        'x': 37,
        'y': 37,
        'w': 575,
        'h': 85
    },
    'number': {
        'x': 77,
        'y': 315,
        'w': 320,
        'h': 50
    },
    'default': {
        'x': 37,
        'y': 230,
        'w': 1125,
        'h': 405
    },
}

# Default styles by block type
DEFAULT_STYLES = {
    'slideTitle': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 50,
        'weight': 700,
        'text_transform': 'none'
    },
    'subTitle': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 25,
        'weight': 400,
        'text_transform': 'none'
    },
    'blockTitle': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 25,
        'weight': 700,
        'text_transform': 'none'
    },
    'text': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 20,
        'weight': 400,
        'text_transform': 'none'
    },
    'number': {
        'text_vertical': 'top',
        'text_horizontal': 'center',
        'font_size': 50,
        'weight': 700,
        'text_transform': 'none'
    },
    'default': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 20,
        'weight': 400,
        'text_transform': 'none'
    },
}

# Default values for new tables
SLIDE_LAYOUT_ADDITIONAL_INFO = {
    "percentesCount": 0,
    "maxSymbolsInBlock": 0,
    "hasHeaders": False,
    "type": "classic"
}

SLIDE_LAYOUT_DIMENSIONS = {
    "x": 0,
    "y": 0,
    "w": 1200,
    "h": 675
}

# SQL templates for generating queries
SQL_TEMPLATES = {
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
    0,
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
INSERT INTO "BlockLayoutStyles" ("blockLayoutId", "textVertical", "textHorizontal", "fontSize", "weight", "zIndex", "color", "textTransform", "borderRadius", "colorSettingsId")
VALUES
{styles_values}
RETURNING *;""",

    "block_dimensions": """-- Create BlockLayoutDimensions
INSERT INTO "BlockLayoutDimensions" ("blockLayoutId", "x", "y", "w", "h")
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
    "slideLayoutId", "percentesCount", "maxSymbolsInBlock", "hasHeaders", "type", "iconUrl"
) VALUES (
    '{slide_layout_id}',
    {percentesCount},
    {maxSymbolsInBlock},
    {hasHeaders},
    '{type}'::"SlideLayoutType",
    '{icon_url}'
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
RETURNING *;"""
}

# Output configuration
OUTPUT_CONFIG = {
    "output_dir": "../new_standard",
    "filename_template": "{slide_layout_name}_{timestamp}.sql",
    "timestamp_format": "%b%d_%H-%M",  # e.g., Mar10_14-23
}

SLIDE_NUMBER_TO_FOLDER = {
    1: "hero",
    2: "1cols",
    3: "2cols",
    4: "3cols",
    5: "infographics",
    6: "4cols",
    7: "5cols",
    8: "divider",
    9: "table",
    10: "6cols",
    11: "7cols",
    12: "chart",
    -1: "last"
}

SLIDE_NUMBER_TO_NUMBER = {
    1: None,        # hero
    2: 1,           # 1cols
    3: 2,           # 2cols
    4: 3,           # 3cols
    5: None,        # infographics
    6: 4,           # 4cols
    7: None,        # 5cols
    8: None,        # divider
    9: None,        # table
    10: 6,          # 6cols
    11: 7,          # 7cols
    12: None,       # chart
    -1: None        # last
}

SLIDE_NUMBER_TO_TYPE = {
    1: 'title',         # hero
    2: 'few_text',      # 1cols
    3: 'optimal_text',  # 2cols
    4: 'many_text',     # 3cols
    5: 'extra_text',    # 4cols
    6: 'other',         # 5cols
    7: 'other',         # 6cols
    8: 'other',         # 7cols
    9: 'table',         # table
    10: 'chart',        # chart
    11: 'infographics', # infographics
    12: 'other',        # divider (if needed)
    -1: 'last'          # last
}

WATERMARK_SLIDES = []

CONTAINER_NAME_TO_SLIDE_NUMBER = {
    "hero": 1,
    "1cols": 2,
    "2cols": 3,
    "3cols": 4,
    "infographics": 5,
    "4cols": 6,
    "5cols": 7,
    "divider": 8,
    "table": 9,
    "6cols": 10,
    "7cols": 11,
    "chart": 12,
    "last": -1
}

FIGMA_TO_SQL_BLOCK_MAPPING = {
    'text': 'text',
    'slideTitle': 'slideTitle',
    'slidetitle': 'slideTitle',
    'slide_title': 'slideTitle',
    'blockTitle': 'blockTitle',
    'blocktitle': 'blockTitle',
    'block_title': 'blockTitle',
    'subTitle': 'subTitle',
    'subtitle': 'subTitle',
    'sub_title': 'subTitle',
    'image': 'image',
    'img': 'image',
    'picture': 'image',
    'background': 'background',
    'bg': 'background',
    'figure': 'figure',
    'fig': 'figure',
    'table': 'table',
    'infographik': 'infographik',
    'infographic': 'infographik',
    'chart': 'chart',
    'watermark': 'watermark',
    'icon': 'icon',
    'number': 'number',
    'num': 'number',
    'email': 'email',
    'date': 'date',
    'name': 'name',
    'percentage': 'percentage',
    'percent': 'percentage',
    '%': 'percentage',
    'title': 'slideTitle',
    'heading': 'slideTitle',
    'header': 'blockTitle',
    'paragraph': 'text',
    'body': 'text',
    'content': 'text',
    'caption': 'text',
    'label': 'text',
}