"""
SQL Generator for Layout and Blocks
Refactored version using modern design patterns
Generates SQL insert statements for slide layouts and blocks

Usage:
    1. Import this module
    2. Create an instance of SQLGenerator with your config module
    3. Call the run() method to start the interactive generator

Example:
    import config
    from sql_generator import SQLGenerator

    generator = SQLGenerator(config)
    generator.run()
"""

import os
import time
import uuid
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Tuple, TypedDict, Literal
from dataclasses import dataclass, field
import re

# Helper to set up the logger file handler in any mode
def setup_slide_insertion_logger(output_dir):
    logger = logging.getLogger(__name__)
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, 'slide_insertion.log')
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # Remove any previous file handlers to avoid duplicate logs
    for h in logger.handlers[:]:
        if isinstance(h, logging.FileHandler):
            logger.removeHandler(h)
    logger.addHandler(file_handler)
    logger.propagate = False
    logger.info('Logger initialized and writing to %s', log_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    """Manages configuration for the SQL generator"""

    def __init__(self, config_module):
        self.config = config_module

    def get_default_value(self, key):
        return self.config.DEFAULT_VALUES.get(key)

    def get_slide_layout_type(self, key):
        return self.config.SLIDE_LAYOUT_TYPES.get(key)

    def get_block_type_options(self):
        return self.config.BLOCK_TYPES['block_layout_type_options']

    def is_null_style_type(self, block_type):
        return block_type in self.config.BLOCK_TYPES['null_style_types']

    def is_z_index_type(self, block_type):
        return block_type in self.config.BLOCK_TYPES['z_index_types']

    def get_default_z_index(self, block_type):
        return self.config.Z_INDEX_DEFAULTS.get(block_type,
               self.config.Z_INDEX_DEFAULTS['default'])

    def get_default_dimensions(self, block_type, is_first_block=False):
        if block_type in self.config.DEFAULT_DIMENSIONS:
            return self.config.DEFAULT_DIMENSIONS[block_type]
        return self.config.DEFAULT_DIMENSIONS['default']

    def get_default_styles(self, block_type):
        if block_type in self.config.DEFAULT_STYLES:
            return self.config.DEFAULT_STYLES[block_type]
        return self.config.DEFAULT_STYLES['default']

    def get_auto_block_config(self, key):
        return self.config.AUTO_BLOCKS.get(key, {})

    def should_add_background(self):
        return self.config.AUTO_BLOCKS.get("add_background", False)

    def should_add_watermark(self):
        return self.config.AUTO_BLOCKS.get("add_watermark", False)

    def get_sql_template(self, key):
        return self.config.SQL_TEMPLATES.get(key, "")

    def get_slide_layout_additional_info(self):
        return self.config.SLIDE_LAYOUT_ADDITIONAL_INFO

    def get_slide_layout_dimensions(self):
        return self.config.SLIDE_LAYOUT_DIMENSIONS

    def get_output_config(self):
        return self.config.OUTPUT_CONFIG

    def get_default_color(self):
        return self.config.DEFAULT_COLOR

    def get_default_color_settings_id(self):
        return self.config.DEFAULT_COLOR_SETTINGS_ID

    def get_miniatures_base_path(self):
        return self.config.MINIATURES_BASE_PATH

    def get_folder_for_slide_number(self, slide_number):
        # Get the output folder name based on slide number
        return self.config.SLIDE_NUMBER_TO_FOLDER.get(slide_number, "other")

    def get_precompiled_images_base_url(self):
        # Get the base URL for precompiled images
        return self.config.PRECOMPILED_IMAGES.get("base_url", "")

    def get_precompiled_images_default_colors(self):
        # Get the list of default colors for precompiled images
        return self.config.PRECOMPILED_IMAGES.get("default_colors", ["#ffffff"])


# ================ Utility Services ================

class IdGenerator:
    """Generates unique IDs for entities"""

    @staticmethod
    def generate_uuid7() -> str:
        """
        Generate a UUID version 7 (time-ordered UUID)
        Implementation based on the draft RFC for UUID v7 - time-ordered
        """
        # Get current UNIX timestamp (milliseconds)
        unix_ts_ms = int(time.time() * 1000)

        # Convert to bytes (48 bits for timestamp)
        ts_bytes = unix_ts_ms.to_bytes(6, byteorder='big')

        # Generate 74 random bits (9 bytes with 2 bits used for version and variant)
        random_bytes = uuid.uuid4().bytes[6:]

        # Create the UUID combining timestamp and random bits
        # First 6 bytes from timestamp, rest from random
        uuid_bytes = ts_bytes + random_bytes

        # Set the version (7) in the 6th byte
        uuid_bytes = (
            uuid_bytes[0:6] +
            bytes([((uuid_bytes[6] & 0x0F) | 0x70)]) +
            uuid_bytes[7:]
        )

        # Set the variant (RFC 4122) in the 8th byte
        uuid_bytes = (
            uuid_bytes[0:8] +
            bytes([((uuid_bytes[8] & 0x3F) | 0x80)]) +
            uuid_bytes[9:]
        )

        return str(uuid.UUID(bytes=uuid_bytes))


class InputValidator:
    """Validates user input"""

    @staticmethod
    def validate_options(value: str, options: List[str]) -> bool:
        return value in options

    @staticmethod
    def validate_integer(value: str) -> bool:
        try:
            int(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_color(value: str) -> bool:
        # Add hash if not provided
        if not value.startswith('#'):
            value = f"#{value}"

        # Check if valid hex color after potentially adding the hash
        return len(value) in [4, 7]

    @staticmethod
    def prepare_color(value: str) -> str:
        # Add hash if not provided
        if not value.startswith('#'):
            value = f"#{value}"
        return value


class UserInputService:
    """Handles user interaction"""

    def __init__(self, validator: InputValidator):
        self.validator = validator

    def get_input(self, prompt, default=None, options=None, is_integer=False, is_color=False):
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
                    logger.error("Please enter a valid hex color (e.g., fff or #fff or ffffff or #ffffff)")
                    continue
                return self.validator.prepare_color(value)

            return value

    def show_color_options(self, colors: List[str]) -> None:
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

    def create_block(self,
                    block_type,
                    index,
                    user_input,
                    total_blocks):
        """Create a block of the specified type"""

        if block_type == 'watermark':
            logger.info("Note: Watermark elements will be ignored as per requirements.")
            return None

        is_first_block = (index == 0)
        block_id = self.id_generator.generate_uuid7()

        needs_null_styles = self.config.is_null_style_type(block_type)
        needs_z_index = self.config.is_z_index_type(block_type)
        is_figure = block_type == 'figure'
        is_background = block_type == 'background'
        is_image = block_type == 'image'

        # Initialize data
        color = None
        figure_info = None
        precompiled_image_info = None
        is_precompiled_image = False

        if needs_null_styles:
            logger.info(f"Note: For '{block_type}' type, style values will be set to NULL")

        if is_figure:
            figure_name = user_input.get_input(f"Figure name for Block {index + 1}", "tallOutlineCrOne")
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
            is_precompiled = user_input.get_input(
                f"Is this a precompiled image?", 
                "no", 
                options=["yes", "no"]
            ) == "yes"
            
            if is_precompiled:
                is_precompiled_image = True
                filename = user_input.get_input(f"Image filename (e.g., centerBarChart.png)", 'centerBarChart.png')
                
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
                    is_integer=True
                )
                precompiled_image_info = []
                for v in range(num_variants):
                    logger.info(f"Variant {v+1} of {num_variants}:")
                    # Color for this variant
                    selected_color = user_input.get_input(
                        f"Color for variant {v+1} (enter number or custom hex color)",
                        "1"
                    )
                    # Handle color selection
                    if isinstance(selected_color, str) and selected_color.isdigit():
                        color_index = int(selected_color) - 1
                        if 0 <= color_index < len(default_colors):
                            color_val = default_colors[color_index]
                        else:
                            logger.error(f"Invalid color number. Using default color.")
                            color_val = default_colors[0]
                    else:
                        # Try to validate as hex color
                        if user_input.validator.validate_color(selected_color):
                            color_val = user_input.validator.prepare_color(selected_color)
                        else:
                            logger.error("Invalid color format. Using default color.")
                            color_val = default_colors[0]
                    # Name for this variant (user provides the full filename without extension)
                    variant_name = user_input.get_input(
                        f"Name for variant {v+1} (filename without extension)"
                    )
                    # Use the provided name as the filename, keep the original extension
                    if '.' in filename:
                        extension = filename.rsplit('.', 1)[1]
                        url_with_name = f"{base_url}/" + variant_name + f".{extension}"
                    else:
                        url_with_name = f"{base_url}/" + variant_name
                    precompiled_image_info.append({
                        "block_layout_id": block_id,  # This is the BlockLayout ID for the image block
                        "url": url_with_name,
                        "color": color_val
                    })
                logger.info(f"Precompiled image will be created with {num_variants} variants.")

        # Handle border radius for image blocks
        border_radius = [0, 0, 0, 0]  # Default: top-left, top-right, bottom-right, bottom-left
        if block_type == 'image':
            logger.info(f"Specify border radius for image (4 integers for top-left, top-right, bottom-right, bottom-left corners)")
            top_left = user_input.get_input(f"Top-left corner radius", 0, is_integer=True)
            top_right = user_input.get_input(f"Top-right corner radius", 0, is_integer=True)
            bottom_right = user_input.get_input(f"Bottom-right corner radius", 0, is_integer=True)
            bottom_left = user_input.get_input(f"Bottom-left corner radius", 0, is_integer=True)
            border_radius = [top_left, top_right, bottom_right, bottom_left]

        # Get styles
        styles = self._get_styles(block_type, index, user_input, needs_null_styles)

        # Get dimensions
        dimensions = self._get_dimensions(block_type, index, user_input, is_first_block)

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
            border_radius=border_radius
        )

    def create_watermark_block(self, dimension_config):
        """Create a watermark block with specified dimensions"""
        wm_id = self.id_generator.generate_uuid7()
        wm_dims = dimension_config

        return Block(
            id=wm_id,
            type="watermark",
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
                "color": "#ffffff"
            },
            dimensions={
                "x": wm_dims["x"],
                "y": wm_dims["y"],
                "w": wm_dims["w"],
                "h": wm_dims["h"]
            }
        )

    def create_background_block(self, bg_config):
        """Create a background block with specified config"""
        bg_id = self.id_generator.generate_uuid7()
        bg_dims = bg_config["dimensions"]

        return Block(
            id=bg_id,
            type="background",
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
                "color": "#ffffff"
            },
            dimensions={
                "x": bg_dims["x"],
                "y": bg_dims["y"],
                "w": bg_dims["w"],
                "h": bg_dims["h"]
            }
        )

    def _get_styles(self,
                   block_type,
                   index,
                   user_input,
                   needs_null_styles):
        """Get style information for a block"""
        if needs_null_styles:
            # For null-style blocks, only collect z-index
            default_z_index = self.config.get_default_z_index(block_type)
            z_index = user_input.get_input(f"Block {index + 1} Z-Index", default_z_index, is_integer=True)

            return {
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": z_index,
                "textTransform": None,
                "color": None
            }
        else:
            default_styles = self.config.get_default_styles(block_type)

            text_vertical = user_input.get_input(
                f"Block {index + 1} Text Vertical Alignment",
                default_styles['text_vertical'],
                options=['top', 'middle', 'bottom']
            )

            text_horizontal = user_input.get_input(
                f"Block {index + 1} Text Horizontal Alignment",
                default_styles['text_horizontal'],
                options=['left', 'center', 'right']
            )

            font_size = user_input.get_input(f"Block {index + 1} Font Size", default_styles['font_size'], is_integer=True)
            weight = user_input.get_input(f"Block {index + 1} Weight", default_styles['weight'], is_integer=True)
            text_transform = default_styles['text_transform']

            # Get default z-index based on the block type
            default_z_index = self.config.get_default_z_index(block_type)
            z_index = user_input.get_input(f"Block {index + 1} Z-Index", default_z_index, is_integer=True)

            return {
                "textVertical": text_vertical,
                "textHorizontal": text_horizontal,
                "fontSize": font_size,
                "weight": weight,
                "zIndex": z_index,
                "textTransform": text_transform,
                "color": None
            }

    def _get_dimensions(self,
                        block_type,
                        index,
                        user_input,
                        is_first_block):
        """Get dimensions for a block"""
        default_dims = self.config.get_default_dimensions(block_type, is_first_block)
        x = user_input.get_input(f"Block {index + 1} X Position", default_dims['x'], is_integer=True)
        y = user_input.get_input(f"Block {index + 1} Y Position", default_dims['y'], is_integer=True)
        w = user_input.get_input(f"Block {index + 1} Width", default_dims['w'], is_integer=True)
        h = user_input.get_input(f"Block {index + 1} Height", default_dims['h'], is_integer=True)

        return {"x": x, "y": y, "w": w, "h": h}


# ================ SQL Command Pattern ================

class SQLCommand(ABC):
    """Base class for SQL commands"""

    @abstractmethod
    def execute(self) -> str:
        """Execute the command and return SQL"""
        pass


class SlideLayoutCommand(SQLCommand):
    """Generates SlideLayout SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout, current_time: str):
        self.config = config
        self.slide_layout = slide_layout
        self.current_time = current_time

    def execute(self) -> str:
        """Generate SlideLayout SQL"""
        return self.config.get_sql_template('slide_layout').format(
            slide_layout_id=self.slide_layout.id,
            slide_layout_name=self.slide_layout.name,
            slide_layout_number=self.slide_layout.number,
            presentation_layout_id=self.slide_layout.presentation_layout_id,
            is_last=str(self.slide_layout.is_last).lower(),
            for_generation = str(self.slide_layout.for_generation).lower()
        )


class BlockLayoutCommand(SQLCommand):
    """Generates BlockLayout SQL"""

    def __init__(self, config: ConfigManager, blocks: List[Block], slide_layout_id: str):
        self.config = config
        self.blocks = blocks
        self.slide_layout_id = slide_layout_id

    def execute(self) -> str:
        """Generate BlockLayout SQL"""
        values = self._format_block_layout_values()
        return self.config.get_sql_template('block_layout').format(
            block_layout_values=values
        )

    def _format_block_layout_values(self) -> str:
        """Format the values for BlockLayout SQL"""
        values = []
        for block in self.blocks:
            values.append(
                f"    ('{block.id}', '{self.slide_layout_id}', '{block.type}'::\"BlockLayoutType\")")
        return ",\n".join(values)


class BlockStylesCommand(SQLCommand):
    """Generates BlockLayoutStyles SQL"""

    def __init__(self, config: ConfigManager, blocks: List[Block]):
        self.config = config
        self.blocks = blocks

    def execute(self) -> str:
        """Generate BlockLayoutStyles SQL"""
        values = self._format_styles_values()
        return self.config.get_sql_template('block_styles').format(
            styles_values=values
        )

    def _format_styles_values(self) -> str:
        """Format the values for BlockLayoutStyles SQL"""
        values = []
        default_color = self.config.get_default_color()
        color_settings_id = self.config.get_default_color_settings_id()

        for block in self.blocks:
            # Only set border radius for image blocks, use null for all others
            if block.type == 'image' and block.border_radius:
                border_radius_str = f"ARRAY[{', '.join(map(str, block.border_radius))}]"
            else:
                border_radius_str = "null"

            # Format the SQL based on block type
            color_value = block.styles.get('color')
            if color_value:
                color_value = str(color_value).strip().lower()
            if not color_value or not color_value.startswith('#') or len(color_value) not in (4, 7):
                color_value = default_color
            if block.needs_null_styles:
                if block.is_background or block.is_figure:
                    # For background and figure blocks, use the block's color or default white
                    values.append(
                        f"    ('{block.id}', null, null, null, null, {block.styles.get('zIndex', 1)}, '{color_value}', null, {border_radius_str}, '{color_settings_id}')")
                else:
                    # For other null style blocks, set color from styles or default
                    values.append(
                        f"    ('{block.id}', null, null, null, null, {block.styles.get('zIndex', 1)}, '{color_value}', null, {border_radius_str}, '{color_settings_id}')")
            else:
                # For text-based blocks, set color from styles or default
                styles = block.styles
                values.append(
                    f"    ('{block.id}', '{styles.get('textVertical')}', '{styles.get('textHorizontal')}', {styles.get('fontSize')}, {styles.get('weight')}, {styles.get('zIndex', 1)}, '{color_value}', '{styles.get('textTransform')}', {border_radius_str}, '{color_settings_id}')"
                )
        return ",\n".join(values)


class BlockDimensionsCommand(SQLCommand):
    """Generates BlockLayoutDimensions SQL"""

    def __init__(self, config: ConfigManager, blocks: List[Block]):
        self.config = config
        self.blocks = blocks

    def execute(self) -> str:
        """Generate BlockLayoutDimensions SQL"""
        values = self._format_dimension_values()
        return self.config.get_sql_template('block_dimensions').format(
            dimension_values=values
        )

    def _format_dimension_values(self) -> str:
        """Format the values for BlockLayoutDimensions SQL"""
        values = []
        for block in self.blocks:
            dim = block.dimensions
            values.append(f"    ('{block.id}', {dim['x']}, {dim['y']}, {dim['w']}, {dim['h']})")
        return ",\n".join(values)


class FigureCommand(SQLCommand):
    """Generates Figure SQL"""

    def __init__(self, config: ConfigManager, id_generator: IdGenerator, figure_blocks: List[Dict[str, str]]):
        self.config = config
        self.id_generator = id_generator
        self.figure_blocks = figure_blocks

    def execute(self) -> str:
        """Generate Figure SQL"""
        if not self.figure_blocks:
            return ""

        values = self._format_figure_values()
        return self.config.get_sql_template('figure').format(
            figure_values=values
        )

    def _format_figure_values(self) -> str:
        """Format the values for Figure SQL"""
        values = []
        for figure in self.figure_blocks:
            figure_id = self.id_generator.generate_uuid7()
            values.append(f"    ('{figure_id}', '{figure['block_id']}', '{figure['name']}')")
        return ",\n".join(values)


class PrecompiledImageCommand(SQLCommand):
    """Generates PrecompiledImage SQL"""

    def __init__(self, config: ConfigManager, id_generator: IdGenerator, precompiled_image_blocks: List[Dict[str, str]]):
        self.config = config
        self.id_generator = id_generator
        self.precompiled_image_blocks = precompiled_image_blocks

    def execute(self) -> str:
        """Generate PrecompiledImage SQL"""
        if not self.precompiled_image_blocks:
            return ""

        values = self._format_precompiled_image_values()
        return self.config.get_sql_template('precompiled_image').format(
            precompiled_image_values=values
        )

    def _format_precompiled_image_values(self) -> str:
        """Format the values for PrecompiledImage SQL"""
        values = []
        for precompiled_image in self.precompiled_image_blocks:
            precompiled_image_id = self.id_generator.generate_uuid7()
            color_value = f"'{precompiled_image['color']}'" if precompiled_image['color'] else "null"
            values.append(f"    ('{precompiled_image_id}', '{precompiled_image['block_layout_id']}', '{precompiled_image['url']}', {color_value})")
        return ",\n".join(values)


class SlideLayoutAdditionalInfoCommand(SQLCommand):
    """Generates SlideLayoutAdditionalInfo SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout):
        self.config = config
        self.slide_layout = slide_layout

    def execute(self) -> str:
        """Generate SlideLayoutAdditionalInfo SQL"""
        additional_info = self.config.get_slide_layout_additional_info()

        return self.config.get_sql_template('slide_layout_additional_info').format(
            slide_layout_id=self.slide_layout.id,
            percentesCount=additional_info['percentesCount'],
            maxSymbolsInBlock=additional_info['maxSymbolsInBlock'],
            hasHeaders=str(additional_info['hasHeaders']).lower(),
            type=self.slide_layout.type,
            icon_url=self.slide_layout.icon_url
        )


class SlideLayoutDimensionsCommand(SQLCommand):
    """Generates SlideLayoutDimensions SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout):
        self.config = config
        self.slide_layout = slide_layout

    def execute(self) -> str:
        """Generate SlideLayoutDimensions SQL"""
        dimensions = self.config.get_slide_layout_dimensions()

        return self.config.get_sql_template('slide_layout_dimensions').format(
            slide_layout_id=self.slide_layout.id,
            x=dimensions['x'],
            y=dimensions['y'],
            w=dimensions['w'],
            h=dimensions['h']
        )


class SlideLayoutStylesCommand(SQLCommand):
    """Generates SlideLayoutStyles SQL"""

    def __init__(self, config: ConfigManager, slide_layout: SlideLayout):
        self.config = config
        self.slide_layout = slide_layout

    def execute(self) -> str:
        """Generate SlideLayoutStyles SQL"""
        return self.config.get_sql_template('slide_layout_styles').format(
            slide_layout_id=self.slide_layout.id
        )


# ================ Strategy Pattern for Slide Type Determination ================

class SlideTypeStrategy(ABC):
    """Base class for slide type determination strategies"""

    @abstractmethod
    def determine_slide_type(self, slide_layout: SlideLayout, blocks: List[Block]) -> Tuple[str, str]:
        """Determine the slide type based on layout and blocks"""
        pass


class NumberBasedSlideTypeStrategy(SlideTypeStrategy):
    """Determines slide type based on slide number"""

    def __init__(self, config: ConfigManager):
        self.config = config

    def determine_slide_type(self, slide_layout: SlideLayout, blocks: List[Block]) -> Tuple[str, str, bool]:
        """Determine the slide type based on slide number"""
        number = slide_layout.number

        # Determine if this slide should have forGeneration set to false
        for_generation = True
        # Set forGeneration to False for 5cols, 6cols, 7cols
        if number in [7, 10, 11]:
            for_generation = False
            logger.info(f"Setting forGeneration to false for slide number {number} (5cols, 6cols, 7cols)")

        if slide_layout.is_last or number == -1:
            type_key = "last"
            logger.info(f"Slide type automatically set to 'last' because this is the last slide (number -1)")
        elif number == 1:
            type_key = "title"
            logger.info(f"Slide type automatically set to 'title' because this is slide number 1")
        elif number == 2:
            type_key = "few_text"
            logger.info(f"Slide type automatically set to 'few_text' because this is slide number 2")
        elif number == 3:
            type_key = "optimal_text"
            logger.info(f"Slide type automatically set to 'optimal_text' because this is slide number 3")
        elif number == 4:
            type_key = "many_text"
            logger.info(f"Slide type automatically set to 'many_text' because this is slide number 4")
        elif number == 5:
            type_key = "infographics"
            logger.info(f"Slide type automatically set to 'infographics' because this is slide number 5")
        elif number == 6:
            type_key = "extra_text"
            logger.info(f"Slide type automatically set to 'extra_text' because this is slide number 6")
        elif number == 7:
            type_key = "other"
            logger.info(f"Slide type automatically set to 'other' because this is slide number 7")
        elif number == 8:
            type_key = "table"
            logger.info(f"Slide type automatically set to 'table' because this is slide number 8")
        elif number == 10:
            type_key = "other"
            logger.info(f"Slide type automatically set to 'other' because this is slide number 10")
        elif number == 14:
            type_key = "chart"
            logger.info(f"Slide type automatically set to 'chart' because this is slide number 14")
        else:
            # Default to classic for other slide numbers
            type_key = "classic"
            logger.info(f"Slide type automatically set to 'classic' (default for slide number {number})")

        # If not for_generation, set type to 'other'
        if not for_generation:
            type_key = "other"
            logger.info(f"for_generation is False, so type is set to 'other'")

        slide_type = self.config.get_slide_layout_type(type_key)
        return type_key, slide_type, for_generation


class ContentBasedSlideTypeStrategy(SlideTypeStrategy):
    """Determines slide type based on content blocks"""

    def __init__(self, config: ConfigManager):
        self.config = config

    def determine_slide_type(self, slide_layout: SlideLayout, blocks: List[Block]) -> Tuple[str, str, bool]:
        """Determine the slide type based on content blocks"""
        # If last slide, don't change the type
        if slide_layout.is_last:
            return slide_layout.type_key, self.config.get_slide_layout_type(slide_layout.type_key), slide_layout.for_generation

        # Check for special block types
        has_table_block = any(block.type == 'table' for block in blocks)
        has_infographik_block = any(block.type == 'infographik' for block in blocks)
        has_chart_block = any(block.type == 'chart' for block in blocks)

        old_type_key = slide_layout.type_key

        if has_table_block:
            type_key = "table"
            logger.info(f"Slide type changed from '{old_type_key}' to 'table' because this slide contains a table block")
        elif has_chart_block:
            type_key = "chart"
            logger.info(f"Slide type changed from '{old_type_key}' to 'chart' because this slide contains a chart block")
        elif has_infographik_block:
            type_key = "infographics"
            logger.info(f"Slide type changed from '{old_type_key}' to 'infographics' because this slide contains an infographik block")
        else:
            # No need to change
            return old_type_key, self.config.get_slide_layout_type(old_type_key), slide_layout.for_generation

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
        self.content_strategy = ContentBasedSlideTypeStrategy(self.config_manager)

        # Set up logging to file in the output directory
        if output_dir is None:
            output_dir = self.config_manager.get_output_config()['output_dir']
        setup_slide_insertion_logger(output_dir)

    def run(self) -> None:
        """Run the SQL Generator"""
        while True:
            output_file = self.generate_sql()

            show_sql = self.user_input.get_input("\nWould you like to see the generated SQL?", "n",
                                               options=["y", "n"]) == "y"
            if show_sql:
                with open(output_file, 'r') as f:
                    logger.info("\n" + f.read())

            again = self.user_input.get_input("\nWould you like to generate another SQL file?", "n",
                                            options=["y", "n"]) == "y"
            if not again:
                break

    def generate_sql(self) -> str:
        """Generate SQL based on user input"""
        logger.info("Starting SQL generation process.")
        # Collect slide layout information
        slide_layout = self._collect_slide_information()
        logger.info(f"Collected slide layout: name={slide_layout.name}, number={slide_layout.number}, type={slide_layout.type}, is_last={slide_layout.is_last}")
        # Collect blocks
        blocks, figure_blocks, precompiled_image_blocks = self._collect_blocks(slide_layout)
        logger.info(f"Collected {len(blocks)} blocks for slide '{slide_layout.name}' (number {slide_layout.number})")
        for block in blocks:
            logger.info(f"Block: type={block.type}, name={getattr(block, 'name', '')}, dimensions={block.dimensions}, styles={block.styles}")
        # Update slide type based on content
        self._update_slide_type(slide_layout, blocks)
        logger.info(f"Final slide type: {slide_layout.type}")
        # Generate SQL
        sql = self._generate_sql_queries(slide_layout, blocks, figure_blocks, precompiled_image_blocks)
        # Write SQL to file
        output_file = self._write_sql_to_file(sql, slide_layout)
        logger.info(f"SQL written to {output_file}")
        logger.info("SQL generation process completed.")
        return output_file

    def _collect_slide_information(self) -> SlideLayout:
        """Collect slide layout information"""
        slide_layout_name = self.user_input.get_input(
            "SlideLayout name",
            self.config_manager.get_default_value('slide_layout_name')
        )

        # Ask if this is the last slide
        is_last_slide_option = self.user_input.get_input(
            "Is this the last slide?",
            "no",
            options=["yes", "no"]
        )
        is_last_slide = (is_last_slide_option == "yes")

        slide_layout_number = -1 if is_last_slide else self.user_input.get_input(
            "SlideLayout number",
            self.config_manager.get_default_value('slide_layout_number'),
            is_integer=True
        )

        presentation_layout_id = self.user_input.get_input(
            "Presentation Layout ID",
            self.config_manager.get_default_value('presentation_layout_id')
        )

        # Initialize with a default for_generation value (will be updated by the strategy)
        for_generation = True

        # Determine initial slide type based on number
        type_key, slide_type, for_generation = self.number_strategy.determine_slide_type(
            SlideLayout(
                id="",  # Temporary ID until we generate it
                name=slide_layout_name,
                number=slide_layout_number,
                presentation_layout_id=presentation_layout_id,
                is_last=is_last_slide,
                type_key="classic",  # Will be set by the strategy
                type="",      # Will be set by the strategy
                icon_url="",  # Will be set later
                for_generation=for_generation
            ),
            []  # No blocks yet
        )

        # Use SLIDE_NUMBER_TO_NUMBER for icon url, but skip number for certain types
        skip_number_types = {"infographics", "table", "chart", "last", "title"}
        if slide_type in skip_number_types:
            icon_url = f"{self.config_manager.get_miniatures_base_path()}/{slide_type}/{slide_layout_name}.svg"
        else:
            number_for_icon = self.config_manager.config.SLIDE_NUMBER_TO_NUMBER.get(slide_layout_number, slide_layout_number)
            icon_url = f"{self.config_manager.get_miniatures_base_path()}/{slide_type}/{number_for_icon}_{slide_layout_name}.svg"

        # Generate ID for slide layout
        slide_layout_id = self.id_generator.generate_uuid7()

        return SlideLayout(
            id=slide_layout_id,
            name=slide_layout_name,
            number=slide_layout_number,
            presentation_layout_id=presentation_layout_id,
            is_last=is_last_slide,
            type_key=type_key,
            type=slide_type,
            icon_url=icon_url,
            for_generation=for_generation
        )

    def _collect_blocks(self, slide_layout):
        """Collect block information"""
        blocks = []
        figure_blocks = []
        precompiled_image_blocks = []

        # For last slides, add watermark info
        if slide_layout.is_last:
            logger.info("Last slide will automatically include a watermark block.")
        # For non-last slides, add watermark based on config
        elif self.config_manager.should_add_watermark():
            logger.info("Regular slide will automatically include a watermark block.")

        # Add automatic background if configured
        if self.config_manager.should_add_background():
            bg_config = self.config_manager.get_auto_block_config("background")
            bg_block = self.block_factory.create_background_block(bg_config)
            blocks.append(bg_block)
            logger.info(f"\nAutomatically added background block with color {bg_config['color']}")

        # Add watermarks based on slide type
        if slide_layout.is_last:
            # Add watermark for last slide
            wm_config = self.config_manager.get_auto_block_config("last_slide")["watermark1"]
            wm_block = self.block_factory.create_watermark_block(wm_config["dimensions"])
            blocks.append(wm_block)
            logger.info("\nAutomatically added watermark block for last slide")
        elif self.config_manager.should_add_watermark():
            # Add regular watermark
            wm_config = self.config_manager.get_auto_block_config("watermark")
            wm_block = self.block_factory.create_watermark_block(wm_config["dimensions"])
            blocks.append(wm_block)
            logger.info("\nAutomatically added watermark block")

        # Collect user-defined blocks
        num_blocks = self.user_input.get_input(
            "How many additional blocks do you want to create?",
            self.config_manager.get_default_value('num_blocks'),
            is_integer=True
        )

        for i in range(num_blocks):
            logger.info(f"\nBlock {i + 1} information:")

            is_first_block = (i == 0)
            default_type = 'slideTitle' if is_first_block else 'text'
            block_type = self.user_input.get_input(
                f"Block {i + 1} Layout Type",
                default_type,
                options=self.config_manager.get_block_type_options()
            )

            block = self.block_factory.create_block(
                block_type,
                i,
                self.user_input,
                num_blocks
            )

            if block:
                blocks.append(block)
                if block.figure_info:
                    figure_blocks.append(block.figure_info)
                if block.precompiled_image_info:
                    # If it's a list (multiple variants), extend; else, append
                    if isinstance(block.precompiled_image_info, list):
                        precompiled_image_blocks.extend(block.precompiled_image_info)
                    else:
                        precompiled_image_blocks.append(block.precompiled_image_info)

        # Ensure a background block is present
        has_background = any(b.type == 'background' for b in blocks)
        if not has_background:
            bg_config = self.config_manager.config.AUTO_BLOCKS['background']
            bg_styles = {
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": bg_config['z_index'],
                "textTransform": None,
                "color": bg_config['color']
            }
            bg_block = Block(
                id=self.id_generator.generate_uuid7(),
                type='background',
                dimensions=bg_config['dimensions'],
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
                name="background"
            )
            blocks.insert(0, bg_block)

        # Add watermark block if specified in config
        add_watermark = False
        if hasattr(self.config_manager.config, 'WATERMARK_SLIDES'):
            add_watermark = slide_layout.number in self.config_manager.config.WATERMARK_SLIDES
        if add_watermark:
            if slide_layout.number == -1 and 'last_slide' in self.config_manager.config.AUTO_BLOCKS:
                wm_dims = self.config_manager.config.AUTO_BLOCKS['last_slide']['watermark1']['dimensions']
            else:
                wm_dims = self.config_manager.config.AUTO_BLOCKS['watermark']['dimensions']
            wm_block = Block(
                id=self.id_generator.generate_uuid7(),
                type='watermark',
                dimensions=wm_dims,
                styles={
                    "textVertical": None,
                    "textHorizontal": None,
                    "fontSize": None,
                    "weight": None,
                    "zIndex": self.config_manager.config.Z_INDEX_DEFAULTS['watermark'],
                    "textTransform": None,
                    "color": "#ffffff"
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
                name="watermark"
            )
            blocks.append(wm_block)

        return blocks, figure_blocks, precompiled_image_blocks

    def _update_slide_type(self, slide_layout, blocks):
        """Update slide type based on block content"""
        type_key, slide_type, for_generation = self.content_strategy.determine_slide_type(slide_layout, blocks)

        # Update slide layout with potentially new type
        slide_layout.type_key = type_key
        slide_layout.type = slide_type
        skip_number_types = {"infographics", "table", "chart", "last", "hero"}
        if slide_type in skip_number_types or slide_layout.number == 0:
            slide_layout.icon_url = f"{self.config_manager.get_miniatures_base_path()}/{slide_type}/{slide_layout.name}.svg"
        else:
            number_for_icon = self.config_manager.config.SLIDE_NUMBER_TO_NUMBER.get(slide_layout.number, slide_layout.number)
            slide_layout.icon_url = f"{self.config_manager.get_miniatures_base_path()}/{slide_type}/{number_for_icon}_{slide_layout.name}.svg"

    def _generate_sql_queries(self,
                            slide_layout,
                            blocks,
                            figure_blocks,
                            precompiled_image_blocks):
        """Generate SQL queries for all entities"""
        sql_queries = []

        # Create timestamp for SQL comment header
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql_queries.append(f"-- Generated on {current_time}\n")

        # Create and execute all SQL commands
        commands = [
            # 1. SlideLayout
            SlideLayoutCommand(self.config_manager, slide_layout, current_time),

            # 2. BlockLayout
            BlockLayoutCommand(self.config_manager, blocks, slide_layout.id),

            # 3. BlockLayoutStyles
            BlockStylesCommand(self.config_manager, blocks),

            # 4. BlockLayoutDimensions
            BlockDimensionsCommand(self.config_manager, blocks),
        ]

        # 5. Figure records (optional)
        if figure_blocks:
            commands.append(
                FigureCommand(self.config_manager, self.id_generator, figure_blocks)
            )

        # 6. PrecompiledImage records (optional)
        if precompiled_image_blocks:
            commands.append(
                PrecompiledImageCommand(self.config_manager, self.id_generator, precompiled_image_blocks)
            )

        # 7-9. Additional slide layout info
        commands.extend([
            SlideLayoutAdditionalInfoCommand(self.config_manager, slide_layout),
            SlideLayoutDimensionsCommand(self.config_manager, slide_layout),
            SlideLayoutStylesCommand(self.config_manager, slide_layout)
        ])

        # Execute all commands and collect SQL
        for command in commands:
            sql = command.execute()
            if sql:  # Only add non-empty SQL
                sql_queries.append(sql)

        # Join all SQL queries
        return "\n\n".join(sql_queries)

    def _write_sql_to_file(self, sql, slide_layout):
        """Write SQL to output file, with folder based on slide number"""
        output_config = self.config_manager.get_output_config()
        base_output_dir = output_config['output_dir']

        # Get the folder name based on slide number
        folder_name = self.config_manager.get_folder_for_slide_number(slide_layout.number)

        # Create the full output directory path
        output_dir = os.path.join(base_output_dir, folder_name)

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created directory: {output_dir}")

        # Generate filename with timestamp
        readable_time = datetime.now().strftime(output_config['timestamp_format'])
        file_name = output_config['filename_template'].format(
            slide_layout_name=slide_layout.name,
            timestamp=readable_time
        )
        output_file = os.path.join(output_dir, file_name)

        # Write SQL to file
        with open(output_file, 'w') as f:
            f.write(sql)

        logger.info(f"\nSQL has been generated and saved to {output_file}")
        return output_file

def auto_generate_sql_from_figma(json_path, output_dir=None):
    """
    Automatically generate SQL files from a Figma JSON export (as produced by figma.py's sql_generator_input.json),
    without any user interaction. Each slide in the JSON will be processed and SQL files will be written to the appropriate output directory.
    """
    import json
    from datetime import datetime
    import config

    generator = SQLGenerator(config, output_dir=output_dir)
    output_dir = output_dir or config.OUTPUT_CONFIG['output_dir']
    setup_slide_insertion_logger(output_dir)
    logger.info(f"Starting auto SQL generation from {json_path} to {output_dir}")
    def strip_zindex(name: str) -> str:
        # Remove ' z-index N' (case-insensitive, with or without leading/trailing spaces)
        return re.sub(r'\s*z-index\s*\d+\s*$', '', name, flags=re.IGNORECASE)
    color_pattern = re.compile(r'(#[0-9a-fA-F]{3,6})')
    precompiled_image_pattern = re.compile(r'^image precompiled ([^\s]+) z-index \d+ (#[0-9a-fA-F]{3,6})$', re.IGNORECASE)
    with open(json_path, 'r', encoding='utf-8') as f:
        slides = json.load(f)
    for slide in slides:
        logger.info(f"Processing slide: name={slide['slide_layout_name']}, number={slide['slide_layout_number']}, type={slide['slide_type']}")
        # Generate a UUID for the SlideLayout
        slide_layout_id = generator.id_generator.generate_uuid7()
        # Strip z-index from slide layout name
        clean_slide_layout_name = strip_zindex(slide['slide_layout_name'])
        # Build SlideLayout object
        slide_layout = SlideLayout(
            id=slide_layout_id,
            name=clean_slide_layout_name,
            number=slide['slide_layout_number'],
            presentation_layout_id=slide['presentation_layout_id'],
            is_last=slide['is_last'],
            type_key=slide['slide_type'],
            type=slide['slide_type'],
            icon_url="",  # Will be set below
            for_generation=True  # Will be set by SQLGenerator
        )
        logger.info(f"Created SlideLayout: {slide_layout}")
        # Set icon_url using config and slide info (same as manual mode)
        miniatures_base_path = config.MINIATURES_BASE_PATH
        slide_type = slide_layout.type
        slide_layout_name = slide_layout.name
        slide_layout_number = slide_layout.number
        skip_number_types = {"infographics", "table", "chart", "last", "title", "hero"}
        if slide_type in skip_number_types or slide_layout_number == 0:
            icon_url = f"{miniatures_base_path}/{slide_type}/{slide_layout_name}.svg"
        else:
            number_for_icon = config.SLIDE_NUMBER_TO_NUMBER.get(slide_layout_number, slide_layout_number)
            icon_url = f"{miniatures_base_path}/{slide_type}/{number_for_icon}_{slide_layout_name}.svg"
        slide_layout.icon_url = icon_url
        # Build Block objects with generated UUIDs
        blocks = []
        block_id_map = {}  # Map Figma block id to generated UUID
        precompiled_images = []
        figure_blocks = []
        for block in slide['blocks']:
            block_uuid = generator.id_generator.generate_uuid7()
            block_id_map[block['id']] = block_uuid
            styles = dict(block['styles']) if block.get('styles') else {}
            color = None
            if 'color' in styles and styles['color']:
                color = styles['color']
            elif 'color' in block and block['color']:
                color = block['color']
            elif block.get('styles', {}).get('color'):
                color = block['styles']['color']
            if color is not None:
                styles['color'] = str(color)
            else:
                styles['color'] = None
            # --- Precompiled image extraction logic ---
            if block['type'] == 'image' and block['name'].startswith('image precompiled'):
                # Extract base name and color if present
                match = re.match(r'image precompiled ([^ ]+)(?: z-index \d+)?(?: (#[0-9a-fA-F]{3,6}))?', block['name'])
                if match:
                    base_name = match.group(1)
                    base_url = config.PRECOMPILED_IMAGES["base_url"]
                    colors = config.PRECOMPILED_IMAGES["default_colors"]
                    prefixes = config.PRECOMPILED_IMAGES["prefix"]
                    # If color is present in the block name, use it, else use all default colors
                    if match.group(2):
                        color_val = match.group(2)
                        url = f"{base_url}/{base_name}.png"
                        precompiled_images.append({
                            "block_layout_id": block_uuid,
                            "url": url,
                            "color": color_val
                        })
                    else:
                        for color_val, prefix in zip(colors, prefixes):
                            variant_name = f"{base_name}{prefix}"
                            url = f"{base_url}/{variant_name}.png"
                            precompiled_images.append({
                                "block_layout_id": block_uuid,
                                "url": url,
                                "color": color_val
                            })
            clean_block_name = strip_zindex(block['name'])
            # --- Figure extraction logic ---
            if block['type'] == 'figure':
                match = re.search(r'\(([^)]+)\)', clean_block_name)
                if match:
                    figure_name = match.group(1)
                else:
                    figure_name = clean_block_name
                figure_color = color if color is not None else '#ffffff'
                figure_blocks.append({
                    "block_id": block_uuid,
                    "name": figure_name,
                    "color": figure_color
                })
            block_obj = Block(
                id=block_uuid,
                type=block['type'],
                dimensions=block['dimensions'],
                styles=styles,
                needs_null_styles=block['needs_null_styles'],
                needs_z_index=block['needs_z_index'],
                is_figure=block.get('is_figure', False),
                is_background=block.get('is_background', False),
                is_precompiled_image=block.get('is_precompiled_image', False),
                color=None,
                figure_info=block.get('figure_info'),
                precompiled_image_info=block.get('precompiled_image_info'),
                border_radius=block.get('corner_radius', [0, 0, 0, 0]),
                name=clean_block_name
            )
            blocks.append(block_obj)
            logger.info(f"Block: type={block_obj.type}, name={block_obj.name}, dimensions={block_obj.dimensions}, styles={block_obj.styles}")
        # Ensure a background block is present
        has_background = any(b.type == 'background' for b in blocks)
        if not has_background:
            bg_config = config.AUTO_BLOCKS['background']
            bg_styles = {
                "textVertical": None,
                "textHorizontal": None,
                "fontSize": None,
                "weight": None,
                "zIndex": bg_config['z_index'],
                "textTransform": None,
                "color": bg_config['color']
            }
            bg_block = Block(
                id=generator.id_generator.generate_uuid7(),
                type='background',
                dimensions=bg_config['dimensions'],
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
                name="background"
            )
            blocks.insert(0, bg_block)
            logger.info(f"Automatically added background block: {bg_block}")
        # Add watermark block if specified in config
        add_watermark = False
        if hasattr(config, 'WATERMARK_SLIDES'):
            add_watermark = slide_layout.number in config.WATERMARK_SLIDES
        if add_watermark:
            if slide_layout.number == -1 and 'last_slide' in config.AUTO_BLOCKS:
                wm_dims = config.AUTO_BLOCKS['last_slide']['watermark1']['dimensions']
            else:
                wm_dims = config.AUTO_BLOCKS['watermark']['dimensions']
            wm_block = Block(
                id=generator.id_generator.generate_uuid7(),
                type='watermark',
                dimensions=wm_dims,
                styles={
                    "textVertical": None,
                    "textHorizontal": None,
                    "fontSize": None,
                    "weight": None,
                    "zIndex": config.Z_INDEX_DEFAULTS['watermark'],
                    "textTransform": None,
                    "color": "#ffffff"
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
                name="watermark"
            )
            blocks.append(wm_block)
            logger.info(f"Automatically added watermark block: {wm_block}")
        # Use SQLGenerator's internal methods to generate SQL and write to file
        sql = generator._generate_sql_queries(slide_layout, blocks, figure_blocks, precompiled_images)
        folder_name = generator.config_manager.get_folder_for_slide_number(slide_layout.number)
        output_path = os.path.join(output_dir, folder_name)
        os.makedirs(output_path, exist_ok=True)
        timestamp = datetime.now().strftime(config.OUTPUT_CONFIG['timestamp_format'])
        filename = f"{clean_slide_layout_name}_{timestamp}.sql"
        sql_file_path = os.path.join(output_path, filename)
        with open(sql_file_path, 'w', encoding='utf-8') as f:
            f.write(sql)
        logger.info(f"Generated SQL for slide {clean_slide_layout_name} at {sql_file_path}")
    logger.info("Auto SQL generation process completed.")

def main():
    """Main entry point for interactive mode"""
    import config
    generator = SQLGenerator(config)
    generator.run()

# Extend CLI to support --auto-from-figma
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SQL Generator for Layout and Blocks (interactive or auto mode)")
    parser.add_argument('--auto-from-figma', type=str, help='Path to sql_generator_input.json from figma.py for non-interactive SQL generation')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory for SQL files (optional, overrides config)')
    args, unknown = parser.parse_known_args()

    if args.auto_from_figma:
        auto_generate_sql_from_figma(args.auto_from_figma, args.output_dir)
    else:
        main_output_dir = args.output_dir if args.output_dir else None
        import config
        generator = SQLGenerator(config, output_dir=main_output_dir)
        generator.run()