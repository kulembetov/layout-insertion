import json
import os
import sys

import requests
import re
import argparse
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from script import config
import logging
import shutil
from enum import Enum

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

# Valid font weights - ONLY these are allowed
VALID_FONT_WEIGHTS = [300, 400, 700]

FIGMA_CONFIG = {
    'TARGET_WIDTH': 1200,
    'TARGET_HEIGHT': 675,
    'OUTPUT_DIR': 'figma_extract',
    'OUTPUT_FILE': 'extracted_data'
}

CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0

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


class EnhancedFigmaExtractor:
    def __init__(self, file_id: str, headers: Dict[str, str], filter_config: Optional[FilterConfig] = None):
        self.file_id = file_id
        self.headers = headers
        self.filter_config = filter_config or FilterConfig()

    def fetch(self) -> List[Dict]:
        response = requests.get(
            f'https://api.figma.com/v1/files/{self.file_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return  response.json()['document']['children']

    def extract(self) -> Dict[str, Any]:
        """Main extraction method"""

        try:
            pages = self.fetch()
            all_slides = []

            with open("1_pages.json", "w", encoding="utf-8") as outfile:
                json.dump(pages, outfile, ensure_ascii=False, indent=4)

            for page in pages:
                # print(f"\nProcessing page: {page.get('name', 'Unnamed')}")
                page_slides = self.traverse_and_extract(page)
                # print(page_slides)
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

    # def traverse_and_extract(self, node: Dict[str, Any], parent_name: str = "") -> List[ExtractedSlide]:
    #     """Enhanced traversal with filtering"""
    #     slides = []
        
    #     if self.is_target_frame(node):
    #         # print(f"Found target frame: \"{node['name']}\"")
    #         # print(f"Parent container: \"{parent_name}\"")

    #         frame_origin = {
    #                 'x': node['absoluteBoundingBox']['x'],
    #                 'y': node['absoluteBoundingBox']['y']
    #             }

    #         slide_number = self.get_slide_number(parent_name)

    #         # Skip if not in target slides (when filtering by specific slides)
    #         if (self.filter_config.mode == FilterMode.SPECIFIC_SLIDES and 
    #             slide_number not in self.filter_config.target_slides):
    #             return slides

    #         slide_type = self.detect_slide_type(parent_name, slide_number)

    #         blocks = self.collect_enhanced_blocks(
    #             node, frame_origin, slide_number, parent_name
    #         )

    #         if blocks or self.filter_config.mode == FilterMode.ALL:
    #             slide = ExtractedSlide(
    #                 number=slide_number,
    #                 container_name=parent_name,
    #                 frame_name=node['name'],
    #                 slide_type=slide_type,
    #                 blocks=blocks,
    #                 frame_id=node['id'],
    #                 dimensions={
    #                     'w': FIGMA_CONFIG['TARGET_WIDTH'],
    #                     'h': FIGMA_CONFIG['TARGET_HEIGHT']
    #                 }
    #             )
    #             # Attach the original node for color extraction
    #             slide._figma_node = node
    #             slides.append(slide)
    #             # print(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")
            
    #         return slides
        
        # Continue traversing children
        # if node.get('children'):
        #     for child in node['children']:
        #         child_slides = self.traverse_and_extract(child, node['name'])
        #         slides.extend(child_slides)
        
        # return slides

    def traverse_and_extract(self, node: Dict[str, Any], parent_name: str = "", depth: int = 0) -> List[ExtractedSlide]:
        """Traverse the Figma document tree and extract slides/blocks according to filter settings."""
        slides = []

        # Debugging info
        # print(f"Depth {depth}: Node {node.get('name')} ({node.get('type')})")

        # Base case: If current node is a target frame (potential slide)
        if self.is_target_frame(node):
            # Frame origin point relative to parent
            frame_origin = {
                'x': node['absoluteBoundingBox']['x'], 
                'y': node['absoluteBoundingBox']['y']
            }

            # Get slide number from parent container name
            slide_number = self.get_slide_number(parent_name)

            # Skip if not targeted by filters
            if self.filter_config.mode != FilterMode.ALL:
                if self.filter_config.mode == FilterMode.SPECIFIC_SLIDES and \
                   slide_number not in self.filter_config.target_slides:
                    return slides
                elif self.filter_config.mode == FilterMode.BY_TYPE and \
                     parent_name not in self.filter_config.target_containers:
                    return slides

            # Detect slide type based on config
            slide_type = self.detect_slide_type(parent_name, slide_number)

            # Collect blocks inside this frame
            blocks = self.collect_enhanced_blocks(node, frame_origin, slide_number, parent_name)

            # Create slide structure
            slide = ExtractedSlide(
                number=slide_number,
                container_name=parent_name,
                frame_name=node['name'],
                slide_type=slide_type,
                blocks=blocks,
                frame_id=node['id'],
                dimensions={'w': FIGMA_CONFIG['TARGET_WIDTH'], 'h': FIGMA_CONFIG['TARGET_HEIGHT']},
            )

            # Attach original node for further processing
            slide._figma_node = node

            # Add to results
            slides.append(slide)

        # Recursive step: Traverse child nodes
        if node.get('children'):
            for child in node['children']:
                child_slides = self.traverse_and_extract(child, node.get('name'), depth+1)
                slides.extend(child_slides)

        return slides

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
    
    def has_z_index_in_name(self, name: str) -> bool:
        """Check if name contains z-index"""
        return 'z-index' in name
    
    def get_slide_number(self, parent_name: str) -> int:
        """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
        key = parent_name.strip().lower()
        return config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)
    
    def detect_slide_type(self, container_name: str, slide_number: int) -> str:
        """Detect slide type using only config.py as the source of truth."""
        # Use config mapping for container name to slide number
        key = container_name.strip().lower()
        number = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
        # Use config mapping for slide number to type
        return config.SLIDE_NUMBER_TO_TYPE.get(number, 'classic')
    
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
                # print(f"Invalid block type '{sql_type}', defaulting to 'text'")
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
                has_corner_radius, corner_radius = self.extract_corner_radius(node)
                text_content = None
                text_like_types = ['text', 'blockTitle', 'slideTitle', 'subTitle', 'number', 'email', 'date', 'name', 'percentage']
                if sql_type in text_like_types and node.get('type') == 'TEXT':
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
                    # print(f"Added {sql_type} block: {name}")
                    # Log block details
                    color_info = f" | Color: {node_color}" if node_color else ""
                    # block_logger.info(
                    #     f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{color_info}"
                    # )
        # Recursively process children (skip children of hidden nodes)
        if node.get('children') and not (self.filter_config.exclude_hidden and node.get('visible') is False):
            for child in node['children']:
                blocks.extend(self.collect_enhanced_blocks(child, frame_origin, slide_number, parent_container))
        return blocks
    
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
                # print(f"Detected '{sql_type}' from pattern '{pattern}' in name '{clean_name}'")
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
                # print(f"Detected 'background' from heuristic keywords in '{clean_name}'")
                return 'background', 'background'
            elif any(keyword in clean_name for keyword in ['icon', 'symbol']):
                # print(f"Detected 'icon' from heuristic keywords in '{clean_name}'")
                return 'icon', 'icon'
            elif any(keyword in clean_name for keyword in ['image', 'img', 'photo', 'picture']):
                # print(f"Detected 'image' from heuristic keywords in '{clean_name}'")
                return 'image', 'image'
            # print(f"Defaulting to 'figure' for RECTANGLE: '{clean_name}'")
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
        # print(f"Using default 'text' type for node: {name} (type: {node_type}, clean_name: {clean_name})")
        return 'text', 'text'
    
    def round_to_nearest_five(self, value: float) -> int:
        """Round value to nearest 5"""
        return round(value / 5) * 5
    
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
                    if block_logger:
                        block_logger.info(f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups")
                        for color_hex, obj_list in block_colors.items():
                            block_logger.info(f"[slideConfig]   Color '{color_hex}': {len(obj_list)} objects")
        return config_dict, sorted(palette_colors)
    

    def _update_figure_config_with_names(self, slide_config, blocks):
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
            
            # Process ALL figure entries from slideColors, not just the ones that have corresponding blocks
            for obj in obj_list:
                figure_name = obj.get('figureName', '')
                if figure_name:
                    # Try to find a matching block in the main structure
                    matching_block = None
                    for fig in figure_blocks_info:
                        base_name = fig['base_name']
                        index_match = re.search(r'_(\d+)$', base_name)
                        if index_match and index_match.group(1) == figure_name:
                            matching_block = fig['block']
                            break
                    
                    # Create figure object for this entry
                    font_family = obj.get('fontFamily')
                    if font_family:
                        # Normalize to snake_case
                        font_family = re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))
                    fill = obj.get('color')
                    
                    # Always try to extract the proper figure name from the figure blocks
                    clean_figure_name = figure_name  # Default to slideColors name
                    
                    # Try to find a matching block to get the proper name
                    found_match = False
                    for fig in figure_blocks_info:
                        base_name = fig['base_name']
                        index_match = re.search(r'_(\d+)$', base_name)
                        if index_match and index_match.group(1) == figure_name:
                            # Found matching block, extract proper name
                            clean_figure_name = re.sub(r'_(\d+)$', '', base_name)
                            if block_logger:
                                block_logger.info(f"[figureConfig] Found exact index match for '{figure_name}', using name: '{clean_figure_name}'")
                            found_match = True
                            break
                    
                    # If no exact match, try to find by z-index or other patterns
                    if not found_match:
                        for fig in figure_blocks_info:
                            base_name = fig['base_name']
                            # Try to match by z-index if available
                            z_index_match = re.search(r'z-index\s*(\d+)', fig['block'].name)
                            if z_index_match and z_index_match.group(1) == figure_name:
                                clean_figure_name = re.sub(r'_(\d+)$', '', base_name)
                                if block_logger:
                                    block_logger.info(f"[figureConfig] Found z-index match for '{figure_name}', using name: '{clean_figure_name}'")
                                found_match = True
                                break
                    
                    # If still no match, try to find by position in the list (assuming order matters)
                    if not found_match and len(figure_blocks_info) > 0:
                        # Use the first available block name as fallback
                        first_block = figure_blocks_info[0]
                        clean_figure_name = re.sub(r'_(\d+)$', '', first_block['base_name'])
                        if block_logger:
                            block_logger.info(f"[figureConfig] No match found for '{figure_name}', using fallback name: '{clean_figure_name}'")
                    
                    if block_logger:
                        if matching_block:
                            block_logger.info(f"[figureConfig] MATCHED: color {color_hex}, figure '{figure_name}' -> color: {fill}, font: {font_family}")
                        else:
                            block_logger.info(f"[figureConfig] NO BLOCK MATCH: color {color_hex}, figure '{figure_name}' -> color: {fill}, font: {font_family}")
                    
                    figure_obj = {
                        "color": fill,
                        "fontFamily": font_family,
                        "figureName": clean_figure_name
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
        # Add word count for all blocks
        text_content = getattr(block, 'text_content', None)
        if text_content:
            words = [w for w in re.split(r'\s+', text_content) if w.strip()]
            block_dict['words'] = len(words)
        else:
            block_dict['words'] = 0
        
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
        
        # Handle figure blocks with color extraction - collect all colors from slideConfig
        elif block.sql_type == 'figure':
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
            
            # Secondary: Collect all colors from slideConfig for figures
            elif slide_config and 'figure' in slide_config:
                # Store all available colors for figures
                all_colors = []
                all_fonts = []
                
                for color_hex, figure_objects in slide_config['figure'].items():
                    for figure_obj in figure_objects:
                        color_val = figure_obj.get('color')
                        font_family = figure_obj.get('fontFamily')
                        if color_val:
                            all_colors.append(color_val)
                        if font_family:
                            all_fonts.append(font_family)
                
                # Store all colors and fonts found for figures
                if all_colors:
                    block_dict['all_colors'] = list(set(all_colors))  # Remove duplicates
                    if block_logger:
                        block_logger.info(f"[figureColor] Block '{block.name}' (figure): Found {len(block_dict['all_colors'])} unique colors: {block_dict['all_colors']}")
                if all_fonts:
                    block_dict['all_fonts'] = list(set(all_fonts))  # Remove duplicates
                    if block_logger:
                        block_logger.info(f"[figureColor] Block '{block.name}' (figure): Found {len(block_dict['all_fonts'])} unique fonts: {block_dict['all_fonts']}")
                
                # Also try to match specific index if available
                if name_match:
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
                
                # Also keep the first color for backward compatibility if no specific match
                if all_colors and 'color' not in block_dict:
                    block_dict['color'] = all_colors[0]
                if all_fonts and 'fontFamily' not in block_dict:
                    block_dict['fontFamily'] = all_fonts[0]
        
        # Handle image blocks with color extraction
        elif block.sql_type == 'image' and hasattr(block, 'node_color') and block.node_color:
            block_dict['color'] = block.node_color
        
        # NEW: Add all available colors for text-based block types from slideConfig
        # This allows extracting all colors (like 5 for slideTitle, 3 for blockTitle) instead of just the first one
        text_block_types = ['slideTitle', 'blockTitle', 'text', 'subTitle', 'number', 'email', 'date', 'name', 'percentage']
        if block.sql_type in text_block_types and slide_config and block.sql_type in slide_config:
            # Store all available colors for this block type
            all_colors = []
            all_fonts = []
            
            for color_hex, color_objects in slide_config[block.sql_type].items():
                for obj in color_objects:
                    color_val = obj.get('color')
                    font_family = obj.get('fontFamily')
                    if color_val:
                        all_colors.append(color_val)
                    if font_family:
                        all_fonts.append(font_family)
            
            # Store all colors and fonts found for this block type
            if all_colors:
                block_dict['all_colors'] = list(set(all_colors))  # Remove duplicates
                if block_logger:
                    block_logger.info(f"[colorExtraction] Block '{block.name}' ({block.sql_type}): Found {len(block_dict['all_colors'])} unique colors: {block_dict['all_colors']}")
            if all_fonts:
                block_dict['all_fonts'] = list(set(all_fonts))  # Remove duplicates
                if block_logger:
                    block_logger.info(f"[colorExtraction] Block '{block.name}' ({block.sql_type}): Found {len(block_dict['all_fonts'])} unique fonts: {block_dict['all_fonts']}")
            
            # Also keep the first color for backward compatibility
            if all_colors and 'color' not in block_dict:
                block_dict['color'] = all_colors[0]
            if all_fonts and 'fontFamily' not in block_dict:
                block_dict['fontFamily'] = all_fonts[0]
        
        return block_dict
    
    def info(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.info("Houston, we have a %s", "notable problem", exc_info=True)
        """
        if self.isEnabledFor(INFO):
            self._log(INFO, msg, args, **kwargs)

    def isEnabledFor(self, level):
        """
        Is this logger enabled for level 'level'?
        """
        if self._is_disabled():
            return False

        try:
            return self._cache[level]
        except KeyError:
            with _lock:
                if self.manager.disable >= level:
                    is_enabled = self._cache[level] = False
                else:
                    is_enabled = self._cache[level] = (
                        level >= self.getEffectiveLevel()
                    )
            return is_enabled
        
    def _is_disabled(self):
        # We need to use getattr as it will only be set the first time a log
        # message is recorded on any given thread
        return self.disabled or getattr(self._tls, 'in_progress', False)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False,
             stacklevel=1):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        sinfo = None
        if _srcfile:
            #IronPython doesn't track Python frames, so findCaller raises an
            #exception on some versions of IronPython. We trap it here so that
            #IronPython can use logging.
            try:
                fn, lno, func, sinfo = self.findCaller(stack_info, stacklevel)
            except ValueError: # pragma: no cover
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else: # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = self.makeRecord(self.name, level, fn, lno, msg, args,
                                 exc_info, func, extra, sinfo)
        self.handle(record)