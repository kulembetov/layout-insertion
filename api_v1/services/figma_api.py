import requests

from typing import Any, Optional
from log_utils import setup_logger, logs

from .data_classes import ExtractedBlock, ExtractedSlide
from .filters.filter_settings import FilterMode, FilterConfig

from api_v1.utils.helpers import round5, get_slide_number
from api_v1.utils.checkers import Checker
from api_v1.utils.filters import should_include
from api_v1.utils.extractors import Extractor
from api_v1.utils.builders import slide_to_dict
from api_v1.utils.detectors import detect_slide_type, detect_block_type

from api_v1.constants import BLOCKS, SLIDES, CONSTANTS


logger = setup_logger(__name__)

@logs(logger, on=True)
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

    @logs(logger, on=True)
    def fetch_comments(self) -> dict:
        """Fetch comments from the Figma API and map them by node_id with full metadata."""
        try:
            response = requests.get(
                f"https://api.figma.com/v1/files/{self.file_id}/comments",
                headers=self.headers
            )
            response.raise_for_status()
            comments_data = response.json().get("comments", [])
            node_comments = {}

            for comment in comments_data:
                client_meta = comment.get("client_meta")
                comment_info = {
                    "message": comment.get("message", ""),
                    "user": comment.get("user", {}),
                    "created_at": comment.get("created_at"),
                    "resolved_at": comment.get("resolved_at"),
                    "comment_id": comment.get("id"),
                    "parent_id": comment.get("parent_id"),
                }

                if isinstance(client_meta, list):
                    for meta in client_meta:
                        node_id = meta.get("node_id")
                        if node_id:
                            node_comments.setdefault(node_id, []).append(comment_info)
                elif isinstance(client_meta, dict):
                    node_id = client_meta.get("node_id")
                    if node_id:
                        node_comments.setdefault(node_id, []).append(comment_info)

            logger.info(f"Fetched {len(comments_data)} comments for {len(node_comments)} nodes")
            if node_comments:
                logger.info(
                    f"Comment distribution: {list(node_comments.keys())[:5]}...")  # Show first 5 node IDs
            return node_comments

        except Exception as e:
            logger.debug(f"Failed to fetch comments: {e}")
            return {}


    # =========== Extract codeblocks ==============
    @logs(logger, on=True)
    def _get_slides(self) -> list[ExtractedSlide]:
        pages = self.fetch()
        all_slides = []
        for page in pages:
            logger.info(f"\nProcessing page: {page.get('name', 'Unnamed')}")
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
            comments = self.fetch_comments()

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
                'slides': [slide_to_dict(slide, comments) for slide in all_slides]
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
    @logs(logger, on=True)
    def traverse_and_extract(self, node: dict[str, Any], parent_name: str = "") -> list[ExtractedSlide]:
        """Enhanced traversal with filtering"""
        slides = []

        if self.is_target_frame(node):
            logger.info(f"Found target frame: \"{node['name']}\"")
            logger.info(f"Parent container: \"{parent_name}\"")

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
                logger.info(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")
            
            return slides

        # Continue traversing children
        if node.get('children'):
            for child in node['children']:
                child_slides = self.traverse_and_extract(child, node['name'])
                slides.extend(child_slides)
        
        return slides


    def is_target_frame(self, node: dict[str, Any]) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker."""

        if not node.get('absoluteBoundingBox'):
            return False
        
        if self.filter_config.require_z_index and not Checker.check_z_index(node.get('name', '')):
            return False
        
        if self.filter_config.mode == FilterMode.READY_TO_DEV:
            dev_status = node.get('devStatus', {}).get('type')
            if dev_status != "READY_FOR_DEV":
                return False
    
        if not Checker.check_dimensions(node['absoluteBoundingBox']):
            return False
        
        if not Checker.check_min_area(
            node['absoluteBoundingBox'], self.filter_config.min_area
        ):
            return False
        
        return True


    # TO-DO: refactor ==========================================================================
    @logs(logger, on=True)
    def collect_enhanced_blocks(self, node: dict[str, Any], frame_origin: dict[str, int], 
                              slide_number: int, parent_container: str) -> list[ExtractedBlock]:
        blocks = []
        if not node.get('absoluteBoundingBox'):
            return blocks
        
        if self.filter_config.mode == FilterMode.READY_TO_DEV:
            dev_status = node.get('devStatus', {}).get('type')
            if dev_status != "READY_FOR_DEV":
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
                logger.debug(f"Skipping {sql_type} block {name} (full image 1200x675)")
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
                    logger.info(f"Added {sql_type} block: {name}")
                    color_info = f" | Color: {node_color}" if node_color else ""
                    logger.info(
                        f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{color_info}",
                    )
        # Recursively process children (skip children of hidden nodes)
        if node.get('children') and not (getattr(self.filter_config, 'exclude_hidden', True) and node.get('visible') is False):
            for child in node['children']:
                blocks.extend(self.collect_enhanced_blocks(child, frame_origin, slide_number, parent_container))
        return blocks
