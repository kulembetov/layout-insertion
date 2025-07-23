import os
import time
import uuid
import logging
import re
import csv
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple, TypedDict, Optional
from dataclasses import dataclass, field
import json
import shutil
import argparse
import config


@dataclass
class SlideLayoutIndexConfig:
    id: str
    presentation_palette_id: str
    block_layout_config_id: str
    matched_background_color: str
    config_background_colors: List[str]


# Load slide layout index config mapping data
slide_layout_index_config_mapping = []
with open("slide_layout_index_config_mapping.csv", "r") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Convert the string representation of list to an actual list
        config_bg_colors = (
            eval(row["config_background_colors"])
            if row["config_background_colors"]
            else []
        )

        # Create an instance of SlideLayoutIndexConfig
        config_obj = SlideLayoutIndexConfig(
            id=row["id"],
            presentation_palette_id=row["presentationPaletteId"],
            block_layout_config_id=row["blockLayoutConfigId"],
            matched_background_color=row["matched_background_color"],
            config_background_colors=config_bg_colors,
        )
        slide_layout_index_config_mapping.append(config_obj)


# Helper to set up the logger file handler in any mode
def setup_slide_insertion_logger(output_dir):
    """Set up a file logger for slide insertion operations in the specified output directory."""
    logger = logging.getLogger(__name__)
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "slide_insertion.log")
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    # Remove any previous file handlers to avoid duplicate logs
    for h in logger.handlers[:]:
        if isinstance(h, logging.FileHandler):
            logger.removeHandler(h)
    logger.addHandler(file_handler)
    logger.propagate = False
    logger.info("Logger initialized and writing to %s", log_path)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================ Domain Models ================


class Dimensions(TypedDict):
    x: int
    y: int
    w: int
    h: int


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
    color: str = None
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
    color: str = None
    figure_info: dict = None
    precompiled_image_info: list = None
    border_radius: list = field(default_factory=lambda: [0, 0, 0, 0])
    name: str = ""
    index: int = (
        None  # Store the index extracted from the block name (e.g., "text_1" -> index=1)
    )
    opacity: int = 1  # Always default to 1 if not provided
    words: int = 1  # Add words field, default 1


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
        return self.config.Z_INDEX_DEFAULTS.get(
            block_type, self.config.Z_INDEX_DEFAULTS["default"]
        )

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

    def get_auto_block_config(self, key):
        """Get the auto block configuration for a given key."""
        return self.config.AUTO_BLOCKS.get(key, {})

    def should_add_background(self):
        """Return True if a background block should be added."""
        return self.config.AUTO_BLOCKS.get("add_background", False)

    def should_add_watermark(self):
        """Return True if a watermark block should be added."""
        return self.config.AUTO_BLOCKS.get("add_watermark", False)

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


class IdGenerator:
    """Generates unique IDs for entities."""

    @staticmethod
    def generate_uuid7() -> str:
        """Generate a UUID version 7 (time-ordered UUID)."""
        # Get current UNIX timestamp (milliseconds)
        unix_ts_ms = int(time.time() * 1000)

        # Convert to bytes (48 bits for timestamp)
        ts_bytes = unix_ts_ms.to_bytes(6, byteorder="big")

        # Generate 74 random bits (9 bytes with 2 bits used for version and variant)
        random_bytes = uuid.uuid4().bytes[6:]

        # Create the UUID combining timestamp and random bits
        # First 6 bytes from timestamp, rest from random
        uuid_bytes = ts_bytes + random_bytes

        # Set the version (7) in the 6th byte
        uuid_bytes = (
            uuid_bytes[0:6] + bytes([((uuid_bytes[6] & 0x0F) | 0x70)]) + uuid_bytes[7:]
        )

        # Set the variant (RFC 4122) in the 8th byte
        uuid_bytes = (
            uuid_bytes[0:8] + bytes([((uuid_bytes[8] & 0x3F) | 0x80)]) + uuid_bytes[9:]
        )

        return str(uuid.UUID(bytes=uuid_bytes))


class InputValidator:
    """Validates user input."""

    @staticmethod
    def validate_options(value: str, options: List[str]) -> bool:
        """Return True if value is in options."""
        return value in options

    @staticmethod
    def validate_integer(value: str) -> bool:
        """Return True if value is an integer."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_color(value: str) -> bool:
        """Return True if value is a valid hex color string."""
        # Add hash if not provided
        if not value.startswith("#"):
            value = f"#{value}"

        # Check if valid hex color after potentially adding the hash
        return len(value) in [4, 7]

    @staticmethod
    def prepare_color(value: str) -> str:
        """Prepare and normalize a color string to hex format."""
        # Add hash if not provided
        if not value.startswith("#"):
            value = f"#{value}"
        return value


class UserInputService:
    """Handles user interaction."""

    def __init__(self, validator: InputValidator):
        """Initialize UserInputService with an InputValidator."""
        self.validator = validator

    def get_input(
        self, prompt, default=None, options=None, is_integer=False, is_color=False
    ):
        """Prompt the user for input, with optional validation for options, integer, or color."""
        """Get validated input from user"""
        while True:
            if default is not None:
                full_prompt = f"{prompt} [default: {default}]: "
            else:
                full_prompt = f"{prompt}: "

            value = input(full_prompt)

            if not value and default is not None:
                return default

            if options and not self.validator.validate_options(value, options):
                logger.error(f"Input must be one of: {', '.join(options)}")
                continue

            if is_integer and value:
                if not self.validator.validate_integer(value):
                    logger.error("Please enter a valid integer")
                    continue
                return int(value)

            if is_color and value:
                if not self.validator.validate_color(value):
                    logger.error(
                        "Please enter a valid hex color (e.g., fff or #fff or ffffff or #ffffff)"
                    )
                    continue
                return self.validator.prepare_color(value)

            return value

    def show_color_options(self, colors: List[str]) -> None:
        """Display available color options to the user."""
        """Display available color options"""
        logger.info("Available default colors:")
        for i, color in enumerate(colors, 1):
            logger.info(f"  {i}. {color}")
        logger.info("You can also enter a custom hex color.")


# ================ Block Factory ================


class BlockFactory:
    """Factory for creating different types of blocks"""

    def __init__(self, config_manager: ConfigManager, id_generator: IdGenerator):
        self.config = config_manager
        self.id_generator = id_generator

    def create_block(self, block_type, index, user_input, total_blocks):
        """Create a block of the specified type"""

        if block_type == self.BLOCK_TYPE_WATERMARK:
            logger.info("Note: Watermark elements will be ignored as per requirements.")
            return None

        is_first_block = index == 0
        block_id = self.id_generator.generate_uuid7()

        needs_null_styles = self.config.is_null_style_type(block_type)
        needs_z_index = self.config.is_z_index_type(block_type)
        is_figure = block_type == self.BLOCK_TYPE_FIGURE
        is_background = block_type == self.BLOCK_TYPE_BACKGROUND
        is_image = block_type == self.BLOCK_TYPE_IMAGE

        # Initialize data
        color = None
        figure_info = None
        precompiled_image_info = None
        is_precompiled_image = False

        if needs_null_styles:
            logger.info(
                f"Note: For '{block_type}' type, style values will be set to NULL"
            )

        if is_figure:
            figure_name = user_input.get_input(
                f"Figure name for Block {index + 1}", "tallOutlineCrOne"
            )
            color = user_input.get_input(f"Figure color", "#ffffff", is_color=True)
            figure_info = {
                "block_id": block_id,
                "name": figure_name,
                "color": color,
            }

        if is_background:
            color = user_input.get_input(f"Background color", "#ffffff", is_color=True)

        if is_image:
            # Ask if this is a precompiled image
            is_precompiled = (
                user_input.get_input(
                    f"Is this a precompiled image?", "no", options=["yes", "no"]
                )
                == "yes"
            )

            if is_precompiled:
                is_precompiled_image = True
                filename = user_input.get_input(
                    f"Image filename (e.g., centerBarChart.png)", "centerBarChart.png"
                )

                if not filename:
                    logger.error("Filename is required for precompiled images")
                    return None

                # Build full URL
                base_url = self.config.get_precompiled_images_base_url()
                full_url = f"{base_url}/{filename}"

                # Show available colors and get user choice
                default_colors = self.config.get_precompiled_images_default_colors()
                user_input.show_color_options(default_colors)

                # Ask how many variants
                num_variants = user_input.get_input(
                    f"How many color/name variants for this precompiled image?",
                    1,
                    is_integer=True,
                )
                precompiled_image_info = []
                for v in range(num_variants):
                    logger.info(f"Variant {v+1} of {num_variants}:")
                    # Color for this variant
                    selected_color = user_input.get_input(
                        f"Color for variant {v+1} (enter number or custom hex color)",
                        "1",
                    )
                    # Handle color selection
                    if isinstance(selected_color, str) and selected_color.isdigit():
                        color_index = int(selected_color)
                        if 0 <= color_index < len(default_colors):
                            color_val = default_colors[color_index]
                        else:
                            logger.error(f"Invalid color number. Using default color.")
                            color_val = default_colors[0]
                    else:
                        # Try to validate as hex color
                        if user_input.validator.validate_color(selected_color):
                            color_val = user_input.validator.prepare_color(
                                selected_color
                            )
                        else:
                            logger.error("Invalid color format. Using default color.")
                            color_val = default_colors[0]
                    # Name for this variant (user provides the full filename without extension)
                    variant_name = user_input.get_input(
                        f"Name for variant {v+1} (filename without extension)"
                    )
                    # Use the provided name as the filename, keep the original extension
                    if "." in filename:
                        extension = filename.rsplit(".", 1)[1]
                        url_with_name = f"{base_url}/" + variant_name + f".{extension}"
                    else:
                        url_with_name = f"{base_url}/" + variant_name
                    precompiled_image_info.append(
                        {
                            "block_layout_id": block_id,  # This is the BlockLayout ID for the image block
                            "url": url_with_name,
                            "color": color_val,
                        }
                    )
                logger.info(
                    f"Precompiled image will be created with {num_variants} variants."
                )

        # Handle border radius for image blocks
        border_radius = [
            0,
            0,
            0,
            0,
        ]  # Default: top-left, top-right, bottom-right, bottom-left
        if block_type == self.BLOCK_TYPE_IMAGE:
            logger.info(
                f"Specify border radius for image (4 integers for top-left, top-right, bottom-right, bottom-left corners)"
            )
            top_left = user_input.get_input(
                f"Top-left corner radius", 0, is_integer=True
            )
            top_right = user_input.get_input(
                f"Top-right corner radius", 0, is_integer=True
            )
            bottom_right = user_input.get_input(
                f"Bottom-right corner radius", 0, is_integer=True
            )
            bottom_left = user_input.get_input(
                f"Bottom-left corner radius", 0, is_integer=True
            )
            border_radius = [top_left, top_right, bottom_right, bottom_left]

        # Get styles
        styles = self._get_styles(block_type, index, user_input, needs_null_styles)

        # Get dimensions
        dimensions = self._get_dimensions(block_type, index, user_input, is_first_block)

        # Opacity: always set to 1 if not provided
        opacity = 1.0

        return Block(
            id=block_id,
            type=block_type,
            needs_null_styles=needs_null_styles,
            needs_z_index=needs_z_index,
            is_figure=is_figure,
            is_background=is_background,
            is_precompiled_image=is_precompiled_image,
            color=color,
            styles=styles,
            dimensions=dimensions,
            figure_info=figure_info,
            precompiled_image_info=precompiled_image_info,
            border_radius=border_radius,
            opacity=opacity,
        )

    def create_watermark_block(self, dimension_config):
        """Create a watermark block with specified dimensions"""
        wm_id = self.id_generator.generate_uuid7()
        watermark_dimensions = dimension_config

        return Block(
            id=wm_id,
            type=self.BLOCK_TYPE_WATERMARK,
            needs_null_styles=True,
            needs_z_index=False,
            is_figure=False,
            is_background=False,
            is_precompiled_image=False,
            color=None,
            styles={
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": self.config.get_default_z_index("watermark"),
                "textTransform": None,
                "color": "#ffffff",
            },
            dimensions={
                "x": watermark_dimensions["x"],
                "y": watermark_dimensions["y"],
                "w": watermark_dimensions["w"],
                "h": watermark_dimensions["h"],
            },
        )

    def create_background_block(self, bg_config):
        """Create a background block with specified config"""
        bg_id = self.id_generator.generate_uuid7()
        bg_dims = bg_config["dimensions"]

        return Block(
            id=bg_id,
            type=self.BLOCK_TYPE_BACKGROUND,
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
                "zIndex": bg_config["z_index"],
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

    def _get_styles(self, block_type, index, user_input, needs_null_styles):
        """Get style information for a block"""
        if needs_null_styles:
            # For null-style blocks, only collect z-index
            default_z_index = self.config.get_default_z_index(block_type)
            z_index = user_input.get_input(
                f"Block {index + 1} Z-Index", default_z_index, is_integer=True
            )

            return {
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": z_index,
                "textTransform": None,
                "color": None,
            }
        else:
            default_styles = self.config.get_default_styles(block_type)

            text_vertical = user_input.get_input(
                f"Block {index + 1} Text Vertical Alignment",
                default_styles["text_vertical"],
                options=["top", "middle", "bottom"],
            )

            text_horizontal = user_input.get_input(
                f"Block {index + 1} Text Horizontal Alignment",
                default_styles["text_horizontal"],
                options=["left", "center", "right"],
            )

            font_size = user_input.get_input(
                f"Block {index + 1} Font Size",
                default_styles["font_size"],
                is_integer=True,
            )
            weight = user_input.get_input(
                f"Block {index + 1} Weight", default_styles["weight"], is_integer=True
            )
            text_transform = default_styles["text_transform"]

            # Get default z-index based on the block type
            default_z_index = self.config.get_default_z_index(block_type)
            z_index = user_input.get_input(
                f"Block {index + 1} Z-Index", default_z_index, is_integer=True
            )

            return {
                "textVertical": text_vertical,
                "textHorizontal": text_horizontal,
                "fontSize": font_size,
                "weight": weight,
                "zIndex": z_index,
                "textTransform": text_transform,
                "color": None,
            }

    def _get_dimensions(self, block_type, index, user_input, is_first_block):
        """Get dimensions for a block"""
        default_dims = self.config.get_default_dimensions(block_type, is_first_block)
        x = user_input.get_input(
            f"Block {index + 1} X Position", default_dims["x"], is_integer=True
        )
        y = user_input.get_input(
            f"Block {index + 1} Y Position", default_dims["y"], is_integer=True
        )
        w = user_input.get_input(
            f"Block {index + 1} Width", default_dims["w"], is_integer=True
        )
        h = user_input.get_input(
            f"Block {index + 1} Height", default_dims["h"], is_integer=True
        )

        return {"x": x, "y": y, "w": w, "h": h}

    @staticmethod
    def create_block_from_dict(block_dict: dict, extra: dict = None) -> Block:
        """
        Create a Block from a dict (Figma JSON or user input), handling all defaults and normalization.
        extra: optional dict for overrides (e.g., id, name, index, etc.)
        """
        data = dict(block_dict)  # shallow copy
        extra = extra or {}
        # Use provided or generate id
        block_id = extra.get("id") or data.get("id") or str(uuid.uuid4())
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
        border_radius = (
            data.get("border_radius") or data.get("corner_radius") or [0, 0, 0, 0]
        )
        # Opacity
        opacity = data.get("opacity", 1)
        # Words
        words = data.get("words", 1)
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
        if block_dict.get("type") != BlockTypes.IMAGE or not block_dict.get(
            "name", ""
        ).startswith("image precompiled"):
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


# ================ Color Utils ================


class ColorUtils:
    @staticmethod
    def normalize_color(color: str) -> str | None:
        """
        Normalize a color string to a standard hex format (#aabbcc, lowercase).
        Returns None if the color is invalid or empty.
        """
        if not color or not isinstance(color, str):
            return None
        color = color.strip().lower()
        # Handle hex colors
        if color.startswith("#"):
            color = color.lstrip("#")
        if re.fullmatch(r"[0-9a-f]{6}", color):
            return f"#{color}"
        if re.fullmatch(r"[0-9a-f]{3}", color):
            # Expand short hex to full
            color = "".join([c * 2 for c in color])
            return f"#{color}"
        return None


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
    LOGO = "logo"
    # Add more as needed


# ================ SQL Command Pattern ================


class SQLCommand(ABC):
    """Base class for SQL commands"""

    @abstractmethod
    def execute(self) -> str:
        """Execute the command and return SQL"""
        pass


class SlideLayoutCommand(SQLCommand):
    """Generates SlideLayout SQL"""

    def __init__(
        self, config: ConfigManager, slide_layout: SlideLayout, current_time: str
    ):
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
            is_last=str(self.slide_layout.is_last).lower(),
            for_generation=str(self.slide_layout.for_generation).lower(),
        )


class BlockLayoutCommand(SQLCommand):
    """Generates BlockLayout SQL"""

    def __init__(
        self, config: ConfigManager, blocks: List[Block], slide_layout_id: str
    ):
        self.config = config
        self.blocks = blocks
        self.slide_layout_id = slide_layout_id

    def execute(self) -> str:
        """Generate BlockLayout SQL"""
        values = self._format_block_layout_values()
        return self.config.get_sql_template("block_layout").format(
            block_layout_values=values
        )

    def _format_block_layout_values(self) -> str:
        """Format the values for BlockLayout SQL"""
        values = []
        for block in self.blocks:
            values.append(
                f"    ('{block.id}', '{self.slide_layout_id}', '{block.type}'::\"BlockLayoutType\")"
            )
        return ",\n".join(values)


class BlockStylesCommand(SQLCommand):
    """Generates BlockLayoutStyles SQL"""

    def __init__(
        self, config: ConfigManager, blocks: List[Block], block_type_image: str
    ):
        self.config = config
        self.blocks = blocks
        self.BLOCK_TYPE_IMAGE = block_type_image

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
            # Only set border radius for image blocks, use null for all others
            if block.type == self.BLOCK_TYPE_IMAGE and block.border_radius:
                border_radius_str = f"ARRAY[{', '.join(map(str, block.border_radius))}]"
            else:
                border_radius_str = "null"

            # Format the SQL based on block type
            color_value = block.styles.get("color")
            color_value = (
                ColorUtils.normalize_color(color_value) if color_value else None
            )
            if (
                not color_value
                or not color_value.startswith("#")
                or len(color_value) not in (4, 7)
            ):
                color_value = default_color
            if block.needs_null_styles:
                if block.is_background or block.is_figure:
                    # For background and figure blocks, use the block's color or default white
                    values.append(
                        f"    ('{block.id}', null, null, null, null, {block.styles.get('zIndex', 1)}, '{color_value}', {block.opacity}, null, {border_radius_str}, '{color_settings_id}')"
                    )
                else:
                    # For other null style blocks, set color from styles or default
                    values.append(
                        f"    ('{block.id}', null, null, null, null, {block.styles.get('zIndex', 1)}, '{color_value}', {block.opacity}, null, {border_radius_str}, '{color_settings_id}')"
                    )
            else:
                # For text-based blocks, set color from styles or default
                styles = block.styles
                values.append(
                    f"    ('{block.id}', '{styles.get('textVertical')}', '{styles.get('textHorizontal')}', {styles.get('fontSize')}, {styles.get('weight')}, {styles.get('zIndex', 1)}, '{color_value}', {block.opacity}, '{styles.get('textTransform')}', {border_radius_str}, '{color_settings_id}')"
                )
        return ",\n".join(values)


class BlockDimensionsCommand(SQLCommand):
    """Generates BlockLayoutDimensions SQL"""

    def __init__(self, config: ConfigManager, blocks: List[Block]):
        self.config = config
        self.blocks = blocks

    def execute(self) -> str:
        values = self._format_dimension_values()
        return self.config.get_sql_template("block_dimensions").format(
            dimension_values=values
        )

    def _format_dimension_values(self) -> str:
        values = []
        for block in self.blocks:
            dim = block.dimensions
            values.append(
                f"    ('{block.id}', {dim['x']}, {dim['y']}, {dim['w']}, {dim['h']})"
            )
        return ",\n".join(values)


class FigureCommand(SQLCommand):
    """Generates Figure SQL"""

    def __init__(
        self,
        config: ConfigManager,
        id_generator: IdGenerator,
        figure_blocks: List[Dict[str, str]],
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
            figure_id = self.id_generator.generate_uuid7()
            name = figure["name"]
            index = BlockNameUtils.extract_index(name, "figure")
            if index is not None:
                logger.info(f"Extracted index {index} from figure name {name}")
            name = re.sub(r"_\d+$", "", name)
            index_comment = f" -- index: {index}" if index is not None else ""
            values.append(
                f"    ('{figure_id}', '{figure['block_id']}', '{name}'){index_comment}"
            )
        return ",\n".join(values)


class PrecompiledImageCommand(SQLCommand):
    """Generates PrecompiledImage SQL"""

    def __init__(
        self,
        config: ConfigManager,
        id_generator: IdGenerator,
        precompiled_image_blocks: List[Dict[str, str]],
    ):
        self.config = config
        self.id_generator = id_generator
        self.precompiled_image_blocks = precompiled_image_blocks

    def execute(self) -> str:
        """Generate PrecompiledImage SQL"""
        if not self.precompiled_image_blocks:
            return ""

        values = self._format_precompiled_image_values()
        return self.config.get_sql_template("precompiled_image").format(
            precompiled_image_values=values
        )

    def _format_precompiled_image_values(self) -> str:
        """Format the values for PrecompiledImage SQL"""
        values = []
        for precompiled_image in self.precompiled_image_blocks:
            precompiled_image_id = self.id_generator.generate_uuid7()
            color_value = (
                f"'{precompiled_image['color']}'"
                if precompiled_image["color"]
                else "null"
            )
            values.append(
                f"    ('{precompiled_image_id}', '{precompiled_image['block_layout_id']}', '{precompiled_image['url']}', {color_value})"
            )
        return ",\n".join(values)


class SlideLayoutAdditionalInfoCommand(SQLCommand):
    """Generates SlideLayoutAdditionalInfo SQL"""

    def __init__(
        self, config: ConfigManager, slide_layout: SlideLayout, blocks: list = None
    ):
        self.config = config
        self.slide_layout = slide_layout
        self.blocks = blocks or []

    def execute(self) -> str:
        """Generate SlideLayoutAdditionalInfo SQL"""
        additional_info = self.config.get_slide_layout_additional_info()
        # Always use camelCase for type
        slide_type_camel = config.SLIDE_NUMBER_TO_TYPE.get(
            self.slide_layout.number, self.slide_layout.type
        )
        # Set hasHeaders True if any block is of type 'blockTitle' or 'percentage'
        has_headers = additional_info["hasHeaders"]
        if self.blocks:
            for block in self.blocks:
                if block.type in ("blockTitle", "percentage"):
                    has_headers = True
                    break

        infographics_type = None
        slide_name = self.slide_layout.name.lower()
        for pattern, config_data in config.SLIDE_LAYOUT_TO_INFOCRAPHICS_TYPE.items():
            if pattern in slide_name:
                infographics_type = config_data["infographicsType"]
                break

        infographics_type_sql = (
            f"'{infographics_type}'" if infographics_type is not None else "null"
        )

        return self.config.get_sql_template("slide_layout_additional_info").format(
            slide_layout_id=self.slide_layout.id,
            percentesCount=additional_info["percentesCount"],
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
        return self.config.get_sql_template("slide_layout_styles").format(
            slide_layout_id=self.slide_layout.id
        )


class BlockLayoutIndexConfigCommand(SQLCommand):
    """Generates BlockLayoutIndexConfig SQL"""

    def __init__(
        self, config: ConfigManager, id_generator: IdGenerator, blocks: List[Block]
    ):
        self.config = config
        self.id_generator = id_generator
        self.blocks = blocks
        self.block_id_to_index_config_id = (
            {}
        )  # mapping block.id -> block_layout_index_config_id

    def execute(self) -> str:
        """Generate BlockLayoutIndexConfig SQL"""
        values = self._format_block_layout_index_config_values()
        if not values:  # If no blocks have indices, return empty string
            return ""
        return self.config.get_sql_template("block_layout_index_config").format(
            block_layout_index_config_values=values
        )

    def _format_block_layout_index_config_values(self) -> str:
        """Format the values for BlockLayoutIndexConfig SQL"""
        values = []
        for block in self.blocks:
            # Only process blocks that have an index
            if block.index is not None:
                # Generate a UUID for the record
                block_layout_index_config_id = self.id_generator.generate_uuid7()
                # Calculate indexColorId and indexFontId as block_index
                index_color_id = block.index
                index_font_id = block.index
                # Save mapping for use in SlideLayoutIndexConfigCommand
                self.block_id_to_index_config_id[block.id] = (
                    block_layout_index_config_id
                )
                # Add the values to the list
                values.append(
                    f"    ('{block_layout_index_config_id}', '{block.id}', {index_color_id}, {index_font_id})"
                )
        return ",\n".join(values)


class BlockLayoutLimitCommand(SQLCommand):
    """Generates BlockLayoutLimit SQL"""

    def __init__(self, config: ConfigManager, blocks: List[Block]):
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
            raise KeyError(
                "block_layout_limit SQL template not found in config.SQL_TEMPLATES"
            )
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
        id_generator: IdGenerator,
        slide_layout: SlideLayout,
        blocks: List[Block],
        block_id_to_index_config_id: dict = None,
    ):
        self.config = config
        self.id_generator = id_generator
        self.slide_layout = slide_layout
        self.blocks = blocks
        self.block_id_to_index_config_id = block_id_to_index_config_id or {}

    def execute(self) -> str:
        """Generate SlideLayoutIndexConfig SQL"""
        values = self._format_slide_layout_index_config_values()
        if not values:  # If no blocks have indices, return empty string
            return ""
        return self.config.get_sql_template("slide_layout_index_config").format(
            slide_layout_index_config_values=values
        )

    def _format_slide_layout_index_config_values(self) -> str:
        """Format the values for SlideLayoutIndexConfig SQL"""
        values = []

        for block in self.blocks:
            # Only process blocks that have an index
            if block.index is not None:
                # Get the slide layout ID
                slide_layout_id = self.slide_layout.id

                # For each presentation palette in the mapping, create a SlideLayoutIndexConfig record
                for config in slide_layout_index_config_mapping:
                    presentation_palette_id = config.presentation_palette_id
                    # Use the block_layout_config_id from the CSV mapping
                    block_layout_config_id = config.block_layout_config_id

                    # Generate a UUID for the record
                    slide_layout_index_config_id = self.id_generator.generate_uuid7()
                    # Use the block index as the config number
                    config_number = 0
                    # Use the actual BlockLayoutIndexConfig ID from the current generation
                    block_layout_index_config_id = self.block_id_to_index_config_id.get(
                        block.id, block.id
                    )

                    # Add the values to the list
                    values.append(
                        f"    ('{slide_layout_index_config_id}', '{presentation_palette_id}', {config_number}, '{slide_layout_id}', '{block_layout_index_config_id}', '{block_layout_config_id}')"
                    )
        return ",\n".join(values)


# ================ Strategy Pattern for Slide Type Determination ================


class SlideTypeStrategy(ABC):
    """Base class for slide type determination strategies"""

    @abstractmethod
    def determine_slide_type(
        self, slide_layout: SlideLayout, blocks: List[Block]
    ) -> Tuple[str, str]:
        """Determine the slide type based on layout and blocks"""
        pass


class NumberBasedSlideTypeStrategy(SlideTypeStrategy):
    """Determines slide type based on slide number"""

    def __init__(self, config: ConfigManager):
        self.config = config

    def determine_slide_type(
        self, slide_layout: SlideLayout, blocks: List[Block]
    ) -> Tuple[str, str, bool]:
        """Determine the slide type based on slide number"""
        number = slide_layout.number

        # Determine if this slide should have forGeneration set to false
        for_generation = True
        # Set forGeneration to False for 5cols, 6cols, 7cols
        if number in [7, 10, 11]:
            for_generation = False
            logger.info(
                f"Setting forGeneration to false for slide number {number} (5cols, 6cols, 7cols)"
            )

        if slide_layout.is_last or number == -1:
            type_key = "last"
            logger.info(
                f"Slide type automatically set to 'last' because this is the last slide (number -1)"
            )
        elif number == 1:
            type_key = "title"
            logger.info(
                f"Slide type automatically set to 'title' because this is slide number 1"
            )
        elif number == 2:
            type_key = "few_text"
            logger.info(
                f"Slide type automatically set to 'few_text' because this is slide number 2"
            )
        elif number == 3:
            type_key = "optimal_text"
            logger.info(
                f"Slide type automatically set to 'optimal_text' because this is slide number 3"
            )
        elif number == 4:
            type_key = "many_text"
            logger.info(
                f"Slide type automatically set to 'many_text' because this is slide number 4"
            )
        elif number == 5:
            type_key = "infographics"
            logger.info(
                f"Slide type automatically set to 'infographics' because this is slide number 5"
            )
        elif number == 6:
            type_key = "extra_text"
            logger.info(
                f"Slide type automatically set to 'extra_text' because this is slide number 6"
            )
        elif number == 7:
            type_key = "other"
            logger.info(
                f"Slide type automatically set to 'other' because this is slide number 7"
            )
        elif number == 8:
            type_key = "table"
            logger.info(
                f"Slide type automatically set to 'table' because this is slide number 8"
            )
        elif number == 10:
            type_key = "other"
            logger.info(
                f"Slide type automatically set to 'other' because this is slide number 10"
            )
        elif number == 14:
            type_key = "chart"
            logger.info(
                f"Slide type automatically set to 'chart' because this is slide number 14"
            )
        else:
            # Default to classic for other slide numbers
            type_key = "classic"
            logger.info(
                f"Slide type automatically set to 'classic' (default for slide number {number})"
            )

        # If not for_generation, set type to 'other'
        if not for_generation:
            type_key = "other"
            logger.info(f"for_generation is False, so type is set to 'other'")

        slide_type = self.config.get_slide_layout_type(type_key)
        return type_key, slide_type, for_generation


class ContentBasedSlideTypeStrategy(SlideTypeStrategy):
    """Determines slide type based on content blocks"""

    def __init__(
        self,
        config: ConfigManager,
        block_type_table: str,
        block_type_infographik: str,
        block_type_chart: str,
    ):
        self.config = config
        self.BLOCK_TYPE_TABLE = block_type_table
        self.BLOCK_TYPE_INFOGRAPHIK = block_type_infographik
        self.BLOCK_TYPE_CHART = block_type_chart

    def determine_slide_type(
        self, slide_layout: SlideLayout, blocks: List[Block]
    ) -> Tuple[str, str, bool]:
        """Determine the slide type based on content blocks"""
        # If last slide, don't change the type
        if slide_layout.is_last:
            return (
                slide_layout.type_key,
                self.config.get_slide_layout_type(slide_layout.type_key),
                slide_layout.for_generation,
            )

        # Check for special block types
        has_table_block = any(block.type == self.BLOCK_TYPE_TABLE for block in blocks)
        has_infographik_block = any(
            block.type == self.BLOCK_TYPE_INFOGRAPHIK for block in blocks
        )
        has_chart_block = any(block.type == self.BLOCK_TYPE_CHART for block in blocks)

        old_type_key = slide_layout.type_key

        if has_table_block:
            type_key = "table"
            logger.info(
                f"Slide type changed from '{old_type_key}' to 'table' because this slide contains a table block"
            )
        elif has_chart_block:
            type_key = "chart"
            logger.info(
                f"Slide type changed from '{old_type_key}' to 'chart' because this slide contains a chart block"
            )
        elif has_infographik_block:
            type_key = "infographics"
            logger.info(
                f"Slide type changed from '{old_type_key}' to 'infographics' because this slide contains an infographik block"
            )
        else:
            # No need to change
            return (
                old_type_key,
                self.config.get_slide_layout_type(old_type_key),
                slide_layout.for_generation,
            )

        slide_type = self.config.get_slide_layout_type(type_key)
        return type_key, slide_type, slide_layout.for_generation


# ================ Main SQL Generator ================


class SQLGenerator:
    """Main SQL Generator class"""

    def __init__(self, config_module, output_dir=None):
        self.config_manager = ConfigManager(config_module)
        self.id_generator = IdGenerator()
        self.input_validator = InputValidator()
        self.user_input = UserInputService(self.input_validator)
        self.block_factory = BlockFactory(self.config_manager, self.id_generator)

        # Initialize strategies
        self.number_strategy = NumberBasedSlideTypeStrategy(self.config_manager)
        # Define canonical block type variables for clarity, robust to missing types
        block_types = self.config_manager.config.BLOCK_TYPES[
            "block_layout_type_options"
        ]

        def safe_block_type(name):
            if name in block_types:
                return block_types[block_types.index(name)]
            logger.warning(
                f"Block type '{name}' not found in config.BLOCK_TYPES['block_layout_type_options']"
            )
            return None

        self.BLOCK_TYPE_WATERMARK = safe_block_type("watermark")
        self.BLOCK_TYPE_FIGURE = safe_block_type("figure")
        self.BLOCK_TYPE_BACKGROUND = safe_block_type("background")
        self.BLOCK_TYPE_IMAGE = safe_block_type("image")
        self.BLOCK_TYPE_TABLE = safe_block_type("table")
        self.BLOCK_TYPE_INFOGRAPHIK = safe_block_type("infographik")
        self.BLOCK_TYPE_CHART = safe_block_type("chart")

        self.content_strategy = ContentBasedSlideTypeStrategy(
            self.config_manager,
            self.BLOCK_TYPE_TABLE,
            self.BLOCK_TYPE_INFOGRAPHIK,
            self.BLOCK_TYPE_CHART,
        )

        # Set up logging to file in the output directory
        if output_dir is None:
            output_dir = self.config_manager.get_output_config()["output_dir"]
        setup_slide_insertion_logger(output_dir)

    def run(self) -> None:
        """Run the SQL Generator"""
        while True:
            output_file = self.generate_sql()

            show_sql = (
                self.user_input.get_input(
                    "\nWould you like to see the generated SQL?",
                    "n",
                    options=["y", "n"],
                )
                == "y"
            )
            if show_sql:
                with open(output_file, "r") as f:
                    logger.info("\n" + f.read())

            again = (
                self.user_input.get_input(
                    "\nWould you like to generate another SQL file?",
                    "n",
                    options=["y", "n"],
                )
                == "y"
            )
            if not again:
                break

    def generate_sql(self) -> str:
        """Generate SQL based on user input"""
        logger.info("Starting SQL generation process.")
        # Load sql_generator_input.json for color/font extraction
        output_config = self.config_manager.get_output_config()
        base_output_dir = output_config["output_dir"]
        sql_input_path = os.path.join(base_output_dir, "sql_generator_input.json")
        sql_input_data = None
        if os.path.exists(sql_input_path):
            with open(sql_input_path, "r", encoding="utf-8") as f:
                sql_input_data = json.load(f)
        else:
            logger.warning(
                f"sql_generator_input.json not found at {sql_input_path}. Color/font SQL will be skipped."
            )
        # Collect slide layout information
        slide_layout = self._collect_slide_information()
        logger.info(
            f"Collected slide layout: name={slide_layout.name}, number={slide_layout.number}, type={slide_layout.type}, is_last={slide_layout.is_last}"
        )
        # Collect blocks
        blocks, figure_blocks, precompiled_image_blocks = self._collect_blocks(
            slide_layout
        )
        logger.info(
            f"Collected {len(blocks)} blocks for slide '{slide_layout.name}' (number {slide_layout.number})"
        )
        for block in blocks:
            logger.info(
                f"Block: type={block.type}, name={getattr(block, 'name', '')}, dimensions={block.dimensions}, styles={block.styles}"
            )
        # Update slide type based on content
        self._update_slide_type(slide_layout, blocks)
        logger.info(f"Final slide type: {slide_layout.type}")
        # Color extraction and SQL generation from sql_generator_input.json
        color_sql = ""
        color_folder = None
        if sql_input_data is not None:
            color_sql, color_folder = self._generate_color_sql_from_sql_input(
                slide_layout, sql_input_data
            )
        # Generate SQL
        sql = self._generate_sql_queries(
            slide_layout, blocks, figure_blocks, precompiled_image_blocks
        )
        # Write SQL to file
        output_file = self._write_sql_to_file(sql, slide_layout)
        if color_sql and color_folder:
            color_sql_file = os.path.join(
                color_folder, f"color_insertion_{slide_layout.name}.sql"
            )
            with open(color_sql_file, "w", encoding="utf-8") as f:
                f.write(color_sql)
            logger.info(f"Color SQL written to {color_sql_file}")
        logger.info(f"SQL written to {output_file}")
        logger.info(
            f"SQL file generated: {os.path.basename(output_file)} (saved at: {os.path.abspath(output_file)})"
        )
        logger.info("SQL generation process completed.")
        return output_file

    def _generate_color_sql_from_sql_input(self, slide_layout, sql_input_data) -> tuple:
        """Generate SQL for color and font insertions and index configs, using sql_generator_input.json."""
        logger.info(
            f"Starting color/font SQL generation for slide: name={slide_layout.name}, number={slide_layout.number}"
        )
        output_config = self.config_manager.get_output_config()
        base_output_dir = output_config["output_dir"]
        folder_name = self.config_manager.get_folder_for_slide_number(
            slide_layout.number
        )
        output_dir = os.path.join(base_output_dir, folder_name)

        matching_slides = self._find_matching_slides(slide_layout, sql_input_data)
        color_sql_lines = []
        found_any = False
        for slide in matching_slides:
            candidate_config = slide.get("slideConfig", None)
            logger.debug(
                f"Found candidate slideConfig for slide_layout_number={slide.get('slide_layout_number')}, name='{slide.get('slide_layout_name')}': {candidate_config}"
            )
            if candidate_config and len(candidate_config) > 0:
                found_any = True
                color_sql_lines.extend(
                    self._process_slide_color_font_config(
                        candidate_config, slide_layout
                    )
                )
        if not found_any:
            logger.warning(
                f"No slideConfig found for slide {slide_layout.number} ('{slide_layout.name}') in sql_generator_input.json"
            )
            return "", output_dir
        return "\n".join(color_sql_lines), output_dir

    def _find_matching_slides(self, slide_layout, sql_input_data) -> list:
        """Find all slides in sql_input_data matching this slide_layout (by number and normalized name)."""

        def normalize_name(name):
            return BlockNameUtils.normalize_name(name)

        slide_layout_name_norm = normalize_name(slide_layout.name)
        matching_slides = []
        for slide in sql_input_data:
            slide_num = str(slide.get("slide_layout_number"))
            slide_name_norm = normalize_name(slide.get("slide_layout_name"))
            logger.debug(
                f"Comparing input slide_layout_number={slide_num}, name='{slide_name_norm}' to current number={slide_layout.number}, name='{slide_layout_name_norm}'"
            )
            if (
                slide_num == str(slide_layout.number)
                and slide_name_norm == slide_layout_name_norm
            ):
                matching_slides.append(slide)
        return matching_slides

    def _process_slide_color_font_config(self, candidate_config, slide_layout) -> list:
        """Process a single slide's color/font config and generate SQL lines."""
        color_sql_lines = []
        palette_colors = set()
        block_config_colors = {}
        block_config_fonts = {}
        for block_type, color_dict in candidate_config.items():
            for color_hex, obj_list in color_dict.items():
                color_hex_lc = normalize_color(color_hex)

                # Find matching config in slide_layout_index_config_mapping
                matching_config = None
                for config in slide_layout_index_config_mapping:
                    if config.matched_background_color == color_hex_lc:
                        matching_config = config
                        break

                for obj in obj_list:
                    fill_color = obj.get("fill")
                    if fill_color:
                        fill_color = normalize_color(fill_color)
                    font_raw = obj.get("fontFamily", "roboto")
                    font_norm = normalize_font_family(font_raw)

                    # Insert color into PresentationPalette
                    if color_hex_lc not in palette_colors:
                        if matching_config:
                            # Use the presentation_palette_id from the matching config
                            palette_id = matching_config.presentation_palette_id
                            logger.info(
                                f"Using existing presentation_palette_id {palette_id} for color {color_hex_lc}"
                            )
                        else:
                            # Generate a new UUID if no matching config is found
                            palette_id = self.id_generator.generate_uuid7()
                            logger.warning(
                                f"No matching config found for color {color_hex_lc}, generating new palette_id {palette_id}"
                            )

                        color_sql_lines.append(
                            f"INSERT INTO \"PresentationPalette\" (id, presentationLayoutId, color) VALUES ('{palette_id}', '{slide_layout.presentation_layout_id}', '{color_hex_lc}') ON CONFLICT DO NOTHING;"
                        )
                        palette_colors.add(color_hex_lc)

                    # Insert color into BlockLayoutConfig for this block type
                    if block_type not in block_config_colors:
                        block_config_colors[block_type] = set()

                    if color_hex_lc not in block_config_colors[block_type]:
                        if matching_config:
                            # Use the block_layout_config_id from the matching config
                            block_layout_config_id = (
                                matching_config.block_layout_config_id
                            )
                            logger.info(
                                f"Using existing block_layout_config_id {block_layout_config_id} for color {color_hex_lc}"
                            )

                            # Add a comment to indicate the relationship
                            color_sql_lines.append(
                                f"-- Using block_layout_config_id {block_layout_config_id} for color {color_hex_lc} in {block_type}"
                            )

                        color_sql_lines.append(
                            f"-- Ensure color {color_hex_lc} is in BlockLayoutConfig.{block_type}"
                        )
                        color_sql_lines.append(
                            f"UPDATE \"BlockLayoutConfig\" SET {block_type} = array_append({block_type}, '{color_hex_lc}'::text) WHERE NOT ('{color_hex_lc}'::text = ANY({block_type}));"
                        )
                        block_config_colors[block_type].add(color_hex_lc)

                    # Insert font into BlockLayoutConfig.font
                    if block_type not in block_config_fonts:
                        block_config_fonts[block_type] = set()

                    if font_norm not in block_config_fonts[block_type]:
                        color_sql_lines.append(
                            f"-- Ensure font {font_norm} is in BlockLayoutConfig.font"
                        )
                        color_sql_lines.append(
                            f'UPDATE "BlockLayoutConfig" SET font = array_append(font, \'{font_norm}\'::"FontFamilyType") WHERE NOT (\'{font_norm}\'::"FontFamilyType" = ANY(font));'
                        )
                        block_config_fonts[block_type].add(font_norm)

                    color_sql_lines.append(
                        f"-- Get color index: SELECT array_position({block_type}, '{color_hex_lc}'::text) FROM \"BlockLayoutConfig\" WHERE ...;"
                    )
                    color_sql_lines.append(
                        f'-- Get font index: SELECT array_position(font, \'{font_norm}\'::"FontFamilyType") FROM "BlockLayoutConfig" WHERE ...;'
                    )

        return color_sql_lines

    def _collect_slide_information(self) -> SlideLayout:
        """Collect slide layout information interactively from the user (manual mode)."""
        slide_layout_name = self.user_input.get_input(
            "SlideLayout name",
            self.config_manager.get_default_value("slide_layout_name"),
        )

        # Ask if this is the last slide
        is_last_slide_option = self.user_input.get_input(
            "Is this the last slide?", "no", options=["yes", "no"]
        )
        is_last_slide = is_last_slide_option == "yes"

        slide_layout_number = (
            -1
            if is_last_slide
            else self.user_input.get_input(
                "SlideLayout number",
                self.config_manager.get_default_value("slide_layout_number"),
                is_integer=True,
            )
        )

        presentation_layout_id = self.user_input.get_input(
            "Presentation Layout ID",
            self.config_manager.get_default_value("presentation_layout_id"),
        )

        # Initialize with a default for_generation value (will be updated by the strategy)
        for_generation = True

        # Determine initial slide type based on number (camelCase)
        slide_type = config.SLIDE_NUMBER_TO_TYPE.get(slide_layout_number, "other")
        type_key = slide_type  # For now, type_key is the same as slide_type

        # Use SLIDE_NUMBER_TO_NUMBER for icon url, but skip number for certain types
        skip_number_types = set(
            [config.SLIDE_NUMBER_TO_TYPE.get(n) for n in [1, 5, 8, 12, -1]]
        )
        miniature_folder = camel_to_snake(slide_type)
        if slide_type in skip_number_types:
            icon_url = f"{self.config_manager.get_miniatures_base_path()}/{miniature_folder}/{slide_layout_name}{config.MINIATURE_EXTENSION}"
            logger.info(
                f"[MiniaturePath] Skipped number: icon_url={icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout_number})"
            )
        else:
            number_for_icon = config.SLIDE_NUMBER_TO_NUMBER.get(slide_layout_number)
            if number_for_icon is not None:
                icon_url = f"{self.config_manager.get_miniatures_base_path()}/{miniature_folder}/{number_for_icon}_{slide_layout_name}{config.MINIATURE_EXTENSION}"
                logger.info(
                    f"[MiniaturePath] With number: icon_url={icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout_number}, number_for_icon={number_for_icon})"
                )
            else:
                icon_url = f"{self.config_manager.get_miniatures_base_path()}/{miniature_folder}/{slide_layout_name}{config.MINIATURE_EXTENSION}"
                logger.info(
                    f"[MiniaturePath] Fallback: icon_url={icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout_number})"
                )

        # Generate ID for slide layout
        slide_layout_id = self.id_generator.generate_uuid7()

        return SlideLayout(
            id=slide_layout_id,
            name=slide_layout_name,
            number=slide_layout_number,
            presentation_layout_id=presentation_layout_id,
            is_last=is_last_slide,
            type_key=type_key,  # camelCase
            type=slide_type,  # camelCase
            icon_url=icon_url,
            for_generation=for_generation,
        )

    def _auto_blocks(self, slide_layout) -> list:
        """Return a list of automatically added blocks (background, watermark, etc) based on config and slide_layout."""
        blocks = []
        # Add background if configured
        if self.config_manager.should_add_background():
            bg_config = self.config_manager.get_auto_block_config("background")
            bg_block = self.block_factory.create_background_block(bg_config)
            blocks.append(bg_block)
            logger.info(
                f"\nAutomatically added background block with color {bg_config['color']}"
            )
        # Add watermark for last slide
        if slide_layout.is_last:
            logger.info("Last slide will automatically include a watermark block.")
            wm_config = self.config_manager.get_auto_block_config("last_slide")[
                "watermark1"
            ]
            watermark_block = self.block_factory.create_watermark_block(
                wm_config["dimensions"]
            )
            blocks.append(watermark_block)
            logger.info("\nAutomatically added watermark block for last slide")
        # Add watermark for regular slides if configured
        elif self.config_manager.should_add_watermark():
            logger.info("Regular slide will automatically include a watermark block.")
            wm_config = self.config_manager.get_auto_block_config("watermark")
            watermark_block = self.block_factory.create_watermark_block(
                wm_config["dimensions"]
            )
            blocks.append(watermark_block)
            logger.info("\nAutomatically added watermark block")
        # Add watermark if specified in config for the slide
        add_watermark = False
        if hasattr(self.config_manager.config, "WATERMARK_SLIDES"):
            add_watermark = (
                slide_layout.number in self.config_manager.config.WATERMARK_SLIDES
            )
        if add_watermark:
            if (
                slide_layout.number == -1
                and "last_slide" in self.config_manager.config.AUTO_BLOCKS
            ):
                watermark_dimensions = self.config_manager.config.AUTO_BLOCKS[
                    "last_slide"
                ]["watermark1"]["dimensions"]
            else:
                watermark_dimensions = self.config_manager.config.AUTO_BLOCKS[
                    "watermark"
                ]["dimensions"]
            watermark_block = Block(
                id=self.id_generator.generate_uuid7(),
                type=self.BLOCK_TYPE_WATERMARK,
                dimensions=watermark_dimensions,
                styles={
                    "textVertical": None,
                    "textHorizontal": None,
                    "fontSize": None,
                    "weight": None,
                    "zIndex": self.config_manager.config.Z_INDEX_DEFAULTS["watermark"],
                    "textTransform": None,
                    "color": "#ffffff",
                },
                needs_null_styles=True,
                needs_z_index=False,
                is_figure=False,
                is_background=False,
                is_precompiled_image=False,
                color=None,
                figure_info=None,
                precompiled_image_info=None,
                border_radius=[0, 0, 0, 0],
                name=self.BLOCK_TYPE_WATERMARK,
            )
            blocks.append(watermark_block)
        return blocks

    def _collect_blocks(self, slide_layout) -> tuple:
        """Collect all blocks for the given slide layout, including auto and user-defined blocks."""
        blocks = self._auto_blocks(slide_layout)
        user_blocks, figure_blocks, precompiled_image_blocks = (
            self._collect_user_defined_blocks()
        )
        blocks += user_blocks
        # Ensure a background block is present
        if not any(b.type == self.BLOCK_TYPE_BACKGROUND for b in blocks):
            bg_config = self.config_manager.config.AUTO_BLOCKS["background"]
            bg_styles = {
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": bg_config["z_index"],
                "textTransform": None,
                "color": "#ffffff",
            }
            bg_block = Block(
                id=self.id_generator.generate_uuid7(),
                type=self.BLOCK_TYPE_BACKGROUND,
                dimensions=bg_config["dimensions"],
                styles=bg_styles,
                needs_null_styles=True,
                needs_z_index=True,
                is_figure=False,
                is_background=True,
                is_precompiled_image=False,
                color=None,
                figure_info=None,
                precompiled_image_info=None,
                border_radius=[0, 0, 0, 0],
                name=self.BLOCK_TYPE_BACKGROUND,
            )
            blocks.insert(0, bg_block)
        return blocks, figure_blocks, precompiled_image_blocks

    def _collect_user_defined_blocks(self) -> tuple:
        """Prompt user for blocks and return (blocks, figure_blocks, precompiled_image_blocks)."""
        blocks = []
        figure_blocks = []
        precompiled_image_blocks = []
        num_blocks = self.user_input.get_input(
            "How many additional blocks do you want to create?",
            self.config_manager.get_default_value("num_blocks"),
            is_integer=True,
        )
        for i in range(num_blocks):
            logger.info(f"\nBlock {i + 1} information:")
            is_first_block = i == 0
            default_type = "slideTitle" if is_first_block else "text"
            block_type = self.user_input.get_input(
                f"Block {i + 1} Layout Type",
                default_type,
                options=self.config_manager.get_block_type_options(),
            )
            block = self.block_factory.create_block(
                block_type, i, self.user_input, num_blocks
            )
            if block:
                blocks.append(block)
                if block.figure_info:
                    figure_blocks.append(block.figure_info)
                if block.precompiled_image_info:
                    if isinstance(block.precompiled_image_info, list):
                        precompiled_image_blocks.extend(block.precompiled_image_info)
                    else:
                        precompiled_image_blocks.append(block.precompiled_image_info)
        return blocks, figure_blocks, precompiled_image_blocks

    def _update_slide_type(self, slide_layout, blocks):
        """Update slide layout type and icon_url based on content analysis."""
        # Use content-based strategy to determine type (camelCase)
        slide_type = config.SLIDE_NUMBER_TO_TYPE.get(slide_layout.number, "other")
        type_key = slide_type
        slide_layout.type_key = type_key  # camelCase
        slide_layout.type = slide_type  # camelCase
        skip_number_types = set(
            [config.SLIDE_NUMBER_TO_TYPE.get(n) for n in [1, 5, 8, 12, -1]]
        )
        miniature_folder = camel_to_snake(slide_type)
        if slide_type in skip_number_types:
            slide_layout.icon_url = f"{self.config_manager.get_miniatures_base_path()}/{miniature_folder}/{slide_layout.name}{config.MINIATURE_EXTENSION}"
            logger.info(
                f"[MiniaturePath] Skipped number: icon_url={slide_layout.icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout.number})"
            )
        else:
            number_for_icon = config.SLIDE_NUMBER_TO_NUMBER.get(
                slide_layout.number, slide_layout.number
            )
            slide_layout.icon_url = f"{self.config_manager.get_miniatures_base_path()}/{miniature_folder}/{number_for_icon}_{slide_layout.name}{config.MINIATURE_EXTENSION}"
            logger.info(
                f"[MiniaturePath] With number: icon_url={slide_layout.icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout.number}, number_for_icon={number_for_icon})"
            )

    def _generate_sql_queries(
        self, slide_layout, blocks, figure_blocks, precompiled_image_blocks
    ):
        """Generate SQL queries for all entities"""
        sql_queries = []

        # Create timestamp for SQL comment header
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql_queries.append(f"-- Generated on {current_time}\n")

        # Create and execute all SQL commands
        # 1. BlockLayoutIndexConfigCommand first, to get mapping
        block_layout_index_config_cmd = BlockLayoutIndexConfigCommand(
            self.config_manager, self.id_generator, blocks
        )
        block_layout_index_config_sql = block_layout_index_config_cmd.execute()
        block_id_to_index_config_id = (
            block_layout_index_config_cmd.block_id_to_index_config_id
        )

        commands = [
            # 1. SlideLayout
            SlideLayoutCommand(self.config_manager, slide_layout, current_time),
            # 2. BlockLayout
            BlockLayoutCommand(self.config_manager, blocks, slide_layout.id),
            # 3. BlockLayoutStyles
            BlockStylesCommand(self.config_manager, blocks, self.BLOCK_TYPE_IMAGE),
            # 4. BlockLayoutDimensions
            BlockDimensionsCommand(self.config_manager, blocks),
            # 5. BlockLayoutLimit
            BlockLayoutLimitCommand(self.config_manager, blocks),
        ]

        # 6. Figure records (optional)
        if figure_blocks:
            commands.append(
                FigureCommand(self.config_manager, self.id_generator, figure_blocks)
            )
        # 7. PrecompiledImage records (optional)
        if precompiled_image_blocks:
            commands.append(
                PrecompiledImageCommand(
                    self.config_manager, self.id_generator, precompiled_image_blocks
                )
            )
        # 8-10. Additional slide layout info
        commands.extend(
            [
                SlideLayoutAdditionalInfoCommand(
                    self.config_manager, slide_layout, blocks
                ),
                SlideLayoutDimensionsCommand(self.config_manager, slide_layout),
                SlideLayoutStylesCommand(self.config_manager, slide_layout),
            ]
        )
        # Execute all remaining commands and collect SQL
        for command in commands:
            sql = command.execute()
            if sql:  # Only add non-empty SQL
                sql_queries.append(sql)
        # Join all SQL queries

        if block_layout_index_config_sql:
            sql_queries.append(block_layout_index_config_sql)
        # 5. SlideLayoutIndexConfig (pass mapping)
        slide_layout_index_config_cmd = SlideLayoutIndexConfigCommand(
            self.config_manager,
            self.id_generator,
            slide_layout,
            blocks,
            block_id_to_index_config_id,
        )
        slide_layout_index_config_sql = slide_layout_index_config_cmd.execute()
        if slide_layout_index_config_sql:
            sql_queries.append(slide_layout_index_config_sql)

        return "\n\n".join(sql_queries)

    def _write_sql_to_file(self, sql, slide_layout):
        """Write SQL to output file, with folder based on slide number, in slide_insertion subdirectory."""
        output_config = self.config_manager.get_output_config()
        base_output_dir = output_config["output_dir"]
        # Get the folder name based on slide number
        folder_name = self.config_manager.get_folder_for_slide_number(
            slide_layout.number
        )
        # Create the full output directory path (slide_insertion subdir)
        output_dir = os.path.join(base_output_dir, "slide_insertion", folder_name)
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created directory: {output_dir}")
        # Generate filename with timestamp
        readable_time = datetime.now().strftime(output_config["timestamp_format"])
        file_name = output_config["filename_template"].format(
            slide_layout_name=slide_layout.name, timestamp=readable_time
        )
        output_file = os.path.join(output_dir, file_name)
        # Write SQL to file
        with open(output_file, "w") as f:
            f.write(sql)
        logger.info(f"\nSQL has been generated and saved to {output_file}")
        return output_file


def normalize_font_family(font_name: str) -> str:
    if not font_name:
        return "roboto"
    return re.sub(
        r"[^a-z0-9_]", "", font_name.strip().lower().replace(" ", "_").replace("-", "_")
    )


def normalize_color(color: str) -> str:
    return color.strip().lower()


def safe_slide_type(config, name):
    val = config.SLIDE_LAYOUT_TYPES.get(name)
    if val is None:
        logger.warning(f"Slide type '{name}' not found in config.SLIDE_LAYOUT_TYPES")
    return val


def auto_generate_sql_from_figma(
    json_path: str, output_dir: Optional[str] = None
) -> None:
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
            # Remove 'background_N' and ' z-index N' (case-insensitive, with or without leading/trailing spaces)
            name = re.sub(r"\s*background_\d+", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s*z-index\s*\d+\s*$", "", name, flags=re.IGNORECASE)
            # Clean up any extra spaces
            return name.strip()

        with open(json_path, "r", encoding="utf-8") as f:
            slides = json.load(f)
        slide_count = 0
        error_count = 0
        for slide in slides:
            try:
                _process_figma_slide(slide, generator, output_dir, strip_zindex)
                slide_count += 1
            except Exception as e:
                logger.error(f"Failed to process slide: {e}")
                print(f"Failed to process slide: {e}")
                error_count += 1
        logger.info(
            f"Auto SQL generation process completed. {slide_count} slides processed successfully, {error_count} failed. Output directory: {output_dir}"
        )
        print(
            f"Auto SQL generation process completed. {slide_count} slides processed successfully, {error_count} failed. Output directory: {output_dir}"
        )
    except Exception as e:
        logger.error(f"Auto SQL generation failed: {e}")
        print(f"Auto SQL generation failed: {e}")


def _process_figma_slide(
    slide: dict, generator: "SQLGenerator", output_dir: str, strip_zindex
) -> None:
    """Process a single slide from Figma JSON and generate SQL."""

    # Generate a UUID for the SlideLayout
    slide_layout_id = generator.id_generator.generate_uuid7()
    # Strip z-index from slide layout name
    clean_slide_layout_name = strip_zindex(slide["slide_layout_name"])
    # Always use camelCase for type
    slide_type = config.SLIDE_NUMBER_TO_TYPE.get(slide["slide_layout_number"], "other")
    slide_layout = SlideLayout(
        id=slide_layout_id,
        name=clean_slide_layout_name,
        number=slide["slide_layout_number"],
        presentation_layout_id=slide["presentation_layout_id"],
        is_last=slide["is_last"],
        type_key=slide_type,  # camelCase
        type=slide_type,  # camelCase
        icon_url="",  # Will be set below
        for_generation=True,  # Will be set by SQLGenerator
    )
    logger.info(f"Created SlideLayout: {slide_layout}")
    # Set icon_url using config and slide info (same as manual mode)
    miniatures_base_path = config.MINIATURES_BASE_PATH
    slide_layout_name = slide_layout.name
    slide_layout_number = slide_layout.number
    skip_number_types = set(
        [config.SLIDE_NUMBER_TO_TYPE.get(n) for n in [1, 5, 8, 12, -1]]
    )
    miniature_folder = camel_to_snake(slide_type)
    if slide_type in skip_number_types:
        slide_layout.icon_url = f"{miniatures_base_path}/{miniature_folder}/{slide_layout.name}{config.MINIATURE_EXTENSION}"
        logger.info(
            f"[MiniaturePath] Skipped number: icon_url={slide_layout.icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout_number})"
        )
    else:
        number_for_icon = config.SLIDE_NUMBER_TO_NUMBER.get(slide_layout_number)
        if number_for_icon is not None:
            slide_layout.icon_url = f"{miniatures_base_path}/{miniature_folder}/{number_for_icon}_{slide_layout_name}{config.MINIATURE_EXTENSION}"
            logger.info(
                f"[MiniaturePath] With number: icon_url={slide_layout.icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout_number}, number_for_icon={number_for_icon})"
            )
        else:
            slide_layout.icon_url = f"{miniatures_base_path}/{miniature_folder}/{slide_layout_name}{config.MINIATURE_EXTENSION}"
            logger.info(
                f"[MiniaturePath] Fallback: icon_url={slide_layout.icon_url} (slide_type={slide_type}, slide_layout_number={slide_layout_number})"
            )
    # Build Block objects with generated UUIDs
    blocks, precompiled_images, figure_blocks = _process_figma_blocks(
        slide, generator, strip_zindex
    )
    _ensure_background_and_watermark_blocks(slide_layout, blocks, generator)
    # Use SQLGenerator's internal methods to generate SQL and write to file
    sql = generator._generate_sql_queries(
        slide_layout, blocks, figure_blocks, precompiled_images
    )
    # Always use the folder from get_folder_for_slide_number for this slide number
    folder_name = generator.config_manager.get_folder_for_slide_number(
        slide_layout.number
    )
    # Write slide SQL to <output_dir>/<folder_name>/slide_insertion/
    slide_insertion_dir = os.path.join(output_dir, folder_name, "slide_insertion")
    os.makedirs(slide_insertion_dir, exist_ok=True)
    timestamp = datetime.now().strftime(config.OUTPUT_CONFIG["timestamp_format"])
    filename = f"{clean_slide_layout_name}_{timestamp}.sql"
    sql_file_path = os.path.join(slide_insertion_dir, filename)
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write(sql)
    logger.info(f"Generated SQL for slide {clean_slide_layout_name} at {sql_file_path}")
    logger.info(
        f"Calling color/font SQL generation for slide: name={slide_layout.name}, number={slide_layout.number}"
    )


def _process_figma_blocks(
    slide: dict, generator: "SQLGenerator", strip_zindex
) -> tuple:
    blocks = []
    block_id_map = {}
    precompiled_images = []
    figure_blocks = []
    for block in slide["blocks"]:
        block_uuid = generator.id_generator.generate_uuid7()
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
        opacity = block.get("opacity", 1)
        original_block_name = block["name"]
        block_index = BlockNameUtils.extract_index(original_block_name, block["type"])
        clean_block_name = BlockNameUtils.normalize_name(original_block_name)
        words = block.get("words", 1)
        block_dict = dict(block)
        block_dict.update(
            {
                "id": block_uuid,
                "name": clean_block_name,
                "index": block_index,
                "styles": styles,
                "opacity": opacity,
                "words": words,
            }
        )
        block_dict["figure_info"] = BlockFactory.extract_figure_info(
            block_dict, block_uuid, clean_block_name, normalized_color
        )
        block_dict["precompiled_image_info"] = (
            BlockFactory.extract_precompiled_image_info(block_dict, block_uuid)
        )
        block_obj = BlockFactory.create_block_from_dict(block_dict)
        blocks.append(block_obj)
        if block_obj.figure_info:
            figure_blocks.append(block_obj.figure_info)
        if block_obj.precompiled_image_info:
            precompiled_images.extend(block_obj.precompiled_image_info)
    return blocks, precompiled_images, figure_blocks


def _ensure_background_and_watermark_blocks(
    slide_layout, blocks: list, generator: "SQLGenerator"
) -> None:
    """Ensure a background block and watermark block are present if needed."""
    has_background = any(b.type == generator.BLOCK_TYPE_BACKGROUND for b in blocks)
    logger.info(f"Background block present from Figma: {has_background}")
    if has_background:
        logger.info(
            "Using background block(s) extracted from Figma with original colors"
        )
    else:
        logger.info(
            "No background block found in Figma extraction - slide will use default background handling"
        )
    # Add watermark block if specified in config
    add_watermark = False
    if hasattr(config, "WATERMARK_SLIDES"):
        add_watermark = slide_layout.number in config.WATERMARK_SLIDES
    if add_watermark:
        if slide_layout.number == -1 and "last_slide" in config.AUTO_BLOCKS:
            watermark_dimensions = config.AUTO_BLOCKS["last_slide"]["watermark1"][
                "dimensions"
            ]
        else:
            watermark_dimensions = config.AUTO_BLOCKS["watermark"]["dimensions"]
        watermark_block = Block(
            id=generator.id_generator.generate_uuid7(),
            type=generator.BLOCK_TYPE_WATERMARK,
            dimensions=watermark_dimensions,
            styles={
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": config.Z_INDEX_DEFAULTS["watermark"],
                "textTransform": None,
                "color": "#ffffff",
            },
            needs_null_styles=True,
            needs_z_index=False,
            is_figure=False,
            is_background=False,
            is_precompiled_image=False,
            color=None,
            figure_info=None,
            precompiled_image_info=None,
            border_radius=[0, 0, 0, 0],
            name=generator.BLOCK_TYPE_WATERMARK,
        )
        blocks.append(watermark_block)


def camel_to_snake(name):
    """Convert camelCase or PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class BlockNameUtils:
    @staticmethod
    def extract_index(name: str, block_type: str = None) -> int | None:
        """
        Extracts an index from a block name using all known patterns.
        Handles:
        - 'background_N', 'percentage_N', 'text_N', etc.
        - 'figure (name_N)' or 'figure (something_N)'
        - 'image precompiled name_N'
        - General '_N' at the end
        Returns the index as int if found, else None.
        """
        if not name:
            return None
        # Figure with parentheses: figure (name_N)
        paren_match = re.search(r"\(([^)]+)\)", name)
        if paren_match:
            inner = paren_match.group(1)
            idx_match = re.search(r"_(\d+)", inner)
            if idx_match:
                return int(idx_match.group(1))
        # background_N, percentage_N, etc.
        if block_type:
            pattern = rf"{block_type}[_\s-]*(\d+)"  # e.g., background_2 or background 2
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

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize a block or slide name by:
        - Removing 'background_N', 'z-index N', and similar suffixes
        - Stripping leading/trailing whitespace
        - Removing extra spaces
        - (NO lowercasing)
        """
        if not name:
            return ""
        # Remove 'background_N' (case-insensitive)
        name = re.sub(r"\s*background_\d+", "", name, flags=re.IGNORECASE)
        # Remove 'z-index N' (case-insensitive)
        name = re.sub(r"\s*z-index\s*\d+\s*$", "", name, flags=re.IGNORECASE)
        # Remove trailing underscores and digits (e.g., _1, _2)
        name = re.sub(r"_\d+$", "", name)
        # Remove extra spaces
        return name.strip()


def main():
    """Main entry point for interactive mode"""
    output_dir = config.OUTPUT_CONFIG["output_dir"]
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
    generator = SQLGenerator(config)
    generator.run()


# Extend CLI to support --auto-from-figma
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SQL Generator for Layout and Blocks (interactive or auto mode)"
    )
    parser.add_argument(
        "--auto-from-figma",
        type=str,
        help="Path to sql_generator_input.json from figma.py for non-interactive SQL generation",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for SQL files (optional, overrides config)",
    )
    args, unknown = parser.parse_known_args()

    if args.auto_from_figma:
        auto_generate_sql_from_figma(args.auto_from_figma, args.output_dir)
    else:
        main_output_dir = args.output_dir if args.output_dir else None
        generator = SQLGenerator(config, output_dir=main_output_dir)
        generator.run()
