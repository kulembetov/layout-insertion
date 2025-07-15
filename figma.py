"""
Complete Figma to SQL Generator Integration
Self-contained file with all necessary classes included.
Fully compatible with config.py specifications.
"""

import json
import os
import requests
import re
import argparse
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import config
import logging
import shutil

# Set up block logger dynamically based on output directory
block_logger = None
block_log_handler = None

def setup_block_logger(output_dir):
    global block_logger, block_log_handler
    if block_logger and block_log_handler:
        block_logger.removeHandler(block_log_handler)
    block_logger = logging.getLogger('block_processing')
    block_logger.setLevel(logging.INFO)
    log_path = os.path.join(output_dir, 'figma.log')
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    block_log_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    block_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    block_logger.addHandler(block_log_handler)

# ================ Constants and Mappings ================

FIGMA_CONFIG = {
    'TARGET_WIDTH': 1200,
    'TARGET_HEIGHT': 675,
    'OUTPUT_DIR': 'figma_extract',
    'OUTPUT_FILE': 'extracted_data'
}

# Valid font weights - ONLY these are allowed
VALID_FONT_WEIGHTS = [300, 400, 700]

# Z-index defaults from config
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

# Default dimensions from config
DEFAULT_DIMENSIONS = {
    'background': {'x': 0, 'y': 0, 'w': 1200, 'h': 675},
    'slideTitle': {'x': 37, 'y': 37, 'w': 1125, 'h': 85},
    'subTitle': {'x': 37, 'y': 250, 'w': 875, 'h': 65},
    'blockTitle': {'x': 37, 'y': 37, 'w': 575, 'h': 30},
    'text': {'x': 37, 'y': 37, 'w': 575, 'h': 85},
    'number': {'x': 77, 'y': 315, 'w': 320, 'h': 50},
    'default': {'x': 37, 'y': 230, 'w': 1125, 'h': 405},
}

# Default styles from config
DEFAULT_STYLES = {
    'slideTitle': {'text_vertical': 'top', 'text_horizontal': 'left', 'font_size': 50, 'weight': 700, 'text_transform': 'none'},
    'subTitle': {'text_vertical': 'top', 'text_horizontal': 'left', 'font_size': 25, 'weight': 400, 'text_transform': 'none'},
    'blockTitle': {'text_vertical': 'top', 'text_horizontal': 'left', 'font_size': 25, 'weight': 700, 'text_transform': 'none'},
    'text': {'text_vertical': 'top', 'text_horizontal': 'left', 'font_size': 20, 'weight': 400, 'text_transform': 'none'},
    'number': {'text_vertical': 'top', 'text_horizontal': 'center', 'font_size': 50, 'weight': 700, 'text_transform': 'none'},
    'default': {'text_vertical': 'top', 'text_horizontal': 'left', 'font_size': 20, 'weight': 400, 'text_transform': 'none'},
}

# Slide type detection patterns
SLIDE_TYPE_PATTERNS = {
    'title': ['hero', 'title', 'cover'],
    'table': ['table', 'grid'],
    'chart': ['chart', 'graph', 'data'],
    'infographics': ['infographic', 'infographik', 'visual'],
    'few_text': ['1cols', '2cols'],
    'optimal_text': ['3cols'],
    'many_text': ['4cols', '5cols', '6cols', '7cols', '8cols', '9cols', '10cols']
}

# ================ Data Classes and Enums ================

class FilterMode(Enum):
    ALL = "all"
    SPECIFIC_SLIDES = "specific_slides"
    SPECIFIC_BLOCKS = "specific_blocks"
    BY_TYPE = "by_type"

@dataclass
class FilterConfig:
    mode: FilterMode = FilterMode.ALL
    target_slides: List[int] = field(default_factory=list)
    target_block_types: List[str] = field(default_factory=list)
    target_containers: List[str] = field(default_factory=list)
    require_z_index: bool = True
    min_area: int = 0
    exclude_hidden: bool = True
    ready_to_dev_marker: Optional[str] = None  # marker for 'ready to dev' (e.g., '[ready]')

@dataclass
class ExtractedBlock:
    id: str
    figma_type: str
    sql_type: str
    name: str
    dimensions: Dict[str, int]
    styles: Dict[str, Any]
    slide_number: int
    parent_container: str
    is_target: bool = False
    has_corner_radius: bool = False
    corner_radius: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    text_content: str = None  # NEW: store actual text content for TEXT nodes

@dataclass
class ExtractedSlide:
    number: int
    container_name: str
    frame_name: str
    slide_type: str
    blocks: List[ExtractedBlock]
    frame_id: str
    dimensions: Dict[str, int]

# ================ Figma Extractor Class ================
class EnhancedFigmaExtractor:
    def __init__(self, file_id: str, token: str, filter_config: FilterConfig | None = None):
        """Initialize the Figma extractor with file ID, access token and optional filter config.
        
        Args:
            file_id: The Figma file ID to extract from
            token: Figma access token for authentication
            filter_config: Optional configuration for filtering extracted elements
        """
        self.file_id = file_id
        self.token = token
        self.filter_config = filter_config or FilterConfig()
        self.headers = {'X-Figma-Token': token}
        
    def round_to_nearest_five(self, value: float) -> int:
        """Round value to nearest 5"""
        return round(value / 5) * 5

    def extract_z_index(self, name: str) -> int:
        """Extract z-index from node name"""
        if 'z-index' in name:
            parts = name.split('z-index')
            if len(parts) > 1:
                after = parts[1].strip()
                match = re.findall(r'\d+', after)
                if match:
                    return int(match[0])
        return 0

    def has_z_index_in_name(self, name: str) -> bool:
        """Check if name contains z-index"""
        return 'z-index' in name

    def normalize_font_weight(self, weight: Any) -> int:
        """Normalize font weight to valid values (300, 400, 700)"""
        if weight is None:
            return 400
        
        try:
            weight_num = int(weight)
        except (ValueError, TypeError):
            return 400
        
        # Map font weights to nearest valid value
        if weight_num <= 350:
            return 300
        elif weight_num <= 550:
            return 400
        else:
            return 700

    def detect_block_type(self, node: Dict[str, Any]) -> Tuple[str, str]:
        """Detect block type from Figma node with enhanced pattern matching"""
        name = node.get('name', '').lower()
        node_type = node.get('type', '')
        
        # Remove z-index suffix for cleaner pattern matching
        clean_name = re.sub(r'\s*z-index.*$', '', name)
        
        # Check for explicit mappings first, but prioritize longer/more specific patterns
        # Sort patterns by length (descending) to match more specific patterns first
        sorted_patterns = sorted(config.FIGMA_TO_SQL_BLOCK_MAPPING.items(), 
                               key=lambda x: len(x[0]), reverse=True)
        
        for pattern, sql_type in sorted_patterns:
            if pattern in clean_name:
                print(f"Detected '{sql_type}' from pattern '{pattern}' in name '{clean_name}'")
                return pattern, sql_type
        
        # Infer from Figma node type with better heuristics
        if node_type == 'TEXT':
            # Look for title/heading indicators
            if any(keyword in clean_name for keyword in ['title', 'heading', 'header', 'h1', 'h2']):
                if any(keyword in clean_name for keyword in ['slide', 'main']):
                    return 'slideTitle', 'slideTitle'
                return 'blockTitle', 'blockTitle'
            elif any(keyword in clean_name for keyword in ['subtitle', 'sub', 'subheading']):
                return 'subTitle', 'subTitle'
            elif any(keyword in clean_name for keyword in ['number', 'num', 'count']):
                return 'number', 'number'
            elif any(keyword in clean_name for keyword in ['email', '@', 'mail']):
                return 'email', 'email'
            elif any(keyword in clean_name for keyword in ['date', 'time', 'year', 'month']):
                return 'date', 'date'
            elif any(keyword in clean_name for keyword in ['name', 'author', 'person']):
                return 'name', 'name'
            elif any(keyword in clean_name for keyword in ['percent', '%', 'percentage']):
                return 'percentage', 'percentage'
            return 'text', 'text'
            
        elif node_type == 'RECTANGLE':
            # Priority order: background > icon > image > figure
            # This ensures "image_bottom background" is detected as background, not image
            if any(keyword in clean_name for keyword in ['background', 'bg', 'backdrop']):
                print(f"Detected 'background' from heuristic keywords in '{clean_name}'")
                return 'background', 'background'
            elif any(keyword in clean_name for keyword in ['icon', 'symbol']):
                print(f"Detected 'icon' from heuristic keywords in '{clean_name}'")
                return 'icon', 'icon'
            elif any(keyword in clean_name for keyword in ['image', 'img', 'photo', 'picture']):
                print(f"Detected 'image' from heuristic keywords in '{clean_name}'")
                return 'image', 'image'
            print(f"Defaulting to 'figure' for RECTANGLE: '{clean_name}'")
            return 'figure', 'figure'
            
        elif node_type in ['FRAME', 'GROUP']:
            if any(keyword in clean_name for keyword in ['table', 'grid', 'data']):
                return 'table', 'table'
            elif any(keyword in clean_name for keyword in ['chart', 'graph']):
                return 'table', 'table'  # Charts are treated as tables
            elif any(keyword in clean_name for keyword in ['infographic', 'infographik', 'visual']):
                return 'infographik', 'infographik'
            elif any(keyword in clean_name for keyword in ['watermark', 'mark']):
                return 'watermark', 'watermark'
            return 'figure', 'figure'
        
        # Default fallback
        print(f"Using default 'text' type for node: {name} (type: {node_type}, clean_name: {clean_name})")
        return 'text', 'text'

    def extract_text_styles(self, node: Dict[str, Any], sql_type: str) -> Dict[str, Any]:
        """Extract text styling information with config defaults (no color)."""
        defaults = config.DEFAULT_STYLES.get(sql_type, config.DEFAULT_STYLES['default'])
        styles = {
            'textVertical': defaults['text_vertical'],
            'textHorizontal': defaults['text_horizontal'],
            'fontSize': defaults['font_size'],
            'weight': defaults['weight'],
            'textTransform': defaults['text_transform']
        }
        style = node.get('style', {})
        if style:
            # Prefer Figma's actual values if present
            text_align_vertical = style.get('textAlignVertical', '').lower()
            if text_align_vertical in ['top', 'middle', 'bottom']:
                styles['textVertical'] = text_align_vertical
            elif text_align_vertical == 'center':
                styles['textVertical'] = 'middle'
            # Figma's textAlignHorizontal: 'LEFT', 'CENTER', 'RIGHT' (case-insensitive)
            text_align_horizontal = style.get('textAlignHorizontal', '').lower()
            if text_align_horizontal in ['left', 'center', 'right']:
                styles['textHorizontal'] = text_align_horizontal
            if 'fontSize' in style:
                styles['fontSize'] = round(style['fontSize'])
            if 'fontWeight' in style:
                styles['weight'] = self.normalize_font_weight(style['fontWeight'])
        return styles

    def extract_corner_radius(self, node: Dict[str, Any]) -> Tuple[bool, List[int]]:
        """Extract corner radius information"""
        corner_radius = [0, 0, 0, 0]  # Default: all corners 0
        has_corner_radius = False
        
        # Check for cornerRadius property
        if 'cornerRadius' in node:
            radius = node['cornerRadius']
            if isinstance(radius, (int, float)) and radius > 0:
                corner_radius = [int(radius)] * 4
                has_corner_radius = True
        
        # Check for individual corner radii
        if 'rectangleCornerRadii' in node:
            radii = node['rectangleCornerRadii']
            if isinstance(radii, list) and len(radii) == 4:
                corner_radius = [int(r) for r in radii]
                has_corner_radius = any(r > 0 for r in corner_radius)
        
        return has_corner_radius, corner_radius

    def is_target_frame(self, node: Dict[str, Any]) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker"""
        if not node.get('absoluteBoundingBox'):
            return False
        # Check for 'ready to dev' marker if set
        marker = getattr(self.filter_config, 'ready_to_dev_marker', None)
        if marker:
            name = node.get('name', '').lower()
            if marker.lower() not in name:
                return False
        # Check z-index requirement
        if self.filter_config.require_z_index and not self.has_z_index_in_name(node.get('name', '')):
            return False
        abs_box = node['absoluteBoundingBox']
        # Check dimensions
        width_match = abs(abs_box['width'] - FIGMA_CONFIG['TARGET_WIDTH']) < 1
        height_match = abs(abs_box['height'] - FIGMA_CONFIG['TARGET_HEIGHT']) < 1
        if not (width_match and height_match):
            return False
        # Check minimum area
        area = abs_box['width'] * abs_box['height']
        if area < self.filter_config.min_area:
            return False
        return True

    def should_include_block(self, block: ExtractedBlock) -> bool:
        """Check if block should be included based on filter"""
        if self.filter_config.mode == FilterMode.ALL:
            return True
        
        if self.filter_config.mode == FilterMode.SPECIFIC_SLIDES:
            return block.slide_number in self.filter_config.target_slides
        
        if self.filter_config.mode == FilterMode.SPECIFIC_BLOCKS:
            return block.sql_type in self.filter_config.target_block_types
        
        if self.filter_config.mode == FilterMode.BY_TYPE:
            return block.parent_container in self.filter_config.target_containers
        
        return True

    def detect_slide_type(self, container_name: str, slide_number: int) -> str:
        """Detect slide type using only config.py as the source of truth."""
        # Use config mapping for container name to slide number
        key = container_name.strip().lower()
        number = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
        # Use config mapping for slide number to type
        return config.SLIDE_NUMBER_TO_TYPE.get(number, 'classic')

    def get_slide_number(self, parent_name: str) -> int:
        """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
        key = parent_name.strip().lower()
        return config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)

    def extract_color_from_fills(self, node: dict) -> tuple[str | None, str | None]:
        fills = node.get('fills')
        color_hex = None
        color_variable = None
        if not fills or not isinstance(fills, list):
            return None, None
        for fill in fills:
            if fill.get('visible', True) and fill.get('type') == 'SOLID':
                # Extract hex color if present
                if 'color' in fill:
                    c = fill['color']
                    r = int(round(c.get('r', 0) * 255))
                    g = int(round(c.get('g', 0) * 255))
                    b = int(round(c.get('b', 0) * 255))
                    a = fill.get('opacity', c.get('a', 1))
                    if a < 1:
                        color_hex = '#{:02x}{:02x}{:02x}{:02x}'.format(r, g, b, int(a * 255))
                    else:
                        color_hex = '#{:02x}{:02x}{:02x}'.format(r, g, b)
                # Extract variable/style if present
                if 'boundVariables' in fill and 'color' in fill['boundVariables']:
                    color_variable = fill['boundVariables']['color'].get('id')
                elif 'fillStyleId' in fill:
                    color_variable = fill['fillStyleId']
        return color_hex, color_variable

    def collect_enhanced_blocks(self, node: Dict[str, Any], frame_origin: Dict[str, int], 
                              slide_number: int, parent_container: str) -> List[ExtractedBlock]:
        """Collect blocks with enhanced information, including text content for TEXT nodes. Now supports 'ready to dev' marker."""
        blocks = []
        if not node.get('absoluteBoundingBox'):
            return blocks
        # Skip hidden nodes if exclude_hidden is enabled
        if self.filter_config.exclude_hidden and node.get('visible') is False:
            return blocks
        # Check for 'ready to dev' marker if set (for blocks)
        marker = getattr(self.filter_config, 'ready_to_dev_marker', None)
        if marker:
            name = node.get('name', '').lower()
            if marker.lower() not in name:
                return blocks
        name = node.get('name', '')
        has_z = self.has_z_index_in_name(name)
        # Only process nodes with z-index in the name
        if has_z:
            figma_type, sql_type = self.detect_block_type(node)
            # Validate sql_type is in our allowed list
            if sql_type not in config.BLOCK_TYPES['block_layout_type_options']:
                print(f"Invalid block type '{sql_type}', defaulting to 'text'")
                sql_type = 'text'
            abs_box = node['absoluteBoundingBox']
            left = abs_box['x'] - frame_origin['x']
            top = abs_box['y'] - frame_origin['y']
            dimensions = {
                'x': self.round_to_nearest_five(left),
                'y': self.round_to_nearest_five(top),
                'w': self.round_to_nearest_five(abs_box['width']),
                'h': self.round_to_nearest_five(abs_box['height'])
            }
            # Skip full-slide images unless 'precompiled' is in the name, but always include background blocks
            name_lower = name.lower()
            is_precompiled = 'precompiled' in name_lower
            should_skip = (
                sql_type == 'image' and  # Only skip images, not backgrounds
                dimensions['x'] == 0 and
                dimensions['y'] == 0 and
                dimensions['w'] == 1200 and
                dimensions['h'] == 675 and
                not is_precompiled
            )
            if should_skip:
                print(f"Skipping {sql_type} block {name} (full image 1200x675)")
            else:
                styles = self.extract_text_styles(node, sql_type)
                z_index = self.extract_z_index(name)
                if z_index == 0:
                    z_index = config.Z_INDEX_DEFAULTS.get(sql_type, config.Z_INDEX_DEFAULTS['default'])
                styles['zIndex'] = z_index
                has_corner_radius = False
                corner_radius = [0, 0, 0, 0]
                text_content = None
                if sql_type == 'text' and node.get('type') == 'TEXT':
                    text_content = node.get('characters', None)
                
                # Extract color information for background and other relevant blocks
                node_color = None
                if sql_type in config.BLOCK_TYPES['null_style_types']:
                    node_color, _ = self.extract_color_from_fills(node)
                
                block = ExtractedBlock(
                    id=node['id'],
                    figma_type=figma_type,
                    sql_type=sql_type,
                    name=name,
                    dimensions=dimensions,
                    styles=styles,
                    slide_number=slide_number,
                    parent_container=parent_container,
                    is_target=True,
                    has_corner_radius=has_corner_radius,
                    corner_radius=corner_radius,
                    text_content=text_content  # Pass text content
                )
                # Store the extracted color for later use
                block.node_color = node_color
                if self.should_include_block(block):
                    blocks.append(block)
                    print(f"Added {sql_type} block: {name}")
                    # Log block details
                    color_info = f" | Color: {node_color}" if node_color else ""
                    block_logger.info(
                        f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{color_info}"
                    )
        # Recursively process children (skip children of hidden nodes)
        if node.get('children') and not (self.filter_config.exclude_hidden and node.get('visible') is False):
            for child in node['children']:
                blocks.extend(self.collect_enhanced_blocks(child, frame_origin, slide_number, parent_container))
        return blocks

    def _extract_slide_config(self, slide_node):
        """Extract slideConfig from the hidden slideColors table in the slide node, including color and fontFamily for each color layer. For 'figure', each color group is a dict with 'index_to_font_fill' mapping index (1,2,3) to color/fontFamily.
        
        Note: This method specifically processes the hidden 'slideColors' table regardless of visibility,
        as it's intentionally hidden but contains necessary configuration data.
        Now also returns a set of all color hexes (presentation palette colors) found in the slideColors table."""
        config_dict = {}
        palette_colors = set()
        if not slide_node or not slide_node.get('children'):
            return config_dict, []
        for child in slide_node['children']:
            if child.get('name') == 'slideColors':
                if block_logger:
                    block_logger.info(f"[slideColors] Found slideColors table in slide")
                for block in child.get('children', []):
                    block_type = block.get('name')
                    if block_logger:
                        block_logger.info(f"[slideColors] Processing block type: {block_type}")
                    block_colors = {}
                    for color_group in block.get('children', []):
                        color_hex = color_group.get('name')
                        if color_hex:
                            color_hex = color_hex.lower()  # Ensure lowercase
                            palette_colors.add(color_hex)
                        if block_logger:
                            block_logger.info(f"[slideColors] Processing color group: {color_hex}")
                        block_objs = []
                        for text_child in color_group.get('children', []):
                            if text_child.get('type') == 'TEXT':
                                obj = {}
                                color_val, _ = self.extract_color_from_fills(text_child)
                                obj['color'] = color_val  # Use 'color' instead of 'fill'
                                font_family = None
                                if 'style' in text_child and 'fontFamily' in text_child['style']:
                                    font_family = text_child['style']['fontFamily']
                                if font_family:
                                    # Normalize to snake_case
                                    font_family = re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))
                                obj['fontFamily'] = font_family
                                if block_type == 'figure':
                                    idx = text_child.get('name', '').strip()
                                    obj['figureName'] = idx
                                    if block_logger:
                                        block_logger.info(f"[slideColors] Found figure in {color_hex}: name='{idx}', color={color_val}, font={font_family}")
                                block_objs.append(obj)
                        block_colors[color_hex] = block_objs
                    config_dict[block_type] = block_colors
        return config_dict, sorted(palette_colors)

    def _update_figure_config_with_names(self, slide_config, blocks):
        import re
        # Collect all figure blocks with their info
        figure_blocks_info = []
        for block in blocks:
            if block.sql_type == 'figure':
                name_match = re.search(r'\(([^)]+)\)', block.name)
                if name_match:
                    base_name = name_match.group(1)
                    figure_blocks_info.append({
                        'base_name': base_name,
                        'block': block
                    })
                    if block_logger:
                        block_logger.info(f"[figureBlocks] Found figure block: '{block.name}' -> base_name: '{base_name}'")
        new_figure_config = {}
        for color_hex, obj_list in slide_config['figure'].items():
            figure_objects = []
            for fig in figure_blocks_info:
                # Extract index from figure name (e.g., "iconOvalOutlineRfs_2" -> "2")
                base_name = fig['base_name']
                clean_figure_name = re.sub(r'_(\d+)$', '', base_name)  # Remove suffix for storage
                index_match = re.search(r'_(\d+)$', base_name)
                
                # Find the matching object by index in slideColors
                match_obj = None
                if index_match:
                    figure_index = index_match.group(1)  # Extract "2" from "iconOvalOutlineRfs_2"
                    for obj in obj_list:
                        if obj.get('figureName') == figure_index:  # Look for "2" in slideColors
                            match_obj = obj
                            break
                    
                    if match_obj:
                        font_family = match_obj.get('fontFamily')
                        if font_family:
                            # Normalize to snake_case
                            font_family = re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))
                        fill = match_obj.get('color')
                        if block_logger:
                            block_logger.info(f"[figureConfig] MATCHED: color {color_hex}, figure '{base_name}' using index '{figure_index}' -> color: {fill}, font: {font_family}")
                    else:
                        font_family = None
                        fill = None
                        if block_logger:
                            available_indices = [obj.get('figureName', 'UNNAMED') for obj in obj_list]
                            block_logger.info(f"[figureConfig] NOT FOUND: color {color_hex}, figure '{base_name}' looking for index '{figure_index}' in slideColors, available: {available_indices}")
                else:
                    # No index found in figure name
                    font_family = None
                    fill = None
                    if block_logger:
                        block_logger.info(f"[figureConfig] NO INDEX: figure '{base_name}' has no index suffix")
                
                figure_obj = {
                    "color": fill,
                    "fontFamily": font_family,
                    "figureName": clean_figure_name  # Store base name without suffix
                }
                figure_objects.append(figure_obj)
            new_figure_config[color_hex] = figure_objects
        slide_config['figure'] = new_figure_config
        
        # Summary logging
        if block_logger:
            block_logger.info(f"[figureConfig] SUMMARY: Processed {len(figure_blocks_info)} figure blocks")
            for fig_info in figure_blocks_info:
                clean_name = re.sub(r'_(\d+)$', '', fig_info['base_name'])
                block_logger.info(f"[figureConfig] Block '{fig_info['base_name']}' -> looking for '{clean_name}' in slideColors")

    def traverse_and_extract(self, node: Dict[str, Any], parent_name: str = "") -> List[ExtractedSlide]:
        """Enhanced traversal with filtering"""
        slides = []
        
        if self.is_target_frame(node):
            print(f"Found target frame: \"{node['name']}\"")
            print(f"Parent container: \"{parent_name}\"")

            frame_origin = {
                'x': node['absoluteBoundingBox']['x'],
                'y': node['absoluteBoundingBox']['y']
            }

            slide_number = self.get_slide_number(parent_name)
            
            # Skip if not in target slides (when filtering by specific slides)
            if (self.filter_config.mode == FilterMode.SPECIFIC_SLIDES and 
                slide_number not in self.filter_config.target_slides):
                return slides

            slide_type = self.detect_slide_type(parent_name, slide_number)
            
            blocks = self.collect_enhanced_blocks(
                node, frame_origin, slide_number, parent_name
            )
            
            if blocks or self.filter_config.mode == FilterMode.ALL:
                slide = ExtractedSlide(
                    number=slide_number,
                    container_name=parent_name,
                    frame_name=node['name'],
                    slide_type=slide_type,
                    blocks=blocks,
                    frame_id=node['id'],
                    dimensions={
                        'w': FIGMA_CONFIG['TARGET_WIDTH'],
                        'h': FIGMA_CONFIG['TARGET_HEIGHT']
                    }
                )
                # Attach the original node for color extraction
                slide._figma_node = node
                slides.append(slide)
                print(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")
            
            return slides

        # Continue traversing children
        if node.get('children'):
            for child in node['children']:
                child_slides = self.traverse_and_extract(child, node['name'])
                slides.extend(child_slides)
        
        return slides

    def extract_data(self) -> Dict[str, Any]:
        """Main extraction method"""
        try:
            response = requests.get(
                f'https://api.figma.com/v1/files/{self.file_id}',
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            pages = data['document']['children']
            all_slides = []

            for page in pages:
                print(f"\nProcessing page: {page.get('name', 'Unnamed')}")
                page_slides = self.traverse_and_extract(page)
                all_slides.extend(page_slides)

            # Generate summary
            summary = {
                'total_slides': len(all_slides),
                'total_blocks': sum(len(slide.blocks) for slide in all_slides),
                'slide_types': {},
                'block_types': {},
                'slide_distribution': {}
            }
            
            for slide in all_slides:
                slide_type = slide.slide_type
                summary['slide_types'][slide_type] = summary['slide_types'].get(slide_type, 0) + 1
                summary['slide_distribution'][slide.number] = slide.container_name
                
                for block in slide.blocks:
                    block_type = block.sql_type
                    summary['block_types'][block_type] = summary['block_types'].get(block_type, 0) + 1

            return {
                'metadata': {
                    'file_id': self.file_id,
                    'figma_config': FIGMA_CONFIG,
                    'extraction_summary': summary,
                    'filter_config': {
                        'mode': self.filter_config.mode.value,
                        'target_slides': self.filter_config.target_slides,
                        'target_block_types': self.filter_config.target_block_types,
                        'target_containers': self.filter_config.target_containers
                    },
                    'sql_generator_compatibility': {
                        'valid_block_types': config.BLOCK_TYPES['block_layout_type_options'],
                        'valid_font_weights': VALID_FONT_WEIGHTS,
                        'slide_layout_types': config.SLIDE_LAYOUT_TYPES
                    }
                },
                'slides': [self._slide_to_dict(slide) for slide in all_slides]
            }

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return {
                'metadata': {
                    'file_id': self.file_id,
                    'error': str(e)
                },
                'slides': []
            }
        except Exception as e:
            print(f"Error: {e}")
            return {
                'metadata': {
                    'file_id': self.file_id, 
                    'error': str(e)
                },
                'slides': []
            }

    def _slide_to_dict(self, slide: ExtractedSlide) -> Dict[str, Any]:
        """Convert slide object to dictionary, using only the text block with the most text for sentence count. Remove debug logs. Add slideColors extraction."""
        # Find the text block with the longest text_content
        max_text_block = None
        max_len = 0
        for block in slide.blocks:
            if block.sql_type == 'text':
                text_content = getattr(block, 'text_content', None)
                if text_content and len(text_content) > max_len:
                    max_text_block = block
                    max_len = len(text_content)
        sentence_count = 0
        if max_text_block:
            text_content = getattr(max_text_block, 'text_content', None)
            split_result = [s for s in re.split(r'[.!?]', text_content)]
            n = len([s for s in split_result if s.strip()])
            if n == 0:
                n = 1
            sentence_count = n
        if sentence_count == 0:
            sentence_count = 1
        # Extract slideConfig and palette colors if available
        slide_config = {}
        presentation_palette_colors = []
        figma_node = getattr(slide, '_figma_node', None)
        if figma_node:
            slide_config, presentation_palette_colors = self._extract_slide_config(figma_node)
            # Build mapping from figure numbers to actual figure names and update slideConfig
            if 'figure' in slide_config:
                self._update_figure_config_with_names(slide_config, slide.blocks)
        return {
            'slide_number': slide.number,
            'container_name': slide.container_name,
            'frame_name': slide.frame_name,
            'slide_type': slide.slide_type,
            'sentences': sentence_count,
            'frame_id': slide.frame_id,
            'dimensions': slide.dimensions,
            'folder_name': config.SLIDE_NUMBER_TO_FOLDER.get(slide.number, 'other'),
            'blocks': [self._block_to_dict(block, slide_config) for block in slide.blocks],
            'block_count': len(slide.blocks),
            'slideConfig': slide_config,
            'presentationPaletteColors': presentation_palette_colors
        }

    def _block_to_dict(self, block: ExtractedBlock, slide_config=None) -> Dict[str, Any]:
        block_dict = {
            'id': block.id,
            'name': block.name,
            'figma_type': block.figma_type,
            'sql_type': block.sql_type,
            'dimensions': block.dimensions,
            'styles': block.styles,  # <-- Add styles at the top level
            'is_target': block.is_target,
            'needs_null_styles': block.sql_type in config.BLOCK_TYPES['null_style_types'],
            'needs_z_index': block.sql_type in config.BLOCK_TYPES['z_index_types'],
            'corner_radius': block.corner_radius if block.corner_radius is not None else None,
        }
        
        # Handle background blocks with color extraction
        if block.sql_type == 'background':
            # First try to get color from slideConfig, then fallback to node color
            color_found = False
            if slide_config and 'background' in slide_config:
                for color_hex, background_objects in slide_config['background'].items():
                    if background_objects:  # If there are objects for this color
                        background_obj = background_objects[0]  # Take the first (should be only one for background)
                        block_dict['color'] = background_obj.get('color')
                        block_dict['fontFamily'] = background_obj.get('fontFamily')
                        color_found = True
                        break  # Use the first color found
            
            # Fallback to direct node color extraction if not found in slideConfig
            if not color_found and hasattr(block, 'node_color') and block.node_color:
                block_dict['color'] = block.node_color
        
        # Handle figure blocks with color extraction - prioritize direct node color
        elif block.sql_type == 'figure':
            import re
            clean_name = block.name  # Default to full block name
            name_match = re.search(r'\(([^)]+)\)', block.name)
            if name_match:
                clean_name = name_match.group(1)
                block_dict['figureName'] = clean_name
            
            # Primary: Use direct node color extraction
            if hasattr(block, 'node_color') and block.node_color:
                block_dict['color'] = block.node_color
                if block_logger:
                    block_logger.info(f"[figureColor] Using direct node color for '{clean_name}': {block.node_color}")
            
            # Secondary: Try slideConfig (though it seems to only contain indices)
            elif slide_config and 'figure' in slide_config and name_match:
                # Extract figure index from name (e.g., "iconOvalOutlineRfs_2" -> "2")
                index_match = re.search(r'_(\d+)$', clean_name)
                if index_match:
                    figure_index = index_match.group(1)
                    
                    # Look for this index in slideColors
                    for color_hex, figure_objects in slide_config['figure'].items():
                        for figure_obj in figure_objects:
                            if figure_obj.get('figureName') == figure_index:
                                block_dict['color'] = figure_obj.get('color')
                                block_dict['fontFamily'] = figure_obj.get('fontFamily')
                                if block_logger:
                                    block_logger.info(f"[figureColor] Using slideConfig index match for '{clean_name}' index '{figure_index}': color={figure_obj.get('color')}")
                                break
                        if 'color' in block_dict:
                            break
        
        # Handle image blocks with color extraction
        elif block.sql_type == 'image' and hasattr(block, 'node_color') and block.node_color:
            block_dict['color'] = block.node_color
        
        return block_dict

    def save_results(self, data: Dict[str, Any], output_file: str | None) -> str:
        """Save extracted data to file"""
        if not data:
            return ""
        if not os.path.exists(FIGMA_CONFIG['OUTPUT_DIR']):
            os.makedirs(FIGMA_CONFIG['OUTPUT_DIR'])

        if not output_file:
            output_file = f"{FIGMA_CONFIG['OUTPUT_DIR']}/{FIGMA_CONFIG['OUTPUT_FILE']}_config_compatible.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nEnhanced data saved: {output_file}")
        
        # Print detailed summary
        metadata = data.get('metadata', {})
        summary = metadata.get('extraction_summary', {})
        print(f"\nEXTRACTION SUMMARY:")
        print(f"   Total slides: {summary.get('total_slides', 0)}")
        print(f"   Total blocks: {summary.get('total_blocks', 0)}")
        print(f"   Slide types: {summary.get('slide_types', {})}")
        print(f"   Block types: {summary.get('block_types', {})}")
        print(f"   Distribution: {summary.get('slide_distribution', {})}")
        
        return output_file

# ================ Integration Classes ================

class FigmaToSQLIntegrator:
    """Integrates Figma extraction with SQL generation"""
    
    def __init__(self, figma_file_id: str, figma_token: str):
        self.figma_file_id = figma_file_id
        self.figma_token = figma_token
        
    def extract_specific_slides(self, slide_numbers: List[int]) -> Dict[str, Any]:
        """Extract specific slides from Figma"""
        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_SLIDES,
            target_slides=slide_numbers,
            require_z_index=True
        )
        
        extractor = EnhancedFigmaExtractor(
            self.figma_file_id, 
            self.figma_token, 
            filter_config
        )
        
        return extractor.extract_data()
    
    def extract_by_block_types(self, block_types: List[str]) -> Dict[str, Any]:
        """Extract slides containing specific block types"""
        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_BLOCKS,
            target_block_types=block_types
        )
        
        extractor = EnhancedFigmaExtractor(
            self.figma_file_id, 
            self.figma_token, 
            filter_config
        )
        
        return extractor.extract_data()
    
    def extract_by_containers(self, container_names: List[str]) -> Dict[str, Any]:
        """Extract slides from specific containers"""
        filter_config = FilterConfig(
            mode=FilterMode.BY_TYPE,
            target_containers=container_names
        )
        
        extractor = EnhancedFigmaExtractor(
            self.figma_file_id, 
            self.figma_token, 
            filter_config
        )
        
        return extractor.extract_data()
    
    def prepare_sql_generator_input(self, figma_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert Figma data to format suitable for SQL Generator with config compatibility. Now includes slideConfig and presentationPaletteColors for each slide."""
        sql_input = []
        for slide in figma_data.get('slides', []):
            is_last = slide['slide_number'] == -1
            presentation_layout_id = config.DEFAULT_VALUES.get('presentation_layout_id')
            slide_input = {
                'slide_layout_name': slide['frame_name'],
                'slide_layout_number': slide['slide_number'],
                'slide_type': slide['slide_type'],
                'presentation_layout_id': presentation_layout_id,
                'is_last': is_last,
                'folder_name': slide.get('folder_name', 'other'),
                'blocks': [],
                'auto_blocks': self._get_auto_blocks_for_slide(slide, is_last),
                'sql_config': {
                    'needs_background': config.AUTO_BLOCKS.get('add_background', True),
                    'needs_watermark': config.AUTO_BLOCKS.get('add_watermark', False) or is_last,
                    'default_color': config.DEFAULT_COLOR,
                    'color_settings_id': config.DEFAULT_COLOR_SETTINGS_ID
                },
                # Add slideConfig and presentationPaletteColors from the Figma slide if present
                'slideConfig': slide.get('slideConfig', {}),
                'presentationPaletteColors': slide.get('presentationPaletteColors', [])
            }
            for block in slide['blocks']:
                styles = dict(block['styles']) if block.get('styles') else {}
                block_input = {
                    'id': block['id'],
                    'type': block['sql_type'],
                    'name': block['name'],
                    'dimensions': block['dimensions'],
                    'styles': styles,
                    'z_index': styles.get('z_index'),
                    'needs_null_styles': block['needs_null_styles'],
                    'needs_z_index': block['needs_z_index'],
                    'corner_radius': block.get('corner_radius'),
                    'sql_ready': True
                }
                slide_input['blocks'].append(block_input)
            sql_input.append(slide_input)
        return sql_input
    
    def _get_auto_blocks_for_slide(self, slide: Dict[str, Any], is_last: bool) -> Dict[str, Any]:
        """Get automatic blocks configuration for a slide"""
        auto_blocks = {}
        
        # Background block
        if config.AUTO_BLOCKS.get('add_background', True):
            auto_blocks['background'] = {
                'type': 'background',
                'color': config.AUTO_BLOCKS['background']['color'],
                'dimensions': config.AUTO_BLOCKS['background']['dimensions'],
                'z_index': config.AUTO_BLOCKS['background']['z_index']
            }
        
        # Watermark blocks
        if is_last:
            auto_blocks['watermark'] = {
                'type': 'watermark',
                'dimensions': config.AUTO_BLOCKS['last_slide']['watermark1']['dimensions'],
                'z_index': config.Z_INDEX_DEFAULTS['watermark']
            }
        elif config.AUTO_BLOCKS.get('add_watermark', False):
            auto_blocks['watermark'] = {
                'type': 'watermark',
                'dimensions': config.AUTO_BLOCKS['watermark']['dimensions'],
                'z_index': config.Z_INDEX_DEFAULTS['watermark']
            }
        
        return auto_blocks
    
    def _convert_styles_for_sql(self, figma_styles: Dict[str, Any], block_type: str) -> Dict[str, Any]:
        """Convert Figma styles to SQL Generator format with config defaults"""
        # Use config defaults as base
        defaults = config.DEFAULT_STYLES.get(block_type, config.DEFAULT_STYLES['default'])
        
        # Ensure font weight is valid (300, 400, 700)
        weight = figma_styles.get('weight', defaults['weight'])
        if weight not in [300, 400, 700]:
            if weight <= 350:
                weight = 300
            elif weight <= 550:
                weight = 400
            else:
                weight = 700
        
        return {
            'textVertical': figma_styles.get('textVertical', defaults['text_vertical']),
            'textHorizontal': figma_styles.get('textHorizontal', defaults['text_horizontal']),
            'fontSize': figma_styles.get('fontSize', defaults['font_size']),
            'weight': weight,
            'textTransform': figma_styles.get('textTransform', defaults['text_transform'])
        }
    
    def generate_sql_for_slides(self, slide_numbers: List[int], output_dir: str = "sql_output"):
        """Complete pipeline: extract from Figma and generate SQL with config compatibility"""
        print(f"Extracting slides {slide_numbers} from Figma...")
        # Remove output directory if it exists
        if os.path.exists(output_dir):
            print(f"Removing existing output directory: {output_dir}")
            shutil.rmtree(output_dir)
            print(f"Removed output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
        # Set up block logger in the output directory
        setup_block_logger(output_dir)
        # Extract from Figma
        figma_data = self.extract_specific_slides(slide_numbers)
        if not figma_data:
            print("Failed to extract data from Figma")
            return
        # Save extracted data
        with open(f"{output_dir}/figma_extract.json", 'w') as f:
            json.dump(figma_data, f, indent=2)
        # Prepare for SQL Generator
        sql_input = self.prepare_sql_generator_input(figma_data)
        # Save SQL input format
        with open(f"{output_dir}/sql_generator_input.json", 'w') as f:
            json.dump(sql_input, f, indent=2)
        # Generate ready-to-use SQL files for each slide
        self._generate_sql_files(sql_input, output_dir)
        print(f"\nProcessing complete!")
        print(f"   Extracted {len(figma_data.get('slides', []))} slides")
        print(f"   Generated {len(sql_input)} SQL-ready configurations")
        print(f"   Files saved to {output_dir}/")
        # Generate instructions for SQL Generator
        self._generate_sql_instructions(sql_input, output_dir)
    
    def _generate_sql_files(self, sql_input: List[Dict[str, Any]], output_dir: str):
        """Generate individual SQL files for each slide"""
        sql_dir = f"{output_dir}/sql_files"
        os.makedirs(sql_dir, exist_ok=True)
        
        for i, slide in enumerate(sql_input):
            sql_content = self._create_sql_for_slide(slide)
            filename = f"slide_{slide['slide_layout_number']:02d}_{slide['slide_layout_name']}.sql"
            
            with open(f"{sql_dir}/{filename}", 'w') as f:
                f.write(sql_content)
            
            print(f"   Generated SQL: {filename}")
    
    def _create_sql_for_slide(self, slide: Dict[str, Any]) -> str:
        """Create SQL content for a single slide using config templates"""
        lines = []
        lines.append(f"-- Slide {slide['slide_layout_number']}: {slide['slide_layout_name']}")
        lines.append(f"-- Type: {slide['slide_type']}")
        lines.append(f"-- Blocks: {len(slide['blocks'])}")
        lines.append(f"-- Generated from Figma extraction")
        lines.append("")
        
        # Add configuration comments
        lines.append("-- CONFIGURATION FOR SQL GENERATOR:")
        lines.append(f"-- Slide Layout Name: {slide['slide_layout_name']}")
        lines.append(f"-- Slide Layout Number: {slide['slide_layout_number']}")
        lines.append(f"-- Slide Type: {slide['slide_type']}")
        lines.append(f"-- Is Last: {slide['is_last']}")
        lines.append(f"-- Presentation Layout ID: {slide['presentation_layout_id']}")
        lines.append("")
        
        # Add auto blocks info
        if slide.get('auto_blocks'):
            lines.append("-- AUTO BLOCKS:")
            for block_name, block_config in slide['auto_blocks'].items():
                lines.append(f"--   {block_name}: {block_config}")
            lines.append("")
        
        # Add blocks info
        lines.append("-- BLOCKS TO CREATE:")
        for i, block in enumerate(slide['blocks']):
            lines.append(f"-- Block {i+1}: {block['type']}")
            lines.append(f"--   Name: {block['name']}")
            lines.append(f"--   Dimensions: {block['dimensions']}")
            lines.append(f"--   Z-Index: {block['z_index']}")
            lines.append(f"--   Styles: {block['styles']}")
            if block.get('corner_radius'):
                lines.append(f"--   Corner Radius: {block['corner_radius']}")
            lines.append("")
        
        lines.append("-- Run the SQL Generator with these parameters to create the actual SQL inserts")
        
        return '\n'.join(lines)
    
    def _generate_sql_instructions(self, sql_input: List[Dict[str, Any]], output_dir: str):
        """Generate comprehensive instructions for using with SQL Generator"""
        instructions = []
        instructions.append("# SQL Generator Instructions")
        instructions.append("Based on extracted Figma data with full config.py compatibility")
        instructions.append("=" * 60)
        instructions.append("")
        
        instructions.append("## Quick Start")
        instructions.append("1. Import the config module into your SQL Generator")
        instructions.append("2. Use the data from sql_generator_input.json")
        instructions.append("3. All font weights are normalized to valid values (300, 400, 700)")
        instructions.append("4. All block types are validated against config.VALID_BLOCK_TYPES")
        instructions.append("")
        
        instructions.append("## Configuration Summary")
        instructions.append(f"- Default Color: {config.DEFAULT_COLOR}")
        instructions.append(f"- Color Settings ID: {config.DEFAULT_COLOR_SETTINGS_ID}")
        instructions.append(f"- Miniatures Base Path: {config.MINIATURES_BASE_PATH}")
        instructions.append(f"- Add Background: {config.AUTO_BLOCKS.get('add_background', True)}")
        instructions.append(f"- Add Watermark: {config.AUTO_BLOCKS.get('add_watermark', False)}")
        instructions.append("")
        
        # Generate per-slide instructions
        for i, slide in enumerate(sql_input):
            instructions.append(f"## Slide {i+1}: {slide['slide_layout_name']}")
            instructions.append(f"**Configuration:**")
            instructions.append(f"- Slide Number: {slide['slide_layout_number']}")
            instructions.append(f"- Slide Type: {slide['slide_type']} ({config.SLIDE_LAYOUT_TYPES.get(slide['slide_type'], 'unknown')})")
            instructions.append(f"- Is Last: {slide['is_last']}")
            instructions.append(f"- Folder: {slide.get('folder_name', 'other')}")
            instructions.append(f"- Total Blocks: {len(slide['blocks'])}")
            
            # Auto blocks
            if slide.get('auto_blocks'):
                instructions.append(f"**Auto Blocks:**")
                for block_name, block_info in slide['auto_blocks'].items():
                    instructions.append(f"- {block_name.title()}: {block_info['type']} (z-index: {block_info.get('z_index', 'default')})")
            
            instructions.append(f"**User Blocks:**")
            for j, block in enumerate(slide['blocks']):
                instructions.append(f"  {j+1}. **{block['type']}** - {block['name']}")
                instructions.append(f"     - Dimensions: {block['dimensions']}")
                instructions.append(f"     - Z-Index: {block['z_index']}")
                instructions.append(f"     - Null Styles: {block['needs_null_styles']}")
                
                if not block['needs_null_styles']:
                    styles = block['styles']
                    font_size = styles.get('fontSize') or styles.get('font_size') or '-'
                    weight = styles.get('weight') or '-'
                    instructions.append(f"     - Font: {font_size}px, weight {weight}")
                    instructions.append(f"     - Alignment: {styles.get('textVertical', '-') } / {styles.get('textHorizontal', '-')}")
                
                if block.get('corner_radius'):
                    instructions.append(f"     - Corner Radius: {block['corner_radius']}")
                instructions.append("")
            
            instructions.append("")
        
        # Add SQL Generator command examples
        instructions.append("## SQL Generator Commands")
        instructions.append("Run these commands in your SQL Generator:")
        instructions.append("```python")
        instructions.append("import config")
        instructions.append("from sql_generator import SQLGenerator")
        instructions.append("")
        instructions.append("generator = SQLGenerator(config)")
        instructions.append("# Use the extracted data to populate the generator")
        instructions.append("generator.run()")
        instructions.append("```")
        instructions.append("")
        
        instructions.append("## Files Generated")
        instructions.append("- `figma_extract.json`: Raw Figma extraction data")
        instructions.append("- `sql_generator_input.json`: Processed data ready for SQL Generator")
        instructions.append("- `sql_files/`: Individual SQL configuration files for each slide")
        instructions.append("- `sql_instructions.md`: This instruction file")
        
        with open(f"{output_dir}/sql_instructions.md", 'w') as f:
            f.write('\n'.join(instructions))

# Usage Examples
def example_usage():
    """Examples of how to use the integration with config compatibility"""
    
    # Initialize integrator
    integrator = FigmaToSQLIntegrator(
        figma_file_id="YOUR_FIGMA_FILE_ID",
        figma_token="YOUR_FIGMA_TOKEN"
    )
    
    # Example 1: Extract specific slides with full SQL generation
    print("Example 1: Extract slides 1, 3, and 5 with SQL generation")
    integrator.generate_sql_for_slides([1, 3, 5], "output/hero_and_cols")
    
    # Example 2: Extract slides with tables (will be automatically typed as 'table')
    print("\nExample 2: Extract slides containing tables")
    table_data = integrator.extract_by_block_types(['table'])
    if table_data:
        sql_input = integrator.prepare_sql_generator_input(table_data)
        print(f"Found {len(sql_input)} slides with tables, ready for SQL Generator")
        
        # Save for SQL Generator
        os.makedirs("output/tables", exist_ok=True)
        with open("output/tables/table_slides_config.json", 'w') as f:
            json.dump(sql_input, f, indent=2)
    
    # Example 3: Extract hero and infographics slides
    print("\nExample 3: Extract from hero and infographics containers")
    container_data = integrator.extract_by_containers(['hero', 'infographics'])
    if container_data:
        sql_input = integrator.prepare_sql_generator_input(container_data)
        print(f"Found {len(sql_input)} slides from specified containers")
        
        # Show configuration details
        for slide in sql_input:
            print(f"  • Slide {slide['slide_layout_number']}: {slide['slide_layout_name']}")
            print(f"    Type: {slide['slide_type']}, Blocks: {len(slide['blocks'])}")
            print(f"    Auto blocks: {list(slide['auto_blocks'].keys())}")
    
    # Example 4: Extract all slides and generate comprehensive SQL package
    print("\nExample 4: Extract all slides for full presentation")
    all_data = integrator.extract_specific_slides(list(range(1, 15)) + [-1])  # All slides including last
    if all_data:
        sql_input = integrator.prepare_sql_generator_input(all_data)
        
        # Generate complete SQL package
        output_dir = "output/complete_presentation"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save by slide type for organization
        by_type = {}
        for slide in sql_input:
            slide_type = slide['slide_type']
            if slide_type not in by_type:
                by_type[slide_type] = []
            by_type[slide_type].append(slide)
        
        for slide_type, slides in by_type.items():
            type_dir = f"{output_dir}/{slide_type}"
            os.makedirs(type_dir, exist_ok=True)
            with open(f"{type_dir}/slides_config.json", 'w') as f:
                json.dump(slides, f, indent=2)
            print(f"  • {slide_type}: {len(slides)} slides saved to {type_dir}/")
    
    # Example 5: Validate extraction against config
    print("\nExample 5: Config validation")
    validation_data = integrator.extract_specific_slides([1, 5, 8, 14])  # Different types
    if validation_data:
        print("Config Validation Results:")
        for slide in validation_data['slides']:
            print(f"  Slide {slide['slide_number']} ({slide['slide_type']}):")
            for block in slide['blocks']:
                is_valid_type = block['sql_type'] in config.BLOCK_TYPES['block_layout_type_options']
                is_valid_weight = block['styles']['weight'] in [300, 400, 700]
                print(f"    • {block['sql_type']}: Type OK: {is_valid_type}, Weight OK: {is_valid_weight}")

# Advanced integration class for batch processing
class BatchFigmaProcessor:
    """Process multiple Figma files or large sets of slides"""
    
    def __init__(self, figma_token: str):
        self.figma_token = figma_token
    
    def process_presentation_by_types(self, file_id: str, output_base: str = "batch_output"):
        """Process a presentation by extracting different slide types separately"""
        integrator = FigmaToSQLIntegrator(file_id, self.figma_token)
        
        # Define slide type groups based on config
        type_groups = {
            'title_and_last': [-1, 1],  # Special slides
            'text_layouts': [2, 3, 4, 6, 7, 9, 10, 11, 12, 13],  # Text-based
            'special_content': [5, 8, 14],  # Infographics, tables, charts
        }
        
        results = {}
        for group_name, slide_numbers in type_groups.items():
            print(f"\nProcessing {group_name}...")
            data = integrator.extract_specific_slides(slide_numbers)
            if data:
                sql_input = integrator.prepare_sql_generator_input(data)
                results[group_name] = sql_input
                
                # Save to organized folders
                group_dir = f"{output_base}/{group_name}"
                os.makedirs(group_dir, exist_ok=True)
                with open(f"{group_dir}/figma_extract.json", 'w') as f:
                    json.dump(data, f, indent=2)
                
                with open(f"{group_dir}/sql_config.json", 'w') as f:
                    json.dump(sql_input, f, indent=2)
                print(f"   {len(sql_input)} slides processed for {group_name}")
        
        return results
    
    def validate_font_weights_across_presentation(self, file_id: str) -> Dict[str, Any]:
        """Extract all slides and validate font weight compliance"""
        integrator = FigmaToSQLIntegrator(file_id, self.figma_token)
        all_data = integrator.extract_specific_slides(list(range(1, 15)) + [-1])
        
        if not all_data:
            return {"error": "Failed to extract data"}
        
        weight_analysis = {
            'total_blocks': 0,
            'weight_distribution': {300: 0, 400: 0, 700: 0},
            'invalid_weights_found': [],
            'slides_analyzed': len(all_data['slides'])
        }
        
        for slide in all_data['slides']:
            for block in slide['blocks']:
                weight_analysis['total_blocks'] += 1
                weight = block['styles']['weight']
                
                if weight in [300, 400, 700]:
                    weight_analysis['weight_distribution'][weight] += 1
                else:
                    weight_analysis['invalid_weights_found'].append({
                        'slide': slide['slide_number'],
                        'block': block['name'],
                        'invalid_weight': weight
                    })
        
        return weight_analysis

# Command-line interface for integration
if __name__ == "__main__":
    import argparse
    import config
    parser = argparse.ArgumentParser(description='Figma to SQL Generator Integration (Config Compatible)')
    parser.add_argument('--file-id', required=False, help='Figma file ID (optional if set in config.py)')
    parser.add_argument('--token', required=False, help='Figma API token (optional if set in config.py)')
    parser.add_argument('--mode', choices=['slides', 'blocks', 'containers', 'batch', 'validate'], 
                       default='slides', help='Processing mode')
    parser.add_argument('--slides', type=int, nargs='*', help='Specific slide numbers')
    parser.add_argument('--block-types', nargs='*', help='Specific block types')
    parser.add_argument('--containers', nargs='*', help='Specific containers')
    parser.add_argument('--output-dir', default='sql_output', help='Output directory')
    parser.add_argument('--batch', action='store_true', help='Enable batch processing mode')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, don\'t generate files')
    args = parser.parse_args()

    # Use config values if not provided
    file_id = args.file_id or getattr(config, 'FIGMA_FILE_ID', None)
    token = args.token or getattr(config, 'FIGMA_TOKEN', None)

    if not file_id or not token:
        print("Please provide --file-id and --token, or set FIGMA_FILE_ID and FIGMA_TOKEN in config.py")
        exit(1)

    integrator = FigmaToSQLIntegrator(file_id, token)

    if args.mode == 'slides' and args.slides:
        print(f"Processing specific slides: {args.slides}")
        integrator.generate_sql_for_slides(args.slides, args.output_dir)
        
    elif args.mode == 'blocks' and args.block_types:
        print(f"Processing slides with block types: {args.block_types}")
        data = integrator.extract_by_block_types(args.block_types)
        if data:
            sql_input = integrator.prepare_sql_generator_input(data)
            os.makedirs(args.output_dir, exist_ok=True)
            with open(f"{args.output_dir}/blocks_config.json", 'w') as f:
                json.dump(sql_input, f, indent=2)
            print(f"Processed {len(sql_input)} slides with specified block types")
        
    elif args.mode == 'containers' and args.containers:
        print(f"Processing slides from containers: {args.containers}")
        data = integrator.extract_by_containers(args.containers)
        if data:
            sql_input = integrator.prepare_sql_generator_input(data)
            os.makedirs(args.output_dir, exist_ok=True)
            with open(f"{args.output_dir}/containers_config.json", 'w') as f:
                json.dump(sql_input, f, indent=2)
            print(f"Processed {len(sql_input)} slides from specified containers")
        
    elif args.mode == 'batch':
        print("Running batch processing...")
        processor = BatchFigmaProcessor(token)
        results = processor.process_presentation_by_types(file_id, args.output_dir)
        print(f"Batch processing complete. Results: {list(results.keys())}")
        
    elif args.mode == 'validate':
        print("Running validation...")
        processor = BatchFigmaProcessor(token)
        validation = processor.validate_font_weights_across_presentation(file_id)
        
        print(f"Validation Results:")
        print(f"   Total blocks analyzed: {validation.get('total_blocks', 0)}")
        print(f"   Slides analyzed: {validation.get('slides_analyzed', 0)}")
        print(f"   Font weight distribution: {validation.get('weight_distribution', {})}")
        
        invalid = validation.get('invalid_weights_found', [])
        if invalid:
            print(f"   Found {len(invalid)} blocks with invalid font weights:")
            for item in invalid[:5]:  # Show first 5
                print(f"     - Slide {item['slide']}, Block: {item['block']}, Weight: {item['invalid_weight']}")
            if len(invalid) > 5:
                print(f"     ... and {len(invalid) - 5} more")
        else:
            print("   All font weights are valid!")
    
    else:
        print("Please specify a valid mode and required parameters")
        print("Examples:")
        print("  python integration.py --file-id ID --token TOKEN --mode slides --slides 1 2 3")
        print("  python integration.py --file-id ID --token TOKEN --mode blocks --block-types table chart")
        print("  python integration.py --file-id ID --token TOKEN --mode containers --containers hero infographics")
        print("  python integration.py --file-id ID --token TOKEN --mode batch")
        print("  python integration.py --file-id ID --token TOKEN --mode validate")

"""
Usage Examples with Config Compatibility:

1. Extract specific slides with full SQL generation:
   python integration.py --file-id YOUR_ID --token YOUR_TOKEN --mode slides --slides 1 3 5

2. Extract slides with specific block types:
   python integration.py --file-id YOUR_ID --token YOUR_TOKEN --mode blocks --block-types table chart slideTitle

3. Extract from specific containers:
   python integration.py --file-id YOUR_ID --token YOUR_TOKEN --mode containers --containers hero infographics table

4. Batch process entire presentation:
   python integration.py --file-id YOUR_ID --token YOUR_TOKEN --mode batch

5. Validate font weights and config compliance:
   python integration.py --file-id YOUR_ID --token YOUR_TOKEN --mode validate

6. Extract with custom output directory:
   python integration.py --file-id YOUR_ID --token YOUR_TOKEN --mode slides --slides 1 5 --output-dir my_slides
"""