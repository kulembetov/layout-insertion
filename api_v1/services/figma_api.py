import requests

from typing import Any, Optional
from logger import setup_logger

from .filters.filter_settings import FilterMode, FilterConfig
from .utils import Checker, Extractor, should_include, round5, get_slide_number, detect_slide_type, \
    detect_block_type, count_sentences, normalize_font_family, block_to_dict
from .data_classes import ExtractedBlock, ExtractedSlide

from api_v1.constants import BLOCKS, SLIDES, CONSTANTS


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
    def file_id(self, file_id: str) -> None:
        if isinstance(file_id, str):
            self._file_id = file_id
        else:
            raise TypeError("'file_id' must be str.")

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, token: str) -> None:
        if isinstance(token, str):
            self._token = token
        else:
            raise TypeError("'token' must be str.")
    
    @property
    def filter_config(self) -> FilterConfig:
        return self._filter_config

    @filter_config.setter
    def filter_config(self, config: FilterConfig) -> None:
        if isinstance(config, FilterConfig):
            self._filter_config = config
        else:
            raise TypeError("'config' must be FilterConfig.")

    @property
    def headers(self) -> dict[str, Any]:
        return {'X-Figma-Token': self._token}


    def fetch(self) -> list[dict]:
        """
        Returns JSON response from Figma by 'file_id'.
        """
        response = requests.get(
            f'https://api.figma.com/v1/files/{self.file_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['document']['children']


    # =========== Extract codeblocks ==============

    def _get_slides(self) -> list[ExtractedSlide]:
        pages = self.fetch()
        all_slides = []
        for page in pages:
            logg.info(f"\nProcessing page: {page.get('name', 'Unnamed')}")
            page_slides = self.traverse_and_extract(page)
            all_slides.extend(page_slides)

        return all_slides

    @staticmethod
    def _get_summary(slides) -> dict[str, Any]:
        # Generate summary
        summary = {
            'total_slides': len(slides),
            'total_blocks': sum(len(slide.blocks) for slide in slides),
            'slide_types': {},
            'block_types': {},
            'slide_distribution': {}
        }

        for slide in slides:
            slide_type = slide.slide_type
            summary['slide_types'][slide_type] = summary['slide_types'].get(slide_type, 0) + 1
            summary['slide_distribution'][slide.number] = slide.container_name

            for block in slide.blocks:
                block_type = block.sql_type
                summary['block_types'][block_type] = summary['block_types'].get(block_type, 0) + 1

        return summary


    def extract(self) -> dict[str, Any]:
        try:
            all_slides = self._get_slides()
            summary = self._get_summary(all_slides)

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

        except Exception as e:
            print(f"Unexpected error: {e}")
            return {
                'metadata': {
                    'file_id': self.file_id,
                    'error': str(e)
                },
                'slides': []
            }

    # =============================================

    def traverse_and_extract(self, node: dict[str, Any], parent_name: str = "") -> list[ExtractedSlide]:
        """Enhanced traversal with filtering"""
        slides = []
        
        if self.is_target_frame(node):
            logg.info(f"Found target frame: \"{node['name']}\"")
            logg.info(f"Parent container: \"{parent_name}\"")

            frame_origin = {
                'x': node['absoluteBoundingBox']['x'],
                'y': node['absoluteBoundingBox']['y']
            }

            slide_number = get_slide_number(parent_name)
            slide_type = detect_slide_type(parent_name, slide_number)

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

    def is_target_frame(self, node: dict[str, Any]) -> bool:
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

    @staticmethod
    def _update_figure_config_with_names(slide_config, blocks):
        # !REFACTOR
        figure_blocks_by_name = {}
        
        for block in blocks:
            if block.sql_type != 'figure':
                continue

            base_name = Extractor.extract_base_figure_name(block.name)
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
                normalized_font_family = normalize_font_family(font_family)
                fill_color = obj.get('color')
                matching_block = figure_blocks_by_name.get(Extractor.extract_base_figure_name(figure_name))
                clean_figure_name = Extractor.extract_base_figure_name(figure_name)
                
                if matching_block is not None:
                    clean_figure_name = Extractor.extract_base_figure_name(matching_block.name)
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


    def _slide_to_dict(self, slide: ExtractedSlide) -> dict[str, Any]:
        """
        Convert slide object to dictionary, using only the text block with the most text for sentence count.
        Remove debug logs. Add slideColors extraction.
        """
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
            sentence_count = count_sentences(text_content)
        if sentence_count == 0:
            sentence_count = 1
        # Extract slideConfig and palette colors if available
        slide_config = {}
        presentation_palette_colors = []
        figma_node = getattr(slide, '_figma_node', None)
        if figma_node:
            slide_config, presentation_palette_colors = Extractor.extract_slide_config(figma_node)
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
            'blocks': [block_to_dict(block, slide_config) for block in slide.blocks],
            'block_count': len(slide.blocks),
            'slideConfig': slide_config,
            'presentationPaletteColors': presentation_palette_colors
        }


    # TO-DO: refactor ==========================================================================
    def collect_enhanced_blocks(self, node: dict[str, Any], frame_origin: dict[str, int], 
                              slide_number: int, parent_container: str) -> list[ExtractedBlock]:
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
            figma_type, sql_type = detect_block_type(node)
            abs_box = node['absoluteBoundingBox']
            left = abs_box['x'] - frame_origin['x']
            top = abs_box['y'] - frame_origin['y']
            dimensions = {
                'x': round5(left),
                'y': round5(top),
                'w': round5(abs_box['width']),
                'h': round5(abs_box['height'])
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
                styles = Extractor.extract_text_styles(node, sql_type)
                z_index = Extractor.extract_z_index(name)
                if z_index == 0:
                    z_index = CONSTANTS.Z_INDEX_DEFAULTS.get(sql_type, CONSTANTS.Z_INDEX_DEFAULTS['default'])
                styles['zIndex'] = z_index
                has_corner_radius, corner_radius = Extractor.extract_corner_radius(node)
                text_content: Optional[str] = None
                text_like_types = ['text', 'blockTitle', 'slideTitle', 'subTitle', 'number', 'email', 'date', 'name', 'percentage']
                if sql_type in text_like_types and node.get('type') == 'TEXT':
                    text_content = node.get('characters', None)
                
                # Extract color information for background and other relevant blocks
                node_color = None
                if sql_type in BLOCKS.BLOCK_TYPES['null_style_types']:
                    node_color = Extractor.extract_color_info(node)[0] # Only get hex color
                
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
    