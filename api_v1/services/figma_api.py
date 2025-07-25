import requests
import json

from typing import Any, Optional
from api_v1.services.filter_service import FilterConfig
from typing import Dict, List, Any, Tuple, Optional
import config
import logging
import os
from logger import setup_logger
from .checker import Checker
from .filter_service import FilterMode, FilterConfig
from utils import should_include, extract_color_info, extract_base_figure_name, BlockBuilder
from .data_classes import ExtractedBlock, ExtractedSlide
import re
from constants import BLOCKS, SLIDES, CONSTANTS, TEMPLATES

logg = setup_logger(__name__)
# ================ Logging Utility ================
class LogUtils:
    @staticmethod
    def log_block_event(message, level='info'):
        """Unified logging for block/frame events, respects config.VERBOSE."""
        global block_logger
        if block_logger:
            if level == 'debug':
                block_logger.debug(message)
            else:
                block_logger.info(message)
        if hasattr(config, 'VERBOSE') and getattr(config, 'VERBOSE', False):
            print(message)

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



class FigmaAPI:
    def __init__(self, *, file_id: Optional[str] = None, token: Optional[str] = None, filter_config: Optional[FilterConfig] = None) -> None:
        self._file_id = file_id
        self._token = token
        self._filter_config = filter_config or FilterConfig()

    @property
    def file_id(self) -> Optional[str]:
        return self._file_id

    @file_id.setter
    def file_id(self, file_id: str):
        if isinstance(file_id, str):
            self._file_id = file_id
        else:
            raise TypeError("'file_id' must be str.")

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, token: str):
        if isinstance(token, str):
            self._token = token
        else:
            raise TypeError("'token' must be str.")

    @property
    def headers(self) -> dict[str, Any]:
        return {'X-Figma-Token': f'{self._token}'}
    
    @property
    def filter_config(self) -> Optional[FilterConfig]:
        return self._filter_config

    @filter_config.setter
    def filter_config(self, value: Optional[FilterConfig]):
        if isinstance(value, FilterConfig) or value is None:
            self._filter_config = value
        else:
            raise ValueError("The filter must be an instance of FilterConfig or None.")


    def fetch(self) -> dict[str, Any]:
        """
        Returns JSON response from Figma by 'file_id'.
        """
        response = requests.get(
            f'https://api.figma.com/v1/files/{self.file_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['document']['children']

    def extract(self) -> dict[str, Any]:

        try:
            pages = self.fetch()
            # print(pages)
            # with open("1_pages.json", "w", encoding="utf-8") as outfile:
            #     json.dump(pages, outfile, ensure_ascii=False, indent=4)

            all_slides = []
            for page in pages:
                # LogUtils.log_block_event(f"\nProcessing page: {page.get('name', 'Unnamed')}")
                logg.info(f"\nProcessing page: {page.get('name', 'Unnamed')}")
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
                    'figma_config': CONSTANTS.FIGMA_CONFIG,
                    'extraction_summary': summary,
                    'filter_config': {
                        'mode': self.filter_config.mode.value,
                        'target_slides': self.filter_config.target_slides,
                        'target_block_types': self.filter_config.target_block_types,
                        'target_containers': self.filter_config.target_containers
                    },
                    'sql_generator_compatibility': {
                        'valid_block_types': BLOCKS.BLOCK_TYPES['block_layout_type_options'],
                        'valid_font_weights': CONSTANTS.VALID_FONT_WEIGHTS,
                        'slide_layout_types': SLIDES.SLIDE_LAYOUT_TYPES
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

    def traverse_and_extract(self, node: Dict[str, Any], parent_name: str = "") -> List[ExtractedSlide]:
        """Enhanced traversal with filtering"""
        slides = []
        
        if self.is_target_frame(node):
            # LogUtils.log_block_event(f"Found target frame: \"{node['name']}\"")
            # LogUtils.log_block_event(f"Parent container: \"{parent_name}\"")
            logg.info(f"Found target frame: \"{node['name']}\"")
            logg.info(f"Parent container: \"{parent_name}\"")

            frame_origin = {
                'x': node['absoluteBoundingBox']['x'],
                'y': node['absoluteBoundingBox']['y']
            }

            slide_number = self.get_slide_number(parent_name)
            slide_type = self.detect_slide_type(parent_name, slide_number)

            # Skip if not in target slides (when filtering by specific slides)
            if (self.filter_config.mode == FilterMode.SPECIFIC_SLIDES and 
                slide_number not in self.filter_config.target_slides):
                return slides
            
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
                        'w': CONSTANTS.FIGMA_CONFIG['TARGET_WIDTH'],
                        'h': CONSTANTS.FIGMA_CONFIG['TARGET_HEIGHT']
                    }
                )
                # Attach the original node for color extraction
                slide._figma_node = node
                slides.append(slide)
                LogUtils.log_block_event(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")
            
            return slides

        # Continue traversing children
        if node.get('children'):
            for child in node['children']:
                child_slides = self.traverse_and_extract(child, node['name'])
                slides.extend(child_slides)
        
        return slides

    def is_target_frame(self, node: Dict[str, Any]) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker"""

        if not node.get('absoluteBoundingBox'):
            return False
        
        # Checks if the frame name contains a Z-index.
        if self.filter_config.require_z_index and not Checker.check_z_index(node.get('name', '')):
            return False
        
        # Checks for the 'ready to dev' label.
        if not Checker.check_marker(
            node, getattr(self.filter_config, 'ready_to_dev_marker', '')
        ):
            return False
        
        # Checks whether the frame size matches the target width and height.
        if not Checker.check_dimensions(node['absoluteBoundingBox']):
            return False
        
        # Checks whether the frame area exceeds the minimum threshold.
        if not Checker.check_min_area(
            node['absoluteBoundingBox'], self.filter_config.min_area
        ):
            return False
        
        return True
    
    def get_slide_number(self, parent_name: str) -> int:
        """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
        key = parent_name.strip().lower()
        return SLIDES.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)
    
    def detect_slide_type(self, container_name: str, slide_number: int) -> str:
        """Detect slide type using only config.py as the source of truth."""
        # Use config mapping for container name to slide number
        key = container_name.strip().lower()
        number = SLIDES.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
        # Use config mapping for slide number to type
        return SLIDES.SLIDE_NUMBER_TO_TYPE.get(number, 'classic')

    def round_to_nearest_five(self, value: float) -> int:
        """Round value to nearest 5"""
        return round(value / 5) * 5
    
    def normalize_font_weight(self, weight: Any) -> int:
        """Normalize font weight to valid values (300, 400, 700)"""
        if weight is None:
            return 400












    # Отрефакторить ==================================================================================================
    def collect_enhanced_blocks(self, node: Dict[str, Any], frame_origin: Dict[str, int], 
                              slide_number: int, parent_container: str) -> List[ExtractedBlock]:
        blocks = []
        if not node.get('absoluteBoundingBox'):
            return blocks
        
        # Centralized filtering for node
        if not should_include(node, self.filter_config):
            return blocks
        name = node.get('name', '')
        has_z = Checker.check_z_index(name)

        # Only process nodes with z-index in the name
        if has_z:
            figma_type, sql_type = self.detect_block_type(node)
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
                LogUtils.log_block_event(f"Skipping {sql_type} block {name} (full image 1200x675)", level='debug')
            else:
                styles = self.extract_text_styles(node, sql_type)
                z_index = self.extract_z_index(name)
                if z_index == 0:
                    z_index = CONSTANTS.Z_INDEX_DEFAULTS.get(sql_type, CONSTANTS.Z_INDEX_DEFAULTS['default'])
                styles['zIndex'] = z_index
                has_corner_radius, corner_radius = self.extract_corner_radius(node)
                text_content = None
                text_like_types = ['text', 'blockTitle', 'slideTitle', 'subTitle', 'number', 'email', 'date', 'name', 'percentage']
                if sql_type in text_like_types and node.get('type') == 'TEXT':
                    text_content = node.get('characters', None)
                
                # Extract color information for background and other relevant blocks
                node_color = None
                if sql_type in BLOCKS.BLOCK_TYPES['null_style_types']:
                    node_color = extract_color_info(node)[0] # Only get hex color
                
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
                if should_include(block, self.filter_config):
                    blocks.append(block)
                    LogUtils.log_block_event(f"Added {sql_type} block: {name}")
                    color_info = f" | Color: {node_color}" if node_color else ""
                    LogUtils.log_block_event(
                        f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{color_info}",
                        level='debug'
                    )
        # Recursively process children (skip children of hidden nodes)
        if node.get('children') and not (getattr(self.filter_config, 'exclude_hidden', True) and node.get('visible') is False):
            for child in node['children']:
                blocks.extend(self.collect_enhanced_blocks(child, frame_origin, slide_number, parent_container))
        return blocks

    def detect_block_type(self, node: dict) -> Tuple[str, str]:
        """Detect block type from a Figma node, returning (figma_type, sql_type). Always returns a valid sql_type."""
        name = node.get('name', '').lower()
        node_type = node.get('type', '')
        clean_name = re.sub(r'\s*z-index.*$', '', name)
        # Check for explicit mappings first, prioritize longer patterns
        sorted_patterns = sorted(CONSTANTS.FIGMA_TO_SQL_BLOCK_MAPPING.items(), key=lambda x: len(x[0]), reverse=True)
        for pattern, sql_type in sorted_patterns:
            if pattern in clean_name:
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return pattern, sql_type
        # Infer from Figma node type with heuristics
        if node_type == 'TEXT':
            if any(keyword in clean_name for keyword in ['title', 'heading', 'header', 'h1', 'h2']):
                if any(keyword in clean_name for keyword in ['slide', 'main']):
                    sql_type = 'slideTitle'
                    if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                        return 'slideTitle', sql_type
                sql_type = 'blockTitle'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'blockTitle', sql_type
            elif any(keyword in clean_name for keyword in ['subtitle', 'sub', 'subheading']):
                sql_type = 'subTitle'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'subTitle', sql_type
            elif any(keyword in clean_name for keyword in ['number', 'num', 'count']):
                sql_type = 'number'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'number', sql_type
            elif any(keyword in clean_name for keyword in ['email', '@', 'mail']):
                sql_type = 'email'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'email', sql_type
            elif any(keyword in clean_name for keyword in ['date', 'time', 'year', 'month']):
                sql_type = 'date'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'date', sql_type
            elif any(keyword in clean_name for keyword in ['name', 'author', 'person']):
                sql_type = 'name'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'name', sql_type
            elif any(keyword in clean_name for keyword in ['percent', '%', 'percentage']):
                sql_type = 'percentage'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'percentage', sql_type
            sql_type = 'text'
            if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                return 'text', sql_type
        elif node_type == 'RECTANGLE':
            if any(keyword in clean_name for keyword in ['background', 'bg', 'backdrop']):
                sql_type = 'background'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'background', sql_type
            elif any(keyword in clean_name for keyword in ['icon', 'symbol']):
                sql_type = 'icon'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'icon', sql_type
            elif any(keyword in clean_name for keyword in ['image', 'img', 'photo', 'picture']):
                sql_type = 'image'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'image', sql_type
            sql_type = 'figure'
            if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                return 'figure', sql_type
        elif node_type in ['FRAME', 'GROUP']:
            if any(keyword in clean_name for keyword in ['table', 'grid', 'data']):
                sql_type = 'table'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'table', sql_type
            elif any(keyword in clean_name for keyword in ['chart', 'graph']):
                sql_type = 'table'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'table', sql_type
            elif any(keyword in clean_name for keyword in ['infographic', 'infographik', 'visual']):
                sql_type = 'infographik'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'infographik', sql_type
            elif any(keyword in clean_name for keyword in ['watermark', 'mark']):
                sql_type = 'watermark'
                if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return 'watermark', sql_type
            sql_type = 'figure'
            if sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                return 'figure', sql_type
        # Default fallback
        return 'text', 'text'
    
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
        sentence_count = 1
        if max_text_block:
            text_content = getattr(max_text_block, 'text_content', None)
            sentence_count = self.count_sentences(text_content)
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
            'folder_name': SLIDES.SLIDE_NUMBER_TO_FOLDER.get(slide.number, 'other'),
            'blocks': [self._block_to_dict(block, slide_config) for block in slide.blocks],
            'block_count': len(slide.blocks),
            'slideConfig': slide_config,
            'presentationPaletteColors': presentation_palette_colors
        }
    
    def count_sentences(self, text: str) -> int:
        if not text:
            return 0
        split_result = [s for s in re.split(r'[.!?]', text)]
        n = len([s for s in split_result if s.strip()])
        return n if n > 0 else 1

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
                            color_hex = color_hex.lower() 
                            palette_colors.add(color_hex)
                        if block_logger:
                            block_logger.info(f"[slideColors] Processing color group: {color_hex}")
                        block_objs = []
                        for text_child in color_group.get('children', []):
                            if text_child.get('type') == 'TEXT':
                                obj = {}
                                color_val, color_var = extract_color_info(text_child)
                                obj['color'] = color_val  # Use 'color' instead of 'fill'
                                if color_var:
                                    obj['color_variable'] = color_var
                                font_family = None
                                if 'style' in text_child and 'fontFamily' in text_child['style']:
                                    font_family = text_child['style']['fontFamily']
                                obj['fontFamily'] = self.normalize_font_family(font_family)
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
    
    def normalize_font_family(self, font_family: str) -> str:
        if not font_family:
            return ""
        return re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))
    
    def _update_figure_config_with_names(self, slide_config, blocks):
        # Collect all figure blocks with their info
        figure_blocks_info = []
        for block in blocks:
            if block.sql_type == 'figure':
                base_name = extract_base_figure_name(block.name)
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
                    font_family = self.normalize_font_family(font_family)
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
        # Now just call build_block_dict for all block dict construction
        return BlockBuilder(block, slide_config).build()




# Вынести в отдельный класс

    def extract_figure_index(self, name: str) -> str:
        """Extract the trailing index (e.g., '_2') from a figure name, or return ''."""
        if not name:
            return ''
        index_match = re.search(r'_(\d+)$', name)
        if index_match:
            return index_match.group(1)
        return ''
    
    def extract_text_styles(self, node: Dict[str, Any], sql_type: str) -> Dict[str, Any]:
        """Extract text styling information with config defaults (no color)."""
        defaults = BLOCKS.DEFAULT_STYLES.get(sql_type, BLOCKS.DEFAULT_STYLES['default'])
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