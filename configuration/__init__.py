# pyright: strict
from __future__ import annotations

from .defaults import DEFAULT_COLOR, DEFAULT_COLOR_SETTINGS_ID, DEFAULT_VALUES, MINIATURE_EXTENSION, MINIATURES_BASE_PATH, SLIDE_LAYOUT_ADDITIONAL_INFO, SLIDE_LAYOUT_DIMENSIONS

# Единая точка импорта для остального кода.
from .env import FigmaSettings, figma_settings
from .figma import FIGMA_CONFIG, VALID_FONT_WEIGHTS, BlockType, FigmaKey, FigmaNodeType
from .mappings import AUTO_BLOCKS, BLOCK_TYPE_MIN_WORDS, BLOCK_TYPES, CONTAINER_NAME_TO_SLIDE_NUMBER, DEFAULT_DIMENSIONS, DEFAULT_STYLES, FIGMA_TO_SQL_BLOCK_MAPPING, SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE, SLIDE_LAYOUT_TYPES, SLIDE_NUMBER_TO_FOLDER, SLIDE_NUMBER_TO_NUMBER, SLIDE_NUMBER_TO_TYPE, Z_INDEX_DEFAULTS
from .output import OUTPUT_CONFIG
from .precompiled_images import PRECOMPILED_IMAGES, PrecompiledImagesConfig
from .sql_templates import SQL_TEMPLATES
from .types import BlockLayoutType, Dimensions, SlideLayoutType, Style, TextHorizontal, TextTransform, TextVertical

__all__ = [
    # env
    "FigmaSettings",
    "figma_settings",
    # figma
    "FigmaKey",
    "FigmaNodeType",
    "BlockType",
    "FIGMA_CONFIG",
    "VALID_FONT_WEIGHTS",
    # precompiled
    "PrecompiledImagesConfig",
    "PRECOMPILED_IMAGES",
    # defaults
    "MINIATURES_BASE_PATH",
    "DEFAULT_COLOR_SETTINGS_ID",
    "DEFAULT_COLOR",
    "MINIATURE_EXTENSION",
    "DEFAULT_VALUES",
    "SLIDE_LAYOUT_ADDITIONAL_INFO",
    "SLIDE_LAYOUT_DIMENSIONS",
    # sql
    "SQL_TEMPLATES",
    # mappings
    "SLIDE_LAYOUT_TYPES",
    "AUTO_BLOCKS",
    "BLOCK_TYPES",
    "BLOCK_TYPE_MIN_WORDS",
    "Z_INDEX_DEFAULTS",
    "DEFAULT_DIMENSIONS",
    "DEFAULT_STYLES",
    "SLIDE_NUMBER_TO_FOLDER",
    "SLIDE_NUMBER_TO_NUMBER",
    "SLIDE_NUMBER_TO_TYPE",
    "CONTAINER_NAME_TO_SLIDE_NUMBER",
    "FIGMA_TO_SQL_BLOCK_MAPPING",
    "SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE",
    # output
    "OUTPUT_CONFIG",
    # types
    "Dimensions",
    "Style",
    "TextVertical",
    "TextHorizontal",
    "TextTransform",
    "SlideLayoutType",
    "BlockLayoutType",
]
