import re
import json
from typing import Optional, Any, Callable

from api_v1.services.data_classes import ExtractedBlock
from api_v1.constants import BLOCKS, TYPES, CONSTANTS, SLIDES
from api_v1.services.filter_service import FilterMode, FilterConfig


# ================ Helpful functions & classes ================

def json_dump(obj, filename: str):
    with open(filename, "w", encoding="utf-8") as outfile:
        json.dump(obj, outfile, ensure_ascii=False, indent=4)


def safe_in(item: Any, container) -> bool:
    if not container:
        return False
    return item in container


class Checker:
    @staticmethod
    def check_z_index(name: str) -> bool:
        """Checks if the frame name contains a Z-index. """
        return 'z-index' in name

    @staticmethod
    def check_dimensions(absolute_bounding_box: dict) -> bool:
        """Checks whether the frame size matches the target width and height."""
        width_diff = abs(absolute_bounding_box['width'] - CONSTANTS.FIGMA_CONFIG['TARGET_WIDTH'])
        height_diff = abs(absolute_bounding_box['height'] - CONSTANTS.FIGMA_CONFIG['TARGET_HEIGHT'])
        return width_diff < 1 and height_diff < 1

    @staticmethod
    def check_min_area(absolute_bounding_box: dict, min_area: int) -> bool:
        """Checks whether the frame area exceeds the minimum threshold."""
        area = absolute_bounding_box['width'] * absolute_bounding_box['height']
        return area >= min_area

    @staticmethod
    def check_marker(ready_to_dev_marker: str, name: str) -> bool:
        """Checks for the 'ready to dev' label."""
        if ready_to_dev_marker:
            return ready_to_dev_marker.lower() in name.lower()
        return True


def round5(value: float) -> int:
    """Round value to nearest 5"""
    return round(value / 5) * 5


def get_slide_number(parent_name: str) -> int:
    """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
    key = parent_name.strip().lower()
    return SLIDES.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)


def detect_slide_type(container_name: str, slide_number: int) -> str:
    """Detect slide type using only config.py as the source of truth."""
    # Use config mapping for container name to slide number
    key = container_name.strip().lower()
    number = SLIDES.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
    # Use config mapping for slide number to type
    return SLIDES.SLIDE_NUMBER_TO_TYPE.get(number, 'classic')


# ================ Text Utils ================

def count_words(text: str) -> int:
    if not text:
        return 0
    return len([w for w in re.split(r'\s+', text) if w.strip()])


def count_sentences(text: str) -> int:
    if not text:
        return 0
    split_result = [s for s in re.split(r'[.!?]', text)]
    n = len([s for s in split_result if s.strip()])
    return n if n > 0 else 1


# ================ Figure Utils ================

def extract_base_figure_name(name: str) -> str:
    """Extract the base figure name from a block name (e.g., 'figure (logoRfs_0)' -> 'logoRfs')."""
    if not name:
        return ''
    name_match = re.search(r'\(([^)]+)\)', name)
    if name_match:
        base_name = name_match.group(1)
        # Remove trailing _<number> if present
        base_name = re.sub(r'_(\d+)$', '', base_name)
        return base_name
    return name


def extract_figure_index(name: str) -> str:
    """Extract the trailing index (e.g., '_2') from a figure name, or return ''."""
    if not name:
        return ''
    index_match = re.search(r'_(\d+)$', name)
    if index_match:
        return index_match.group(1)
    return ''


# ================ Color Utils ================

def _hex_and_color_var(fill: dict) -> tuple[Optional[str], Optional[str]]:
    c = fill['color']
    r = int(round(c.get('r', 0) * 255))
    g = int(round(c.get('g', 0) * 255))
    b = int(round(c.get('b', 0) * 255))
    a = fill.get('opacity', c.get('a', 1))
    if a < 1:
        hex_color = '#{:02x}{:02x}{:02x}{:02x}'.format(r, g, b, int(a * 255))
    else:
        hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
    # Extract variable/style if present
    color_variable = None
    if 'boundVariables' in fill and 'color' in fill['boundVariables']:
        color_variable = fill['boundVariables']['color'].get('id')
    elif 'fillStyleId' in fill:
        color_variable = fill['fillStyleId']
    return hex_color, color_variable


def extract_color_info(node: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extracts the first visible solid fill color and its variable/style from a Figma node.
    Returns (hex_color, color_variable_id).
    """
    fills: Optional[list] = node.get('fills')
    if fills and isinstance(fills, list):
        for fill in fills:
            if fill.get('visible', True) and fill.get('type') == 'SOLID' and 'color' in fill:
                return _hex_and_color_var(fill)

    # Fallback: check for direct color field
    color = node.get('color')
    if color and isinstance(color, str):
        return color.lower(), None
    return None, None


# ================ Font Utils ================

def normalize_font_family(font_family: str) -> str:
    if not font_family:
        return ""
    return re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))


def normalize_font_weight(weight: Any) -> Optional[int]:
    """Normalize font weight to valid values (300, 400, 700)"""
    if weight is None:
        return 400
    return None


# ================ Block Utils ================

class BlockBuilder:
    """
    Build a block dictionary from an ExtractedBlock or dict and optional slide_config.
    This is the single source of truth for block dict construction.
    Adds figure_info and precompiled_image_info if relevant.
    Always includes both has_corner_radius (bool) and corner_radius (list of 4 ints).
    """
    def __init__(self, block: dict | ExtractedBlock, slide_config: Optional[dict] = None):
        self.block = block
        self.slide_config = slide_config
        self.block_dict: dict = {}

    def get(self, key: str) -> Optional[Any]:
        if isinstance(self.block, dict):
            return self.block.get(key, None)
        return getattr(self.block, key, None)

    def _init_block_dict(self) -> None:
        self.block_dict = {
            'id': self.get('id'),
            'name': self.get('name'),
            'figma_type': self.get('figma_type'),
            'sql_type': self.get('sql_type'),
            'dimensions': self.get('dimensions'),
            'styles': self.get('styles'),
            'is_target': self.get('is_target'),
            'needs_null_styles': self.get('sql_type') in BLOCKS.BLOCK_TYPES['null_style_types'],
            'needs_z_index': self.get('sql_type') in BLOCKS.BLOCK_TYPES['z_index_types'],
            # Always include both fields for clarity and downstream use
            'has_corner_radius': self.get('has_corner_radius') if self.get('has_corner_radius') is not None else False,
            'corner_radius': self.get('corner_radius') if self.get('corner_radius') is not None else [0, 0, 0, 0],
        }

    def _fill_words(self) -> None:
        text_content = self.get('text_content')
        # Use existing 'words' if present in dict, else recalculate
        if isinstance(self.block, dict) and self.block.get('words'):
            self.block_dict['words'] = self.block['words']
        else:
            self.block_dict['words'] = count_words(text_content)

    def _fill_by_sql_type(self, sql_type: str) -> None:
        if sql_type == 'background':
            self._fill_by_background()
        elif sql_type == 'figure':
            self._fill_by_figure()
        elif sql_type == 'image' and self.get('node_color'):
            self._fill_by_image()
        text_block_types = ['slideTitle', 'blockTitle', 'text', 'subTitle', 'number', 'email', 'date', 'name',
                            'percentage']
        if self.get('sql_type') in text_block_types and safe_in(self.get('sql_type'), self.slide_config):
            self._fill_by_types()

    def __fill_color_var(self) -> None:
        if self.get('node'):
            color_hex, color_var = extract_color_info(self.get('node'))
            if color_var:
                self.block_dict['color_variable'] = color_var

    def __get_colors_and_fonts(self) -> tuple[list, list]:
        all_colors = []
        all_fonts = []
        for color_hex, objects in self.slide_config[self.get('sql_type')].items():
            all_colors.extend([o.get('color') for o in objects if o.get('color')])
            all_fonts.extend([o.get('fontFamily') for o in objects if o.get('fontFamily')])

        return all_colors, all_fonts

    def _fill_by_background(self) -> None:
        color_found = False
        if safe_in('background', self.slide_config):
            for color_hex, background_objects in self.slide_config['background'].items():
                if background_objects:
                    background_obj = background_objects[0]
                    self.block_dict['color'] = background_obj.get('color')
                    self.block_dict['fontFamily'] = background_obj.get('fontFamily')
                    color_found = True
                    break
        if not color_found and self.get('node_color'):
            self.block_dict['color'] = self.get('node_color')
        self.__fill_color_var()

    def _fill_by_figure(self) -> None:
        clean_name = extract_base_figure_name(self.get('name'))
        self.block_dict['figureName'] = clean_name
        if self.get('node_color'):
            self.block_dict['color'] = self.get('node_color')
        elif safe_in('figure', self.slide_config):
            all_colors, all_fonts = self.__get_colors_and_fonts()
            if all_colors:
                self.block_dict['all_colors'] = list(set(all_colors))
            if all_fonts:
                self.block_dict['all_fonts'] = list(set(all_fonts))

            figure_index = extract_figure_index(clean_name)
            if figure_index:
                for color_hex, figure_objects in self.slide_config['figure'].items():
                    for figure_obj in figure_objects:
                        if figure_obj.get('figureName') == figure_index:
                            self.block_dict['color'] = figure_obj.get('color')
                            self.block_dict['fontFamily'] = figure_obj.get('fontFamily')
                            break
                    if 'color' in self.block_dict:
                        break

            if all_colors and 'color' not in self.block_dict:
                self.block_dict['color'] = all_colors[0]
            if all_fonts and 'fontFamily' not in self.block_dict:
                self.block_dict['fontFamily'] = all_fonts[0]
        self.__fill_color_var()

    def _fill_by_image(self) -> None:
        self.block_dict['color'] = self.get('node_color')
        self.__fill_color_var()

    def _fill_by_types(self) -> None:
        all_colors, all_fonts = self.__get_colors_and_fonts()

        if all_colors:
            self.block_dict['all_colors'] = list(set(all_colors))
        if all_fonts:
            self.block_dict['all_fonts'] = list(set(all_fonts))
        if all_colors and 'color' not in self.block_dict:
            self.block_dict['color'] = all_colors[0]
        if all_fonts and 'fontFamily' not in self.block_dict:
            self.block_dict['fontFamily'] = all_fonts[0]
        self.__fill_color_var()

    def _fill_info(self) -> None:
        # Always add figure_info and precompiled_image_info for consistency
        self.block_dict['figure_info'] = self.extract_figure_info()
        self.block_dict['precompiled_image_info'] = self.extract_precompiled_image_info()

    def extract_figure_info(self) -> Optional[dict]:
        """Extract and return figure_info dict for a figure block, or None if not a figure."""
        if self.get('sql_type') != 'figure':
            return None
        info = {
            'id': self.get('id'),
            'name': self.get('name'),
            'color': self.get('color'),
            'fontFamily': self.get('fontFamily'),
        }
        # Optionally enrich with slide_config if available
        if safe_in('figure', self.slide_config):
            # Try to find matching color/font info
            for color_hex, figure_objects in self.slide_config['figure'].items():
                for figure_obj in figure_objects:
                    if figure_obj.get('figureName') == info['name']:
                        info['color'] = figure_obj.get('color')
                        info['fontFamily'] = figure_obj.get('fontFamily')
                        break
        return info

    def extract_precompiled_image_info(self) -> Optional[dict]:
        """Extract and return precompiled_image_info dict for a precompiled image block, or None if not applicable."""
        if self.get('sql_type') != 'image':
            return None
        name = getattr(self.block, 'name', '')
        if not name.lower().startswith('image precompiled'):
            return None
        info = {
            'id': self.get('id'),
            'name': name,
            'color': self.get('color'),
        }
        # Optionally enrich with slide_config if available
        return info

    def build(self) -> dict:
        self._init_block_dict()
        self._fill_words()
        self._fill_by_sql_type(self.get('sql_type'))
        self._fill_info()
        return self.block_dict


# ================ Block Filter Utils ================

def _check_mode(mode: FilterMode, filter_config: FilterConfig, get: Callable) -> bool:
    if mode == FilterMode.ALL:
        return True
    if mode == FilterMode.SPECIFIC_SLIDES:
        slide_number = get('slide_number') or get('slideNumber')
        if slide_number is not None:
            return slide_number in getattr(filter_config, 'target_slides', [])
    if mode == FilterMode.SPECIFIC_BLOCKS:
        sql_type = get('sql_type')
        if sql_type is not None:
            return sql_type in getattr(filter_config, 'target_block_types', [])
    if mode == FilterMode.BY_TYPE:
        parent_container = get('parent_container')
        if parent_container is not None:
            return parent_container in getattr(filter_config, 'target_containers', [])
    return True


def should_include(node_or_block: dict | ExtractedBlock, filter_config) -> bool:
    """
    Centralized logic for whether a node/block should be included based on filter_config.
    Handles z-index, marker, visibility, and filter mode.
    Accepts either a Figma node (dict) or an ExtractedBlock/dict.
    """
    def get(key: str) -> Optional[Any]:
        if isinstance(node_or_block, dict):
            return node_or_block.get(key, None)
        return getattr(node_or_block, key, None)

    # Exclude hidden
    if getattr(filter_config, 'exclude_hidden', True) and get(TYPES.FIGMA_KEY_VISIBLE) is False:
        return False

    name = get(TYPES.FIGMA_KEY_NAME) or ''
    # Marker check
    marker = getattr(filter_config, 'ready_to_dev_marker', None)
    if marker:
        if marker.lower() not in name.lower():
            return False
    # Z-index requirement
    if getattr(filter_config, 'require_z_index', True):
        if 'z-index' not in name:
            return False
    # Filter mode logic
    mode = getattr(filter_config, 'mode', None)
    return _check_mode(mode, filter_config, get)
