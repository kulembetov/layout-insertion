from typing import Any

from .types import PrecompiledImagesConfig, SlideLayoutType

# Precompiled Images configuration
PRECOMPILED_IMAGES: PrecompiledImagesConfig = {
    "base_url": "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/raiffeisen",
    "default_colors": ["#bae4e4", "#c6d6f2", "#dfe8f5", "#e3dcf8", "#f0f0f0", "#f5e7e7", "#fad2be"],  # мятно-бирюзовый  # холодно-синий  # небесно-голубой  # сиреневый  # светло-серый  # розово-бежевый  # персиково-оранжевый
    "prefix": ["Green", "Blue", "Sky", "Purple", "Gray", "Pink", "Orange"],
}


# ========================
# Defaults and Templates
# ========================


MINIATURES_BASE_PATH: str = "/assets/miniatures/raiffeisen"
DEFAULT_COLOR_SETTINGS_ID: str = "019565bd-99ce-792c-86fd-0188712beb9b"
DEFAULT_COLOR: str = "#ffffff"
MINIATURE_EXTENSION: str = ".png"

# Default values for user inputs
DEFAULT_VALUES: dict[str, Any] = {
    "slide_layout_name": "grid_cards_horizontal",
    "slide_layout_number": 9,
    "presentation_layout_id": "0197c55e-1c1b-7760-9525-f51752cf23e2",
    "slide_layout_type": SlideLayoutType.CLASSIC,
    "num_blocks": 5,
}


# Default Z-index mappings
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

# Default dimensions for different block types
DEFAULT_DIMENSIONS: dict[str, dict[str, int]] = {
    "background": {"x": 0, "y": 0, "w": 1200, "h": 675},
    "slideTitle": {"x": 37, "y": 37, "w": 1125, "h": 85},
    "subTitle": {"x": 37, "y": 250, "w": 875, "h": 65},
    "blockTitle": {"x": 37, "y": 37, "w": 575, "h": 30},
    "text": {"x": 37, "y": 37, "w": 575, "h": 85},
    "number": {"x": 77, "y": 315, "w": 320, "h": 50},
    "default": {"x": 37, "y": 230, "w": 1125, "h": 405},
}

DEFAULT_STYLES: dict[str, dict[str, Any]] = {
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

# Output configuration
OUTPUT_CONFIG = {
    "output_dir": "my_sql_output",
    "filename_template": "{slide_layout_name}_{timestamp}.sql",
    "timestamp_format": "%b%d_%H-%M",  # e.g., Mar10_14-23
}

FIGMA_TO_SQL_BLOCK_MAPPING: dict[str, str] = {
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
    "img": "image",
    "picture": "image",
    "background": "background",
    "bg": "background",
    "figure": "figure",
    "fig": "figure",
    "table": "table",
    "infographik": "infographik",
    "infographic": "infographik",
    "chart": "chart",
    "watermark": "watermark",
    "icon": "icon",
    "number": "number",
    "num": "number",
    "email": "email",
    "date": "date",
    "name": "name",
    "percentage": "percentage",
    "percent": "percentage",
    "%": "percentage",
    "title": "slideTitle",
    "heading": "slideTitle",
    "header": "blockTitle",
    "paragraph": "text",
    "body": "text",
    "content": "text",
    "caption": "text",
    "label": "text",
}

FIGMA_CONFIG: dict[str, Any] = {"TARGET_WIDTH": 1200, "TARGET_HEIGHT": 675, "OUTPUT_DIR": "figma_extract", "OUTPUT_FILE": "extracted_data"}

# Valid font weights - ONLY these are allowed
VALID_FONT_WEIGHTS = [300, 400, 700]
