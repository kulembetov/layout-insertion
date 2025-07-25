import requests
from api_v1.services.filter_service import FilterConfig
from typing import Dict, List, Any, Tuple, Optional
from logger import setup_logger
# from .checker import Checker
from .filter_service import FilterMode, FilterConfig
from .utils import should_include, extract_color_info, extract_base_figure_name, BlockBuilder, Checker
from .data_classes import ExtractedBlock, ExtractedSlide
import re
from api_v1.constants import BLOCKS, SLIDES, CONSTANTS, TEMPLATES

logg = setup_logger(__name__)

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
            all_slides = []
            for page in pages:
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
                logg.info(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")
            
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
            getattr(self.filter_config, 'ready_to_dev_marker', ''),
            node.get('name', '')
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
                
        type_mappings = {
            'TEXT': [
                (['title', 'heading', 'header', 'h1', 'h2'], {'sql_type': 'blockTitle'}),
                (['slide', 'main'], {'sql_type': 'slideTitle'} if any(kw in clean_name for kw in ['title', 'heading', 'header', 'h1', 'h2']) else None),
                (['subtitle', 'sub', 'subheading'], {'sql_type': 'subTitle'}),
                (['number', 'num', 'count'], {'sql_type': 'number'}),
                (['email', '@', 'mail'], {'sql_type': 'email'}),
                (['date', 'time', 'year', 'month'], {'sql_type': 'date'}),
                (['name', 'author', 'person'], {'sql_type': 'name'}),
                (['percent', '%', 'percentage'], {'sql_type': 'percentage'}),
                ([], {'sql_type': 'text'})
            ],
            'RECTANGLE': [
                (['background', 'bg', 'backdrop'], {'sql_type': 'background'}),
                (['icon', 'symbol'], {'sql_type': 'icon'}),
                (['image', 'img', 'photo', 'picture'], {'sql_type': 'image'}),
                ([], {'sql_type': 'figure'})
            ],
            'FRAME': [
                (['table', 'grid', 'data'], {'sql_type': 'table'}),
                (['chart', 'graph'], {'sql_type': 'table'}),
                (['infographic', 'infographik', 'visual'], {'sql_type': 'infographik'}),
                (['watermark', 'mark'], {'sql_type': 'watermark'}),
                ([], {'sql_type': 'figure'})
            ],
            'GROUP': [
                (['table', 'grid', 'data'], {'sql_type': 'table'}),
                (['chart', 'graph'], {'sql_type': 'table'}),
                (['infographic', 'infographik', 'visual'], {'sql_type': 'infographik'}),
                (['watermark', 'mark'], {'sql_type': 'watermark'}),
                ([], {'sql_type': 'figure'})
            ]
        }

        mappings_for_node = type_mappings.get(node_type, [])
        for keywords, mapping in mappings_for_node:
            if not keywords or any(keyword in clean_name for keyword in keywords):
                sql_type = mapping.get('sql_type')
                if sql_type and sql_type in BLOCKS.BLOCK_TYPES['block_layout_type_options']:
                    return clean_name, sql_type
        return 'text', 'text'

    def count_sentences(self, text: str) -> int:
        if not text:
            return 0
        split_result = [s for s in re.split(r'[.!?]', text)]
        n = len([s for s in split_result if s.strip()])
        return n if n > 0 else 1
    
    def normalize_font_family(self, font_family: str) -> str:
        if not font_family:
            return ""
        return re.sub(r'[^a-z0-9_]', '', font_family.strip().lower().replace(' ', '_').replace('-', '_'))
    
    def _update_figure_config_with_names(self, slide_config, blocks):
        figure_blocks_by_name = {}
        
        for block in blocks:
            if block.sql_type != 'figure':
                continue

            base_name = extract_base_figure_name(block.name)
            figure_blocks_by_name[base_name] = block
            logg.info(f"[figureBlocks] Found figure block: '{block.name}' -> base_name: '{base_name}'")

        new_figure_config = {}

        for color_hex, obj_list in slide_config['figure'].items():
            figure_objects = []
            
            for obj in obj_list:
                figure_name = obj.get('figureName', '')
                if not figure_name:
                    continue
                    
                font_family = obj.get('fontFamily')
                normalized_font_family = self.normalize_font_family(font_family)
                fill_color = obj.get('color')
                matching_block = figure_blocks_by_name.get(extract_base_figure_name(figure_name))
                clean_figure_name = extract_base_figure_name(figure_name)
                
                if matching_block is not None:
                    clean_figure_name = extract_base_figure_name(matching_block.name)
                    logg.info(f"[figureConfig] MATCHED: color {color_hex}, figure '{figure_name}' -> color: {fill_color}, font: {normalized_font_family}")
                else:
                    logg.info(f"[figureConfig] NO BLOCK MATCH: color {color_hex}, figure '{figure_name}' -> color: {fill_color}, font: {normalized_font_family}")

                figure_obj = {
                    "color": fill_color,
                    "fontFamily": normalized_font_family,
                    "figureName": clean_figure_name
                }
                figure_objects.append(figure_obj)
            new_figure_config[color_hex] = figure_objects
        slide_config['figure'] = new_figure_config
        logg.info(f"[figureConfig] SUMMARY: Processed {len(figure_blocks_by_name)} figure blocks")

    def _extract_slide_config(self, slide_node):
        """ Extract slideConfig from the hidden slideColors table in the slide node, including color and fontFamily for each color layer. Also extracts presentation palette colors found in the slideColors table. :param slide_node: Slide XML representation containing hidden slideColors table :return: tuple(config_dict, list_of_palette_colors) """
        config_dict = {}
        palette_colors = set()

        if not slide_node or not slide_node.get("children"):
            return config_dict, []

        for child in slide_node["children"]:
            if child.get("name") != "slideColors":
                continue

            logg.info("[slideColors] Found slideColors table in slide")

            for block in child.get("children", []):
                block_type = block.get("name")
                logg.info(f"[slideColors] Processing block type: {block_type}")

                block_colors = {}
                for color_group in block.get("children", []):
                    color_hex = color_group.get("name").lower() if color_group.get("name") else ""
                    palette_colors.add(color_hex)

                    logg.info(f"[slideColors] Processing color group: {color_hex}")

                    block_objs = []
                    for text_child in color_group.get("children", []):
                        if text_child.get("type") != "TEXT":
                            continue

                        obj = {
                            "color": extract_color_info(text_child)[0],  # Use 'color' instead of 'fill'
                            "fontFamily": self.normalize_font_family(
                                text_child["style"].get("fontFamily")
                            ),
                        }

                        if block_type == "figure":
                            obj["figureName"] = text_child.get("name", "").strip()

                        color_var = extract_color_info(text_child)[1]
                        if color_var:
                            obj["color_variable"] = color_var

                        logg.info(
                            f"[slideColors] Found figure in {color_hex}: "
                            f"name='{obj.get('figureName')}'; color={obj['color']}; font={obj['fontFamily']}"
                        )

                        block_objs.append(obj)

                    block_colors[color_hex] = block_objs

                config_dict[block_type] = block_colors
                logg.info(f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups")

        return config_dict, sorted(palette_colors)
    
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
    
    # МБ Вынести в отдельный класс ===================================================================

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
        defaults = CONSTANTS.DEFAULT_STYLES.get(sql_type, CONSTANTS.DEFAULT_STYLES['default'])
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
    
    def _block_to_dict(self, block: ExtractedBlock, slide_config=None) -> Dict[str, Any]:
        # Now just call build_block_dict for all block dict construction
        return BlockBuilder(block, slide_config).build()

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
                logg.info(f"Skipping {sql_type} block {name} (full image 1200x675)", level='debug')
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
                    logg.info(f"Added {sql_type} block: {name}")
                    color_info = f" | Color: {node_color}" if node_color else ""
                    logg.info(
                        f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{color_info}",
                    )
        # Recursively process children (skip children of hidden nodes)
        if node.get('children') and not (getattr(self.filter_config, 'exclude_hidden', True) and node.get('visible') is False):
            for child in node['children']:
                blocks.extend(self.collect_enhanced_blocks(child, frame_origin, slide_number, parent_container))
        return blocks
    
    