import argparse
import ast
import csv
import json
import logging
import os
import re
import shutil
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict

import config
import uuid_utils as uuid


@dataclass
class SlideLayoutIndexConfig:
    id: str
    presentation_palette_id: str
    block_layout_config_id: str
    matched_background_color: str
    config_background_colors: list[str]


# Load slide layout index config mapping data
slide_layout_index_config_mapping = []
with open("slide_layout_index_config_mapping.csv") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Convert the string representation of list to an actual list

        config_bg_colors = ast.literal_eval(row["config_background_colors"]) if row["config_background_colors"] else []

        # Create an instance of SlideLayoutIndexConfig
        config_obj = SlideLayoutIndexConfig(
            id=row["id"],
            presentation_palette_id=row["presentationPaletteId"],
            block_layout_config_id=row["blockLayoutConfigId"],
            matched_background_color=row["matched_background_color"],
            config_background_colors=config_bg_colors,
        )
        slide_layout_index_config_mapping.append(config_obj)


def load_block_layout_config_mapping() -> list[dict]:
    """
    Load block layout config mapping data from CSV file.

    Returns:
        List of dictionaries containing block layout config data
    """
    try:
        block_layout_config_mapping = []
        with open("block_layout_config_mapping.csv") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                block_layout_config_mapping.append(
                    {
                        "id": row["id"],
                        "font": row.get("font", "{}"),
                        "background": row.get("background", "{}"),
                    }
                )
        logger.info(f"Loaded {len(block_layout_config_mapping)} block layout config mappings")
        return block_layout_config_mapping
    except FileNotFoundError:
        logger.error("block_layout_config_mapping.csv not found")
        return []
    except Exception as e:
        logger.error(f"Error loading block layout config mapping: {e}")
        return []


# Helper to set up the logger file handler in any mode
def setup_slide_insertion_logger(output_dir):
    """Set up a file logger for slide insertion operations in the specified output directory."""
    logger = logging.getLogger(__name__)
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "slide_insertion.log")
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    # Remove any previous file handlers to avoid duplicate logs
    for h in logger.handlers[:]:
        if isinstance(h, logging.FileHandler):
            logger.removeHandler(h)
    logger.addHandler(file_handler)
    logger.propagate = False
    logger.info("Logger initialized and writing to %s", log_path)


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ================ Helper Functions ================


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


# ================ Domain Models ================


class Dimensions(TypedDict):
    x: int
    y: int
    w: int
    h: int
    rotation: int


class BlockStyles(TypedDict):
    textVertical: str
    textHorizontal: str
    fontSize: int
    weight: int
    zIndex: int
    textTransform: str
    color: str


@dataclass
class Figure:
    block_id: str
    name: str
    color: str
    id: str = field(default_factory=str)


@dataclass
class PrecompiledImage:
    block_layout_id: str
    url: str
    color: str | None = None
    id: str = field(default_factory=str)


@dataclass
class Block:
    id: str = field(default_factory=str)
    type: str = field(default_factory=str)
    dimensions: dict = field(default_factory=dict)
    styles: dict = field(default_factory=dict)
    needs_null_styles: bool = False
    needs_z_index: bool = False
    is_figure: bool = False
    is_background: bool = False
    is_precompiled_image: bool = False
    color: str | None = None
    figure_info: dict | None = None
    precompiled_image_info: list | None = None
    border_radius: list = field(default_factory=lambda: [0, 0, 0, 0])
    name: str = ""
    index: int | None = None  # Store the index extracted from the block name (e.g., "text_1" -> index=1)
    opacity: int = 1
    words: int = 1
    font_family: str | None = None  # Store the font family for font index extraction


@dataclass
class SlideLayout:
    id: str = field(default_factory=str)
    name: str = field(default_factory=str)
    number: int = 0
    presentation_layout_id: str = field(default_factory=str)
    is_last: bool = False
    type_key: str = field(default_factory=str)
    type: str = field(default_factory=str)
    icon_url: str = field(default_factory=str)
    for_generation: bool = True
    imagesCount: int = 0


# ================ Configuration ================


class ConfigManager:
    """Manages configuration for the SQL generator."""

    def __init__(self, config_module):
        """Initialize ConfigManager with a config module."""
        self.config = config_module

    def get_default_value(self, key):
        """Get the default value for a given key from config."""
        return self.config.DEFAULT_VALUES.get(key)

    def get_slide_layout_type(self, key):
        """Get the slide layout type for a given key from config."""
        return self.config.SLIDE_LAYOUT_TYPES.get(key)

    def get_block_type_options(self):
        """Get available block type options from config."""
        return self.config.BLOCK_TYPES["block_layout_type_options"]

    def is_null_style_type(self, block_type):
        """Check if the block type should use null styles."""
        return block_type in self.config.BLOCK_TYPES["null_style_types"]

    def is_z_index_type(self, block_type):
        """Check if the block type should use z-index."""
        return block_type in self.config.BLOCK_TYPES["z_index_types"]

    def get_default_z_index(self, block_type):
        """Get the default z-index for a block type."""
        return self.config.Z_INDEX_DEFAULTS.get(block_type, self.config.Z_INDEX_DEFAULTS["default"])

    def get_default_dimensions(self, block_type, is_first_block=False):
        """Get the default dimensions for a block type."""
        if block_type in self.config.DEFAULT_DIMENSIONS:
            return self.config.DEFAULT_DIMENSIONS[block_type]
        return self.config.DEFAULT_DIMENSIONS["default"]

    def get_default_styles(self, block_type):
        """Get the default styles for a block type."""
        if block_type in self.config.DEFAULT_STYLES:
            return self.config.DEFAULT_STYLES[block_type]
        return self.config.DEFAULT_STYLES["default"]

    def get_block_config(self, key):
        """Get the auto block configuration for a given key."""
        return self.config.AUTO_BLOCKS.get(key, {})

    def should_add_background(self):
        """Return True if a background block should be added."""
        return self.config.AUTO_BLOCKS.get("add_background", False)

    def get_sql_template(self, key):
        """Get the SQL template for a given key."""
        return self.config.SQL_TEMPLATES.get(key, "")

    def get_slide_layout_additional_info(self):
        """Get additional info for the slide layout."""
        return self.config.SLIDE_LAYOUT_ADDITIONAL_INFO

    def get_slide_layout_dimensions(self):
        """Get the dimensions for the slide layout."""
        return self.config.SLIDE_LAYOUT_DIMENSIONS

    def get_output_config(self):
        """Get the output configuration dictionary."""
        return self.config.OUTPUT_CONFIG

    def get_default_color(self):
        """Get the default color from config."""
        return self.config.DEFAULT_COLOR

    def get_default_color_settings_id(self):
        """Get the default color settings ID from config."""
        return self.config.DEFAULT_COLOR_SETTINGS_ID

    def get_miniatures_base_path(self):
        """Get the base path for slide layout miniatures."""
        return self.config.MINIATURES_BASE_PATH

    def get_folder_for_slide_number(self, slide_number):
        """Get the output folder name based on slide number."""
        return self.config.SLIDE_NUMBER_TO_FOLDER.get(slide_number, "other")

    def get_precompiled_images_base_url(self):
        """Get the base URL for precompiled images."""
        return self.config.PRECOMPILED_IMAGES.get("base_url", "")

    def get_precompiled_images_default_colors(self):
        """Get the list of default colors for precompiled images."""
        return self.config.PRECOMPILED_IMAGES.get("default_colors", ["#ffffff"])


# ================ Utility Services ================


# ================ Block Factory ================


class BlockFactory:
    """Factory for creating different types of blocks"""

    def __init__(self, config_manager: ConfigManager, id_generator):
        self.config = config_manager
        self.id_generator = id_generator

    def create_background_block(self, bg_config):
        """Create a background block with specified config"""
        bg_id = generate_uuid()
        bg_dims = bg_config["dimensions"]

        return Block(
            id=bg_id,
            type=BlockTypes.BACKGROUND,
            needs_null_styles=True,
            needs_z_index=True,
            is_figure=False,
            is_background=True,
            is_precompiled_image=False,
            color=bg_config["color"],
            styles={
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": self.config.get_default_z_index("background"),
                "textTransform": None,
                "color": "#ffffff",
            },
            dimensions={
                "x": bg_dims["x"],
                "y": bg_dims["y"],
                "w": bg_dims["w"],
                "h": bg_dims["h"],
            },
        )

    @staticmethod
    def create_block_from_dict(block_dict: dict, extra: dict | None = None) -> Block:
        """
        Create a Block from a dict (Figma JSON or user input), handling all defaults and normalization.
        extra: optional dict for overrides (e.g., id, name, index, etc.)
        """
        data = dict(block_dict)  # shallow copy
        extra = extra or {}
        # Use provided or generate id
        block_id = extra.get("id") or data.get("id") or generate_uuid()
        # Normalize/clean name
        name = extra.get("name") or data.get("name") or ""
        name = BlockNameUtils.normalize_name(name)
        # Index
        index = extra.get("index") if "index" in extra else data.get("index")
        # Styles
        styles = dict(data.get("styles", {}))
        # Dimensions
        dimensions = dict(data.get("dimensions", {}))
        # Border radius
        border_radius = styles.get("borderRadius") or data.get("border_radius") or [0, 0, 0, 0]
        # Opacity
        opacity = styles.get("opacity") or data.get("opacity", 1)
        # Words
        words = data.get("words", 1)
        # Font family
        font_family = data.get("font_family")
        # Flags
        needs_null_styles = data.get("needs_null_styles", False)
        needs_z_index = data.get("needs_z_index", False)
        is_figure = data.get("is_figure", False)
        is_background = data.get("is_background", False)
        is_precompiled_image = data.get("is_precompiled_image", False)
        # Info
        color = data.get("color")
        figure_info = data.get("figure_info")
        precompiled_image_info = data.get("precompiled_image_info")
        # Compose
        return Block(
            id=block_id,
            type=data.get("type", ""),
            dimensions=dimensions,
            styles=styles,
            needs_null_styles=needs_null_styles,
            needs_z_index=needs_z_index,
            is_figure=is_figure,
            is_background=is_background,
            is_precompiled_image=is_precompiled_image,
            color=color,
            figure_info=figure_info,
            precompiled_image_info=precompiled_image_info,
            border_radius=border_radius,
            name=name,
            index=index,
            opacity=opacity,
            words=words,
            font_family=font_family,
        )

    @staticmethod
    def extract_figure_info(block_dict, block_uuid, clean_block_name, color):
        if block_dict.get("type") != BlockTypes.FIGURE:
            return None
        # Extract figure name from clean_block_name (handle (name_N) or just name)
        match = re.search(r"\(([^)]+)\)", clean_block_name)
        if match:
            figure_name = match.group(1)
            figure_name = re.sub(r"_\d+", "", figure_name)
        else:
            figure_name = clean_block_name
        normalized_color = ColorUtils.normalize_color(color) if color else None
        figure_color = normalized_color if normalized_color is not None else "#ffffff"
        return {
            "block_id": block_uuid,
            "name": figure_name,
            "color": figure_color,
        }

    @staticmethod
    def extract_precompiled_image_info(block_dict, block_uuid):
        if block_dict.get("type") != BlockTypes.IMAGE or not block_dict.get("name", "").startswith("image precompiled"):
            return None
        match = re.match(
            r"image precompiled ([^ ]+)(?: z-index \d+)?(?: (#[0-9a-fA-F]{3,6}))?",
            block_dict["name"],
        )
        if not match:
            return None
        base_name = match.group(1)
        block_index = BlockNameUtils.extract_index(base_name, BlockTypes.IMAGE)
        if block_index is not None:
            base_name = re.sub(r"_\d+$", "", base_name)
        base_url = config.PRECOMPILED_IMAGES["base_url"]
        colors = config.PRECOMPILED_IMAGES["default_colors"]
        prefixes = config.PRECOMPILED_IMAGES["prefix"]
        precompiled_images = []
        if match.group(2):
            color_val = ColorUtils.normalize_color(match.group(2))
            url = f"{base_url}/{base_name}.png"
            precompiled_images.append(
                {
                    "block_layout_id": block_uuid,
                    "url": url,
                    "color": color_val,
                }
            )
        else:
            for color_val, prefix in zip(colors, prefixes):
                norm_color = ColorUtils.normalize_color(color_val)
                variant_name = f"{base_name}{prefix}"
                url = f"{base_url}/{variant_name}.png"
                precompiled_images.append(
                    {
                        "block_layout_id": block_uuid,
                        "url": url,
                        "color": norm_color,
                    }
                )
        return precompiled_images


# ================ Centralized Data Cleaning System ================


class CleaningRule:
    """Base class for cleaning rules."""

    def apply(self, text: str) -> str:
        """Apply the cleaning rule to the text."""
        raise NotImplementedError


class RegexCleaningRule(CleaningRule):
    """Cleaning rule that uses regex substitution."""

    def __init__(self, pattern: str, replacement: str = "", flags: int = 0):
        self.pattern = pattern
        self.replacement = replacement
        self.flags = flags

    def apply(self, text: str) -> str:
        return re.sub(self.pattern, self.replacement, text, flags=self.flags)


class StripCleaningRule(CleaningRule):
    """Cleaning rule that strips whitespace and specific characters."""

    def __init__(self, chars: str | None = None):
        self.chars = chars

    def apply(self, text: str) -> str:
        return text.strip(self.chars)


class DataCleaner:
    """Centralized, extensible data cleaning system."""

    # Pre-defined rule sets for different data types
    NAME_RULES = [
        RegexCleaningRule(r"\s*background_\d+", "", re.IGNORECASE),  # Remove background_N
        RegexCleaningRule(r"\s*z-index\s*\d+.*", "", re.IGNORECASE),  # Remove z-index N and everything after
        RegexCleaningRule(r"_\d+$", ""),  # Remove trailing _N
        RegexCleaningRule(r"\s+", " "),  # Normalize multiple spaces to single
        StripCleaningRule(),  # Strip leading/trailing whitespace
    ]

    SLIDE_NAME_RULES = [
        RegexCleaningRule(r"\s*background_\d+", "", re.IGNORECASE),
        RegexCleaningRule(r"\s*z-index\s*\d+.*", "", re.IGNORECASE),
        RegexCleaningRule(r"\s+", " "),
        StripCleaningRule(),
    ]

    FONT_RULES = [
        StripCleaningRule(),  # Strip whitespace first
        RegexCleaningRule(r"[^a-z0-9_]", ""),  # Keep only alphanumeric and underscore
    ]

    COLOR_RULES = [
        StripCleaningRule(),  # Strip whitespace
    ]

    @staticmethod
    def clean_with_rules(text: str, rules: Sequence[CleaningRule]) -> str:
        """Apply a list of cleaning rules in sequence."""
        if not text:
            return ""

        result = text
        for rule in rules:
            result = rule.apply(result)
        return result

    @classmethod
    def clean_block_name(cls, name: str) -> str:
        """Clean a block name using standard rules."""
        return cls.clean_with_rules(name, cls.NAME_RULES)

    @classmethod
    def clean_slide_name(cls, name: str) -> str:
        """Clean a slide layout name using standard rules."""
        return cls.clean_with_rules(name, cls.SLIDE_NAME_RULES)

    @classmethod
    def clean_font_name(cls, name: str) -> str:
        """Clean and normalize a font name."""
        if not name:
            return "roboto"  # Default font

        # Convert to lowercase and replace spaces/hyphens with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        return cls.clean_with_rules(normalized, cls.FONT_RULES)

    @classmethod
    def normalize_color(cls, color: str) -> str | None:
        """Normalize a color string to standard hex format."""
        if not color or not isinstance(color, str):
            return None

        cleaned = cls.clean_with_rules(color, cls.COLOR_RULES).lower()

        # Handle hex colors
        if cleaned.startswith("#"):
            cleaned = cleaned.lstrip("#")
        if re.fullmatch(r"[0-9a-f]{6}", cleaned):
            return f"#{cleaned}"
        if re.fullmatch(r"[0-9a-f]{3}", cleaned):
            # Expand short hex to full
            cleaned = "".join([c * 2 for c in cleaned])
            return f"#{cleaned}"
        return None

    @classmethod
    def extract_index(cls, name: str, block_type: str | None = None) -> int | None:
        """Extract numeric index from name using various patterns."""
        if not name:
            return None

        # Figure with parentheses: figure (name_N)
        paren_match = re.search(r"\(([^)]+)\)", name)
        if paren_match:
            inner = paren_match.group(1)
            idx_match = re.search(r"_(\d+)", inner)
            if idx_match:
                return int(idx_match.group(1))

        # Block type specific: background_N, percentage_N, etc.
        if block_type:
            pattern = rf"{block_type}[_\s-]*(\d+)"
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return int(match.group(1))

        # General _N at the end
        match = re.search(r"_(\d+)$", name)
        if match:
            return int(match.group(1))

        # percentage N (with space)
        match = re.search(r"percentage\s*(\d+)", name, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None


# ================ Color Utils ================


class ColorUtils:
    @staticmethod
    def normalize_color(color: str) -> str | None:
        """
        Normalize a color string to a standard hex format (#aabbcc, lowercase).
        Returns None if the color is invalid or empty.
        """
        return DataCleaner.normalize_color(color)


class BlockTypes:
    FIGURE = "figure"
    IMAGE = "image"
    BACKGROUND = "background"
    TEXT = "text"
    SLIDE_TITLE = "slideTitle"
    BLOCK_TITLE = "blockTitle"
    EMAIL = "email"
    DATE = "date"
    NAME = "name"
    PERCENTAGE = "percentage"
    ICON = "icon"
    SUBTITLE = "subTitle"
    NUMBER = "number"
    WATERMARK = "watermark"
    TABLE = "table"
    INFOGRAPHIK = "infographik"
    CHART = "chart"


# ================ SQL Command Pattern ================


class SQLCommand(ABC):
    """Base class for SQL commands"""

    @abstractmethod
    def execute(self) -> str:
        """Execute the command and return SQL"""


class SlideLayoutCommand(SQLCommand):
    """Generates SlideLayout SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout, current_time: str):
        self.config = config
        self.slide_layout = slide_layout
        self.current_time = current_time

    def execute(self) -> str:
        """Generate SlideLayout SQL"""
        return self.config.get_sql_template("slide_layout").format(
            slide_layout_id=self.slide_layout.id,
            slide_layout_name=self.slide_layout.name,
            slide_layout_number=self.slide_layout.number,
            presentation_layout_id=self.slide_layout.presentation_layout_id,
            imagesCount=self.slide_layout.imagesCount,
            is_last=str(self.slide_layout.is_last).lower(),
            for_generation=str(self.slide_layout.for_generation).lower(),
        )


class BlockLayoutCommand(SQLCommand):
    """Generates BlockLayout SQL"""

    def __init__(self, config: ConfigManager, blocks: list[Block], slide_layout_id: str):
        self.config = config
        self.blocks = blocks
        self.slide_layout_id = slide_layout_id

    def execute(self) -> str:
        """Generate BlockLayout SQL"""
        values = self._format_block_layout_values()
        return self.config.get_sql_template("block_layout").format(block_layout_values=values)

    def _format_block_layout_values(self) -> str:
        """Format the values for BlockLayout SQL"""
        values = []
        for block in self.blocks:
            values.append(f"    ('{block.id}', '{self.slide_layout_id}', '{block.type}'::\"BlockLayoutType\")")
        return ",\n".join(values)


class BlockStylesCommand(SQLCommand):
    """Generates BlockLayoutStyles SQL"""

    def __init__(self, config: ConfigManager, blocks: list[Block], block_type_image: str):
        self.config = config
        self.blocks = blocks

    def execute(self) -> str:
        """Generate BlockLayoutStyles SQL"""
        values = self._format_styles_values()
        return self.config.get_sql_template("block_styles").format(styles_values=values)

    def _format_styles_values(self) -> str:
        """Format the values for BlockLayoutStyles SQL"""
        values = []
        default_color = self.config.get_default_color()
        color_settings_id = self.config.get_default_color_settings_id()

        for block in self.blocks:
            # Use block's border_radius field - always include border radius
            border_radius = block.border_radius or [0, 0, 0, 0]
            border_radius_str = f"ARRAY[{', '.join(map(str, border_radius))}]"

            # Format the SQL based on block type
            color_value = block.styles.get("color")
            color_value = ColorUtils.normalize_color(color_value) if color_value else None
            if not color_value or not color_value.startswith("#") or len(color_value) not in (4, 7):
                color_value = default_color
            if block.needs_null_styles:
                if block.is_background or block.is_figure:
                    # For background and figure blocks, use the block's color or default white
                    values.append(f"    ('{block.id}', null, null, null, null, {block.styles.get('zIndex', 1)}, '{color_value}', {block.opacity}, null, {border_radius_str}, '{color_settings_id}')")
                else:
                    # For other null style blocks, set color from styles or default
                    values.append(f"    ('{block.id}', null, null, null, null, {block.styles.get('zIndex', 1)}, '{color_value}', {block.opacity}, null, {border_radius_str}, '{color_settings_id}')")
            else:
                # For text-based blocks, set color from styles or default
                styles = block.styles
                values.append(f"    ('{block.id}', '{styles.get('textVertical')}', '{styles.get('textHorizontal')}', {styles.get('fontSize')}, {styles.get('weight')}, {styles.get('zIndex', 1)}, '{color_value}', {block.opacity}, '{styles.get('textTransform')}', {border_radius_str}, '{color_settings_id}')")
        return ",\n".join(values)


class BlockDimensionsCommand(SQLCommand):
    """Generates BlockLayoutDimensions SQL"""

    def __init__(self, config: ConfigManager, blocks: list[Block]):
        self.config = config
        self.blocks = blocks

    def execute(self) -> str:
        values = self._format_dimension_values()
        return self.config.get_sql_template("block_dimensions").format(dimension_values=values)

    def _format_dimension_values(self) -> str:
        values = []
        for block in self.blocks:
            dim = block.dimensions
            rotation = dim.get("rotation", 0)
            values.append(f"    ('{block.id}', {dim['x']}, {dim['y']}, {dim['w']}, {dim['h']}, {rotation})")
        return ",\n".join(values)


class FigureCommand(SQLCommand):
    """Generates Figure SQL"""

    def __init__(
        self,
        config: ConfigManager,
        id_generator,
        figure_blocks: list[dict[str, str]],
    ):
        self.config = config
        self.id_generator = id_generator
        self.figure_blocks = figure_blocks

    def execute(self) -> str:
        """Generate Figure SQL"""
        if not self.figure_blocks:
            return ""

        values = self._format_figure_values()
        return self.config.get_sql_template("figure").format(figure_values=values)

    def _format_figure_values(self) -> str:
        """Format the values for Figure SQL, extracting and storing the index from names like 'text_1'"""
        values = []
        for figure in self.figure_blocks:
            figure_id = generate_uuid()
            name = figure["name"]
            index = BlockNameUtils.extract_index(name, "figure")
            if index is not None:
                logger.info(f"Extracted index {index} from figure name {name}")
            name = re.sub(r"_\d+$", "", name)
            index_comment = f" -- index: {index}" if index is not None else ""
            values.append(f"    ('{figure_id}', '{figure['block_id']}', '{name}'){index_comment}")
        return ",\n".join(values)


class PrecompiledImageCommand(SQLCommand):
    """Generates PrecompiledImage SQL"""

    def __init__(
        self,
        config: ConfigManager,
        id_generator,
        precompiled_image_blocks: list[dict[str, str]],
    ):
        self.config = config
        self.id_generator = id_generator
        self.precompiled_image_blocks = precompiled_image_blocks

    def execute(self) -> str:
        """Generate PrecompiledImage SQL"""
        if not self.precompiled_image_blocks:
            return ""

        values = self._format_precompiled_image_values()
        return self.config.get_sql_template("precompiled_image").format(precompiled_image_values=values)

    def _format_precompiled_image_values(self) -> str:
        """Format the values for PrecompiledImage SQL"""
        values = []
        for precompiled_image in self.precompiled_image_blocks:
            precompiled_image_id = generate_uuid()
            color_value = f"'{precompiled_image['color']}'" if precompiled_image["color"] else "null"
            values.append(f"    ('{precompiled_image_id}', '{precompiled_image['block_layout_id']}', '{precompiled_image['url']}', {color_value})")
        return ",\n".join(values)


class SlideLayoutAdditionalInfoCommand(SQLCommand):
    """Generates SlideLayoutAdditionalInfo SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout, blocks: list | None = None):
        self.config = config
        self.slide_layout = slide_layout
        self.blocks = blocks or []

    def execute(self) -> str:
        """Generate SlideLayoutAdditionalInfo SQL"""
        additional_info = self.config.get_slide_layout_additional_info()
        # Use slide_type from input data instead of determining from config
        slide_type_camel = self.slide_layout.type

        # Count actual percentage blocks
        percentes_count = 0
        has_headers = additional_info["hasHeaders"]
        if self.blocks:
            for block in self.blocks:
                if block.type == "percentage":
                    percentes_count += 1
                if block.type in ("blockTitle", "percentage"):
                    has_headers = True

        infographics_type = None
        slide_name = self.slide_layout.name.lower()
        for pattern, config_data in config.SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE.items():
            if pattern in slide_name:
                infographics_type = config_data["infographicsType"]
                break

        infographics_type_sql = f"'{infographics_type}'" if infographics_type is not None else "null"

        return self.config.get_sql_template("slide_layout_additional_info").format(
            slide_layout_id=self.slide_layout.id,
            percentesCount=percentes_count,
            maxSymbolsInBlock=additional_info["maxSymbolsInBlock"],
            hasHeaders=str(has_headers).lower(),
            type=slide_type_camel,  # always camelCase
            icon_url=self.slide_layout.icon_url,
            infographics_type=infographics_type_sql,
        )


class SlideLayoutDimensionsCommand(SQLCommand):
    """Generates SlideLayoutDimensions SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout):
        self.config = config
        self.slide_layout = slide_layout

    def execute(self) -> str:
        """Generate SlideLayoutDimensions SQL"""
        dimensions = self.config.get_slide_layout_dimensions()

        return self.config.get_sql_template("slide_layout_dimensions").format(
            slide_layout_id=self.slide_layout.id,
            x=dimensions["x"],
            y=dimensions["y"],
            w=dimensions["w"],
            h=dimensions["h"],
        )


class SlideLayoutStylesCommand(SQLCommand):
    """Generates SlideLayoutStyles SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout):
        self.config = config
        self.slide_layout = slide_layout

    def execute(self) -> str:
        """Generate SlideLayoutStyles SQL"""
        return self.config.get_sql_template("slide_layout_styles").format(slide_layout_id=self.slide_layout.id)


class BlockLayoutIndexConfigCommand(SQLCommand):
    """Generates BlockLayoutIndexConfig SQL"""

    def __init__(
        self,
        config: ConfigManager,
        id_generator,
        blocks: list[Block],
        block_layout_config_mapping: list[dict],
        slide_config,
    ):
        self.config = config
        self.id_generator = id_generator
        self.blocks = blocks
        self.block_layout_config_mapping = block_layout_config_mapping
        self.block_id_to_index_config_id: dict[str, list[str]] = {}
        self.slide_config = slide_config

    def execute(self) -> str:
        """Generate BlockLayoutIndexConfig SQL"""
        values = self._format_block_layout_index_config_values()
        if not values:  # If no blocks have indices, return empty string
            return ""
        return self.config.get_sql_template("block_layout_index_config").format(block_layout_index_config_values=values)

    def _format_block_layout_index_config_values(self) -> str:
        values = []

        for block in self.blocks:

            if block.type in ["table", "infographik", "image"]:
                continue

            # Only process blocks that have an index
            if block.index is not None:
                self.block_id_to_index_config_id[block.id] = []

                # Calculate indexColorId as block_index
                index_color_id = block.index
                index_font_id = 0

                for slideConfigColor in self.slide_config[block.type]:
                    # Generate a UUID for the record
                    block_layout_index_config_id = generate_uuid()

                    block_style = self.slide_config[block.type][slideConfigColor][block.index]

                    # Поиск данных
                    for config_item in self.block_layout_config_mapping:
                        if slideConfigColor in config_item["background"]:
                            fonts = parse_fonts_from_config(config_item)
                            for index, font_family in enumerate(fonts):
                                if font_family == block_style.get("fontFamily", "arial"):
                                    index_font_id = index

                    self.block_id_to_index_config_id[block.id].append(block_layout_index_config_id)

                    values.append(f"    ('{block_layout_index_config_id}', '{block.id}', {index_color_id}, {index_font_id})")

        return ",\n".join(values)


class BlockLayoutLimitCommand(SQLCommand):
    """Generates BlockLayoutLimit SQL"""

    def __init__(self, config: ConfigManager, blocks: list[Block]):
        self.config = config
        self.blocks = blocks

    def execute(self) -> str:
        """Generate BlockLayoutLimit SQL"""
        values = self._format_block_layout_limit_values()
        if not values:  # If no blocks have indices, return ""
            return ""
        # Use the SQL template for BlockLayoutLimit
        sql_template = self.config.config.SQL_TEMPLATES.get("block_layout_limit")
        if not sql_template:
            raise KeyError("block_layout_limit SQL template not found in config.SQL_TEMPLATES")
        return sql_template.format(block_layout_limit_values=",\n".join(values))

    def _format_block_layout_limit_values(self) -> list:
        values = []
        min_words_config = getattr(self.config.config, "BLOCK_TYPE_MIN_WORDS", {})
        for block in self.blocks:
            min_words = min_words_config.get(block.type, 1)
            max_words = getattr(block, "words", 1)
            values.append(f"    ({min_words}, {max_words}, '{block.id}')")
        return values


class SlideLayoutIndexConfigCommand(SQLCommand):
    """Generates SlideLayoutIndexConfig SQL"""

    def __init__(
        self,
        config: ConfigManager,
        id_generator,
        slide_layout: SlideLayout,
        blocks: list[Block],
        block_id_to_index_config_id: dict | None = None,
        slide_config=None,
    ):
        self.config = config
        self.id_generator = id_generator
        self.slide_layout = slide_layout
        self.blocks = blocks
        self.block_id_to_index_config_id = block_id_to_index_config_id
        self.slide_config = slide_config

    def execute(self) -> str:
        """Generate SlideLayoutIndexConfig SQL"""
        values = self._format_slide_layout_index_config_values()
        if not values:  # If no blocks have indices, return empty string
            return ""
        return self.config.get_sql_template("slide_layout_index_config").format(slide_layout_index_config_values=values)

    def _format_slide_layout_index_config_values(self) -> str:
        """Format the values for SlideLayoutIndexConfig SQL"""
        values = []

        for block in self.blocks:

            if block.type in ["table", "infographik", "image"]:
                continue

            block_layout_index_config_id = (self.block_id_to_index_config_id or {}).get(block.id, block.id)

            if block.index is not None:
                slide_layout_id = self.slide_layout.id

                for index, config_item in enumerate(slide_layout_index_config_mapping):
                    slide_layout_index_config_id = generate_uuid()

                    presentation_palette_id = config_item.presentation_palette_id

                    block_layout_config_id = config_item.block_layout_config_id

                    config_number = 0

                    values.append(f"    ('{slide_layout_index_config_id}', '{presentation_palette_id}', {config_number}, '{slide_layout_id}', '{block_layout_index_config_id[index]}', '{block_layout_config_id}')")
        return ",\n".join(values)


# ================ Main SQL Generator ================


class SQLGenerator:
    """Main SQL Generator class"""

    def __init__(self, config_module, output_dir=None):
        self.config_manager = ConfigManager(config_module)
        self.id_generator = None  # We'll use uuid directly
        self.block_factory = BlockFactory(self.config_manager, self.id_generator)

        # Set up logging to file in the output directory
        if output_dir is None:
            output_dir = self.config_manager.get_output_config()["output_dir"]
        setup_slide_insertion_logger(output_dir)

    def _generate_color_font_sql(self, slide_layout, sql_input_data) -> tuple:
        """Generate SQL for color and font configurations from input data."""
        logger.info(f"Starting color/font SQL generation for slide: name={slide_layout.name}, number={slide_layout.number}")
        output_config = self.config_manager.get_output_config()
        base_output_dir = output_config["output_dir"]
        folder_name = self.config_manager.get_folder_for_slide_number(slide_layout.number)
        output_dir = os.path.join(base_output_dir, folder_name)

        matching_slides = self._find_slides_by_name_and_number(slide_layout, sql_input_data)
        color_sql_lines = []
        found_any = False
        for slide in matching_slides:
            candidate_config = slide.get("slideConfig", None)
            logger.debug(f"Found candidate slideConfig for slide_layout_number={slide.get('slide_layout_number')}, name='{slide.get('slide_layout_name')}': {candidate_config}")
            if candidate_config and len(candidate_config) > 0:
                found_any = True
                color_sql_lines.extend(self._create_color_font_sql_lines(candidate_config, slide_layout))
        if not found_any:
            logger.warning(f"No slideConfig found for slide {slide_layout.number} ('{slide_layout.name}') in sql_generator_input.json")
            return "", output_dir
        return "\n".join(color_sql_lines), output_dir

    def _find_slides_by_name_and_number(self, slide_layout, sql_input_data) -> list:
        """Find matching slides by name and number."""

        def normalize_name(name):
            return BlockNameUtils.normalize_name(name)

        slide_layout_name_norm = normalize_name(slide_layout.name)
        matching_slides = []
        for slide in sql_input_data:
            slide_num = str(slide.get("slide_layout_number"))
            slide_name_norm = normalize_name(slide.get("slide_layout_name"))
            logger.debug(f"Comparing input slide_layout_number={slide_num}, name='{slide_name_norm}' to current number={slide_layout.number}, name='{slide_layout_name_norm}'")
            if slide_num == str(slide_layout.number) and slide_name_norm == slide_layout_name_norm:
                matching_slides.append(slide)
        return matching_slides

    def _create_color_font_sql_lines(self, candidate_config, slide_layout) -> list:
        """Create SQL lines for color and font configurations."""
        color_sql_lines = []
        palette_colors = set()
        block_config_colors: dict[str, set[str]] = {}
        block_config_fonts: dict[str, set[str]] = {}
        for block_type, color_dict in candidate_config.items():
            for color_hex, obj_list in color_dict.items():
                color_hex_lc = ColorUtils.normalize_color(color_hex)

                # Find matching config in slide_layout_index_config_mapping
                matching_config = None
                for config_item in slide_layout_index_config_mapping:
                    if config_item.matched_background_color == color_hex_lc:
                        matching_config = config_item
                        break

                for obj in obj_list:
                    fill_color = obj.get("fill")
                    if fill_color:
                        fill_color = ColorUtils.normalize_color(fill_color)
                    font_raw = obj.get("fontFamily", "roboto")
                    font_norm = normalize_font_family(font_raw)

                    # Insert color into PresentationPalette
                    if color_hex_lc not in palette_colors:
                        if matching_config:
                            # Use the presentation_palette_id from the matching config
                            palette_id = matching_config.presentation_palette_id
                            logger.info(f"Using existing presentation_palette_id {palette_id} for color {color_hex_lc}")
                        else:
                            # Generate a new UUID if no matching config is found
                            palette_id = generate_uuid()
                            logger.warning(f"No matching config found for color {color_hex_lc}, generating new palette_id {palette_id}")

                        color_sql_lines.append(f"INSERT INTO \"PresentationPalette\" (id, presentationLayoutId, color) VALUES ('{palette_id}', '{slide_layout.presentation_layout_id}', '{color_hex_lc}') ON CONFLICT DO NOTHING;")  # nosec
                        palette_colors.add(color_hex_lc)

                    # Insert color into BlockLayoutConfig for this block type
                    if block_type not in block_config_colors:
                        block_config_colors[block_type] = set()

                    if color_hex_lc not in block_config_colors[block_type]:
                        if matching_config:
                            # Use the block_layout_config_id from the matching config
                            block_layout_config_id = matching_config.block_layout_config_id
                            logger.info(f"Using existing block_layout_config_id {block_layout_config_id} for color {color_hex_lc}")

                            # Add a comment to indicate the relationship
                            color_sql_lines.append(f"-- Using block_layout_config_id {block_layout_config_id} for color {color_hex_lc} in {block_type}")

                        if color_hex_lc is not None:
                            color_sql_lines.append(f"-- Ensure color {color_hex_lc} is in BlockLayoutConfig.{block_type}")
                            color_sql_lines.append(f"UPDATE \"BlockLayoutConfig\" SET {block_type} = array_append({block_type}, '{color_hex_lc}'::text) WHERE NOT ('{color_hex_lc}'::text = ANY({block_type}));")  # nosec
                            block_config_colors[block_type].add(color_hex_lc)

                    # Insert font into BlockLayoutConfig.font
                    if block_type not in block_config_fonts:
                        block_config_fonts[block_type] = set()

                    if font_norm not in block_config_fonts[block_type]:
                        color_sql_lines.append(f"-- Ensure font {font_norm} is in BlockLayoutConfig.font")
                        color_sql_lines.append(f'UPDATE "BlockLayoutConfig" SET font = array_append(font, \'{font_norm}\'::"FontFamilyType") WHERE NOT (\'{font_norm}\'::"FontFamilyType" = ANY(font));')  # nosec
                        block_config_fonts[block_type].add(font_norm)

                    color_sql_lines.append(f"-- Get color index: SELECT array_position({block_type}, '{color_hex_lc}'::text) FROM \"BlockLayoutConfig\" WHERE ...;")  # nosec
                    color_sql_lines.append(f'-- Get font index: SELECT array_position(font, \'{font_norm}\'::"FontFamilyType") FROM "BlockLayoutConfig" WHERE ...;')  # nosec

        return color_sql_lines

    def _get_default_blocks(self, slide_layout) -> list:
        """Return a list of default blocks (background, etc) based on config and slide_layout."""
        blocks = []
        # Add background if configured
        if self.config_manager.should_add_background():
            bg_config = self.config_manager.get_block_config("background")
            bg_block = self.block_factory.create_background_block(bg_config)
            blocks.append(bg_block)
            logger.info(f"\nAutomatically added background block with color {bg_config['color']}")
        return blocks

    def _set_slide_icon_url(self, slide_layout, blocks):
        """Set slide layout icon URL based on slide type and number."""
        logger.info(f"forGeneration value from input JSON: {slide_layout.for_generation} (not overridden by config)")
        logger.info(f"slide_type from input data: {slide_layout.type} (not overridden by config)")

        slide_layout.icon_url = build_slide_icon_url(slide_layout.type, slide_layout.name, slide_layout.number, self.config_manager.get_miniatures_base_path())

    def _build_complete_sql(
        self,
        slide_layout,
        blocks,
        figure_blocks,
        precompiled_image_blocks,
        slide_config=None,
    ):
        """Build complete SQL for slide layout and all blocks."""
        sql_queries = []
        current_time = datetime.now().strftime(self.config_manager.get_output_config()["timestamp_format"])

        # Load block layout config mapping
        block_layout_config_mapping = load_block_layout_config_mapping()

        # Create and execute all SQL commands
        # 1. BlockLayoutIndexConfigCommand first, to get mapping
        block_layout_index_config_cmd = BlockLayoutIndexConfigCommand(
            self.config_manager,
            self.id_generator,
            blocks,
            block_layout_config_mapping,
            slide_config,
        )

        block_layout_index_config_sql = block_layout_index_config_cmd.execute()
        block_id_to_index_config_id = block_layout_index_config_cmd.block_id_to_index_config_id

        commands: list[SQLCommand] = [
            SlideLayoutCommand(self.config_manager, slide_layout, current_time),
            BlockLayoutCommand(self.config_manager, blocks, slide_layout.id),
            BlockStylesCommand(self.config_manager, blocks, BlockTypes.IMAGE),
            BlockDimensionsCommand(self.config_manager, blocks),
            BlockLayoutLimitCommand(self.config_manager, blocks),
        ]

        if figure_blocks:
            commands.append(FigureCommand(self.config_manager, self.id_generator, figure_blocks))
        if precompiled_image_blocks:
            commands.append(PrecompiledImageCommand(self.config_manager, self.id_generator, precompiled_image_blocks))
        commands.extend(
            [
                SlideLayoutAdditionalInfoCommand(self.config_manager, slide_layout, blocks),
                SlideLayoutDimensionsCommand(self.config_manager, slide_layout),
                SlideLayoutStylesCommand(self.config_manager, slide_layout),
            ]
        )
        for command in commands:
            sql = command.execute()
            if sql:
                sql_queries.append(sql)
        # Join all SQL queries

        if block_layout_index_config_sql:
            sql_queries.append(block_layout_index_config_sql)

        slide_layout_index_config_cmd = SlideLayoutIndexConfigCommand(
            self.config_manager,
            self.id_generator,
            slide_layout,
            blocks,
            block_id_to_index_config_id,
            slide_config,
        )
        slide_layout_index_config_sql = slide_layout_index_config_cmd.execute()
        if slide_layout_index_config_sql:
            sql_queries.append(slide_layout_index_config_sql)
        return "\n\n".join(sql_queries)

    def _save_sql_file(self, sql, slide_layout):
        """Save SQL to file in appropriate directory structure."""
        output_config = self.config_manager.get_output_config()
        base_output_dir = output_config["output_dir"]
        # Get the folder name based on slide number
        folder_name = self.config_manager.get_folder_for_slide_number(slide_layout.number)
        # Create the full output directory path (slide_insertion subdir)
        output_dir = os.path.join(base_output_dir, "slide_insertion", folder_name)
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created directory: {output_dir}")
        # Generate filename with timestamp
        readable_time = datetime.now().strftime(output_config["timestamp_format"])
        file_name = output_config["filename_template"].format(slide_layout_name=slide_layout.name, timestamp=readable_time)
        output_file = os.path.join(output_dir, file_name)
        # Write SQL to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(sql)
        logger.info(f"\nSQL has been generated and saved to {output_file}")
        return output_file


def normalize_font_family(font_name: str) -> str:
    return DataCleaner.clean_font_name(font_name)


def create_sql_from_figma_export(json_path: str, output_dir: str | None = None) -> None:
    """
    Automatically generate SQL files from a Figma JSON export (as produced by figma.py's sql_generator_input.json),
    without any user interaction. Each slide in the JSON will be processed and SQL files will be written to the appropriate output directory.
    Args:
        json_path: Path to the Figma JSON export file
        output_dir: Output directory for generated SQL files (optional)
    Returns:
        None
    """
    try:
        generator = SQLGenerator(config, output_dir=output_dir)

        output_dir = output_dir or config.OUTPUT_CONFIG["output_dir"]
        # Remove output directory if it exists
        if os.path.exists(output_dir):
            logger.info(f"Preparing to remove existing output directory: {output_dir}")
            # Close all file handlers for loggers to avoid PermissionError
            loggers = [logging.getLogger(), logger]
            for log in loggers:
                handlers = log.handlers[:]
                for handler in handlers:
                    logger.info(f"Closing logger handler: {handler}")
                    handler.close()
                    log.removeHandler(handler)
            logger.info(f"All logger handlers closed. Removing directory: {output_dir}")
            shutil.rmtree(output_dir)
            logger.info(f"Removed output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
        setup_slide_insertion_logger(output_dir)
        logger.info(f"Starting auto SQL generation from {json_path} to {output_dir}")

        def strip_zindex(name: str) -> str:
            return DataCleaner.clean_slide_name(name)

        with open(json_path, encoding="utf-8") as f:
            slides = json.load(f)
        slide_count = 0
        error_count = 0
        for slide in slides:
            try:
                _generate_slide_sql(slide, generator, output_dir, strip_zindex)
                slide_count += 1
            except Exception as e:
                logger.error(f"Failed to process slide: {e}")
                print(f"Failed to process slide: {e}")
                error_count += 1
        logger.info(f"Auto SQL generation process completed. {slide_count} slides processed successfully, {error_count} failed. Output directory: {output_dir}")
        print(f"Auto SQL generation process completed. {slide_count} slides processed successfully, {error_count} failed. Output directory: {output_dir}")
    except Exception as e:
        logger.error(f"Auto SQL generation failed: {e}")
        print(f"Auto SQL generation failed: {e}")


def _generate_slide_sql(slide: dict, generator: "SQLGenerator", output_dir: str, strip_zindex) -> None:
    """Process a single slide from Figma JSON and generate SQL."""

    # Generate a UUID for the SlideLayout
    slide_layout_id = generate_uuid()
    # Strip z-index from slide layout name
    clean_slide_layout_name = strip_zindex(slide["slide_layout_name"])
    # Use slide_type from input data instead of determining from config
    slide_type = slide.get("slide_type", "classic")

    for_generation = slide.get("forGeneration", True)
    logger.info(f"Using forGeneration value from input JSON: {for_generation}")

    slide_layout = SlideLayout(
        id=slide_layout_id,
        name=clean_slide_layout_name,
        number=slide["slide_layout_number"],
        presentation_layout_id=slide["presentation_layout_id"],
        is_last=slide["is_last"],
        type_key=slide_type,
        type=slide_type,
        icon_url="",
        for_generation=for_generation,
        imagesCount=slide.get("imagesCount", 0),
    )
    logger.info(f"Created SlideLayout: {slide_layout}")
    miniatures_base_path = config.MINIATURES_BASE_PATH
    slide_layout.icon_url = build_slide_icon_url(slide_type, slide_layout.name, slide_layout.number, miniatures_base_path)
    # Build Block objects with generated UUIDs
    blocks, precompiled_images, figure_blocks, slide_config = _create_blocks_from_slide(slide, generator, strip_zindex)
    # Use SQLGenerator's internal methods to generate SQL and write to file
    sql = generator._build_complete_sql(slide_layout, blocks, figure_blocks, precompiled_images, slide_config)
    # Always use the folder from get_folder_for_slide_number for this slide number
    folder_name = generator.config_manager.get_folder_for_slide_number(slide_layout.number)
    # Write slide SQL to <output_dir>/<folder_name>/slide_insertion/
    slide_insertion_dir = os.path.join(output_dir, folder_name, "slide_insertion")
    os.makedirs(slide_insertion_dir, exist_ok=True)
    timestamp = datetime.now().strftime(config.OUTPUT_CONFIG["timestamp_format"])
    filename = f"{clean_slide_layout_name}_{timestamp}.sql"
    sql_file_path = os.path.join(slide_insertion_dir, filename)
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write(sql)
    logger.info(f"Generated SQL for slide {clean_slide_layout_name} at {sql_file_path}")
    logger.info(f"Calling color/font SQL generation for slide: name={slide_layout.name}, number={slide_layout.number}")


def _create_blocks_from_slide(slide: dict, generator: "SQLGenerator", strip_zindex) -> tuple:
    blocks = []
    block_id_map = {}
    precompiled_images = []
    figure_blocks = []

    # Extract font family mapping from slideConfig
    font_family_map = {}
    slide_config = slide.get("slideConfig", {})
    for block_type, color_configs in slide_config.items():
        for color_hex, font_configs in color_configs.items():
            if isinstance(font_configs, list) and len(font_configs) > 0:
                font_family = font_configs[0].get("fontFamily", "arial")
                font_family_map[(block_type, color_hex)] = font_family
            elif isinstance(font_configs, dict) and "fontFamily" in font_configs:
                font_family = font_configs.get("fontFamily", "arial")
                font_family_map[(block_type, color_hex)] = font_family

    logger.info(f"Extracted {len(font_family_map)} font family mappings from slideConfig")

    for block in slide["blocks"]:
        block_uuid = generate_uuid()
        block_id_map[block["id"]] = block_uuid
        styles = dict(block["styles"]) if block.get("styles") else {}
        color = None
        if "color" in styles and styles["color"]:
            color = styles["color"]
        elif "color" in block and block["color"]:
            color = block["color"]
        elif block.get("styles", {}).get("color"):
            color = block["styles"]["color"]
        normalized_color = ColorUtils.normalize_color(color) if color else None
        if normalized_color is not None:
            styles["color"] = normalized_color
        else:
            styles["color"] = None
        opacity = styles.get("opacity") or block.get("opacity", 1)
        original_block_name = block["name"]
        block_index = BlockNameUtils.extract_index(original_block_name, block["type"])
        clean_block_name = BlockNameUtils.normalize_name(original_block_name)
        words = block.get("words", 1)

        # Extract font family from slideConfig based on block type and color
        font_family = None
        block_type = block["type"]

        # Try to find font family by block type and color
        if normalized_color:
            font_family = font_family_map.get((block_type, normalized_color))

        # If not found, try to find by block type only
        if not font_family:
            for (
                config_block_type,
                config_color,
            ), config_font in font_family_map.items():
                if config_block_type == block_type:
                    font_family = config_font
                    break

        # Default fallback
        if not font_family:
            font_family = "arial"
            logger.warning(f"No font family found for block '{block_type}' (color: {normalized_color}), using default 'arial'")

        block_dict = dict(block)
        block_dict.update(
            {
                "id": block_uuid,
                "name": clean_block_name,
                "index": block_index,
                "styles": styles,
                "opacity": opacity,
                "words": words,
                "font_family": font_family,
            }
        )
        block_dict["figure_info"] = BlockFactory.extract_figure_info(block_dict, block_uuid, clean_block_name, normalized_color)
        block_dict["precompiled_image_info"] = BlockFactory.extract_precompiled_image_info(block_dict, block_uuid)
        block_obj = BlockFactory.create_block_from_dict(block_dict)
        blocks.append(block_obj)
        if block_obj.figure_info:
            figure_blocks.append(block_obj.figure_info)
        if block_obj.precompiled_image_info:
            precompiled_images.extend(block_obj.precompiled_image_info)
    return blocks, precompiled_images, figure_blocks, slide_config


def camel_to_snake(name):
    """Convert camelCase or PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def build_slide_icon_url(slide_type: str, slide_name: str, slide_number: int, miniatures_base_path: str) -> str:
    """Generate icon URL for slide layout."""
    skip_number_types = {config.SLIDE_NUMBER_TO_TYPE.get(n) for n in [1, 5, 8, 12, -1]}
    miniature_folder = camel_to_snake(slide_type)

    if slide_type in skip_number_types:
        return f"{miniatures_base_path}/{miniature_folder}/{slide_name}{config.MINIATURE_EXTENSION}"

    number_for_icon = config.SLIDE_NUMBER_TO_NUMBER.get(slide_number)
    if number_for_icon is not None:
        return f"{miniatures_base_path}/{miniature_folder}/{number_for_icon}_{slide_name}{config.MINIATURE_EXTENSION}"

    return f"{miniatures_base_path}/{miniature_folder}/{slide_name}{config.MINIATURE_EXTENSION}"


class BlockNameUtils:
    @staticmethod
    def extract_index(name: str, block_type: str | None = None) -> int | None:
        """
        Extracts an index from a block name using all known patterns.
        """
        return DataCleaner.extract_index(name, block_type)

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize a block or slide name using centralized cleaning rules.
        """
        return DataCleaner.clean_block_name(name)


def parse_fonts_from_config(config: dict) -> list[str]:
    """
    Parse fonts from a block layout config.

    Args:
        config: Dictionary containing block layout config data with a 'font' field

    Returns:
        List of font names extracted from the config
    """
    font_str = config.get("font", "{}")
    if not font_str or font_str == "{}":
        return []
    # Remove { and } and split by comma
    font_str = font_str.strip("{}")
    return [font.strip() for font in font_str.split(",") if font.strip()]


class FontIndexUtils:
    """Utility class for font index operations in block layout configurations."""

    @staticmethod
    def get_font_index(
        font_family: str,
        block_layout_config_id: str,
        block_layout_config_mapping: list[dict],
    ) -> int:
        """
        Get the font index for a given font family from the block layout config mapping.

        Args:
            font_family: The font family name to find
            block_layout_config_id: The ID of the block layout config to search in
            block_layout_config_mapping: List of block layout config dictionaries

        Returns:
            The index (0-based) of the font in the font array, or 0 if not found
        """
        if not font_family:
            return 0

        # Find the matching block layout config
        for config_item in block_layout_config_mapping:
            if config_item["id"] == block_layout_config_id:
                fonts = parse_fonts_from_config(config_item)
                normalized_font = normalize_font_family(font_family)

                # Find the index of the font in the array
                for i, font in enumerate(fonts):
                    if normalize_font_family(font) == normalized_font:
                        return i

                # Font not found, return 0
                logger.warning(f"Font '{font_family}' not found in config {block_layout_config_id}, using index 0")
                return 0

        # Config not found, return 0
        logger.warning(f"Block layout config {block_layout_config_id} not found, using font index 0")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQL Generator for Layout and Blocks (auto mode only)")
    parser.add_argument(
        "json_path",
        type=str,
        help="Path to sql_generator_input.json from figma.py for SQL generation",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for SQL files (optional, overrides config)",
    )
    args = parser.parse_args()

    create_sql_from_figma_export(args.json_path, args.output_dir)
