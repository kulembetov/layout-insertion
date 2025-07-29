from typing import Optional, Any

from api_v1.constants import BLOCKS, SLIDES
from api_v1.services.data_classes import ExtractedBlock, ExtractedSlide
from api_v1.utils.extractors import Extractor
from api_v1.utils.font import normalize_font_family
from api_v1.utils.helpers import safe_in
from api_v1.utils.text import count_words, count_sentences


# don't use / import this class
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
            color_hex, color_var = Extractor.extract_color_info(self.get('node'))
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
        clean_name = Extractor.extract_base_figure_name(self.get('name'))
        self.block_dict['figureName'] = clean_name
        if self.get('node_color'):
            self.block_dict['color'] = self.get('node_color')
        elif safe_in('figure', self.slide_config):
            all_colors, all_fonts = self.__get_colors_and_fonts()
            if all_colors:
                self.block_dict['all_colors'] = list(set(all_colors))
            if all_fonts:
                self.block_dict['all_fonts'] = list(set(all_fonts))

            figure_index = Extractor.extract_figure_index(clean_name)
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
        self.block_dict['figure_info'] = self._extract_figure_info()
        self.block_dict['precompiled_image_info'] = self._extract_precompiled_image_info()

    def _extract_figure_info(self) -> Optional[dict]:
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

    def _extract_precompiled_image_info(self) -> Optional[dict]:
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


def block_to_dict(block: ExtractedBlock, slide_config: Optional[dict] = None):
    # Convert block to dict construction
    return BlockBuilder(block, slide_config).build()


# codeblock for 'slide_to_dict', don't use/import this
def _update_figure_config_with_names(slide_config, blocks):
    # !REFACTOR
    figure_blocks_by_name = {}

    for block in blocks:
        if block.sql_type != 'figure':
            continue

        base_name = Extractor.extract_base_figure_name(block.name)
        figure_blocks_by_name[base_name] = block
        # logger.info(f"[figureBlocks] Found figure block: '{block.name}' -> base_name: '{base_name}'")

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
                # logger.info(
                #     f"[figureConfig] MATCHED: color {color_hex}, figure '{figure_name}' -> color: {fill_color}, font: {normalized_font_family}")
            # else:
                # logger.info(
                #     f"[figureConfig] NO BLOCK MATCH: color {color_hex}, figure '{figure_name}' -> color: {fill_color}, font: {normalized_font_family}")

            figure_obj = {
                "color": fill_color,
                "fontFamily": normalized_font_family,
                "figureName": clean_figure_name
            }
            figure_objects.append(figure_obj)
        new_figure_config[color_hex] = figure_objects
    slide_config['figure'] = new_figure_config
    # logger.info(f"[figureConfig] SUMMARY: Processed {len(figure_blocks_by_name)} figure blocks")


def slide_to_dict(slide: ExtractedSlide) -> dict[str, Any]:
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
            _update_figure_config_with_names(slide_config, slide.blocks)
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
