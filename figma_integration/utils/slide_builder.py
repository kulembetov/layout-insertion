import re

import configuration as config
from figma_integration.models import ExtractedBlock, ExtractedSlide
from log_utils import logs, setup_logger

from .block import BlockUtils
from .color import ColorUtils
from .figure import FigureUtils
from .font import FontUtils
from .text import TextUtils

logger = setup_logger(__name__)


@logs(logger, on=False)
class SlideBuilder:
    @staticmethod
    @logs(logger, on=True)
    def _extract_slide_config(slide_node):
        """Extract slideConfig from the hidden slideColors table in the slide node, including color and fontFamily for each color layer."""
        config_dict = {}
        palette_colors = set()

        if not slide_node or not BlockUtils.get_node_property(slide_node, "children"):
            return config_dict, []

        children_raw = BlockUtils.get_node_property(slide_node, "children")
        if not isinstance(children_raw, list):
            return config_dict, []

        for node_child in children_raw:
            if not isinstance(node_child, dict):
                continue

            if BlockUtils.get_node_property(node_child, "name") == "slideColors":
                logger.info("[slideColors] Found slideColors table in slide")

                children_raw2 = BlockUtils.get_node_property(node_child, "children", [])
                if not isinstance(children_raw2, list):
                    continue

                for node_block in children_raw2:
                    if not isinstance(node_block, dict):
                        continue

                    block_type = BlockUtils.get_node_property(node_block, "name")
                    if not block_type:
                        continue

                    logger.info(f"[slideColors] Processing block type: {block_type}")

                    block_colors = {}
                    children_raw3 = BlockUtils.get_node_property(node_block, "children", [])
                    if not isinstance(children_raw3, list):
                        continue

                    for color_group in children_raw3:
                        if not isinstance(color_group, dict):
                            continue

                        color_hex = BlockUtils.get_node_property(color_group, "name")
                        if not color_hex:
                            continue

                        color_hex = color_hex.lower().strip()
                        palette_colors.add(color_hex)

                        logger.info(f"[slideColors] Processing color group: {color_hex}")

                        block_objs = []
                        children_raw4 = BlockUtils.get_node_property(color_group, "children", [])
                        if not isinstance(children_raw4, list):
                            continue

                        for text_child in children_raw4:
                            if not isinstance(text_child, dict):
                                continue

                            if BlockUtils.is_node_type(text_child, "TEXT"):
                                text_obj = {}

                                color_val, color_var = ColorUtils.extract_color_info(text_child)
                                text_obj["color"] = color_val

                                if color_var and color_var.strip():
                                    text_obj["color_variable"] = color_var
                                    logger.info(f"[slideColors] Found color variable: {color_var} for color: {color_val}")

                                font_family = None
                                style_raw = text_child.get("style")
                                if isinstance(style_raw, dict) and "fontFamily" in style_raw:
                                    font_family = style_raw["fontFamily"]

                                normalized_font = FontUtils.normalize_font_family(font_family)
                                if normalized_font:
                                    text_obj["fontFamily"] = normalized_font

                                if block_type == "figure":
                                    figure_name = BlockUtils.get_node_property(text_child, "name", "").strip()
                                    text_obj["figureName"] = None if not figure_name else figure_name
                                    logger.info(f"[slideColors] Found figure in {color_hex}: name='{figure_name}', color={color_val}, color_var={color_var}, font={font_family}")

                                if color_val or color_var or normalized_font or text_obj.get("figureName"):
                                    block_objs.append(text_obj)

                        if block_objs:
                            block_colors[color_hex] = block_objs

                    if block_colors:
                        config_dict[block_type] = block_colors
                        logger.info(f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups")
                        for color_hex, obj_list in block_colors.items():
                            logger.info(f"[slideConfig]   Color '{color_hex}': {len(obj_list)} objects")
                            if obj_list and logger:
                                first_obj = obj_list[0]
                                logger.info(f"[slideConfig]     Sample object: {first_obj}")

        return config_dict, sorted(palette_colors)

    @staticmethod
    @logs(logger, on=True)
    def _update_figure_config_with_names(slide_config, blocks):
        figure_blocks_info = []
        for block in blocks:
            if block.sql_type == "figure":
                base_name = FigureUtils.extract_base_figure_name(block.name)
                figure_blocks_info.append({"base_name": base_name, "block": block})
                logger.info(f"[figureBlocks] Found figure block: '{block.name}' -> base_name: '{base_name}'")
        new_figure_config = {}
        for color_hex, obj_list in slide_config["figure"].items():
            figure_objects = []

            for obj in obj_list:
                figure_name = obj.get("figureName", "")
                if figure_name:
                    matching_block = None
                    for fig in figure_blocks_info:
                        base_name = fig["base_name"]
                        index_match = re.search(r"_(\d+)$", base_name)
                        if index_match and index_match.group(1) == figure_name:
                            matching_block = fig["block"]
                            break

                    font_family = obj.get("fontFamily")
                    font_family = FontUtils.normalize_font_family(font_family)
                    fill = obj.get("color")

                    clean_figure_name = figure_name

                    found_match = False
                    for fig in figure_blocks_info:
                        base_name = fig["base_name"]
                        index_match = re.search(r"_(\d+)$", base_name)
                        if index_match and index_match.group(1) == figure_name:
                            clean_figure_name = re.sub(r"_(\d+)$", "", base_name)
                            logger.info(f"[figureConfig] Found exact index match for '{figure_name}', using name: '{clean_figure_name}'")
                            found_match = True
                            break

                    if not found_match:
                        for fig in figure_blocks_info:
                            base_name = fig["base_name"]
                            z_index_match = re.search(r"z-index\s*(\d+)", fig["block"].name)
                            if z_index_match and z_index_match.group(1) == figure_name:
                                clean_figure_name = re.sub(r"_(\d+)$", "", base_name)
                                logger.info(f"[figureConfig] Found z-index match for '{figure_name}', using name: '{clean_figure_name}'")
                                found_match = True
                                break

                    if not found_match and len(figure_blocks_info) > 0:
                        first_block = figure_blocks_info[0]
                        clean_figure_name = re.sub(r"_(\d+)$", "", first_block["base_name"])
                        logger.info(f"[figureConfig] No match found for '{figure_name}', using fallback name: '{clean_figure_name}'")

                    if matching_block:
                        logger.info(f"[figureConfig] MATCHED: color {color_hex}, figure '{figure_name}' -> color: {fill}, font: {font_family}")
                    else:
                        logger.info(f"[figureConfig] NO BLOCK MATCH: color {color_hex}, figure '{figure_name}' -> color: {fill}, font: {font_family}")

                    figure_obj = {
                        "color": fill,
                        "fontFamily": font_family,
                        "figureName": None if not figure_blocks_info else clean_figure_name,
                    }
                    figure_objects.append(figure_obj)

            new_figure_config[color_hex] = figure_objects
        slide_config["figure"] = new_figure_config

        logger.info(f"[figureConfig] SUMMARY: Processed {len(figure_blocks_info)} figure blocks")
        for fig_info in figure_blocks_info:
            clean_name = re.sub(r"_(\d+)$", "", fig_info["base_name"])
            logger.info(f"[figureConfig] Block '{fig_info['base_name']}' -> looking for '{clean_name}' in slideColors")

    @staticmethod
    def _extract_slide_type_from_name(frame_name: str) -> str:
        """Extract slide type from the frame name.
        Example: 'one_square_outline_icon_shield_image_right background_0 z-index 0 upload optimalText' -> 'optimalText'
        """
        if not frame_name:
            return "classic"

        parts = frame_name.strip().split()

        skip_patterns = ["upload", "z-index", "background"]

        for part in reversed(parts):
            if not any(part.startswith(pattern) for pattern in skip_patterns) and not part.isdigit():
                if len(part) <= 20 and "_" not in part:
                    return part

        return "classic"

    @staticmethod
    def _block_to_dict(block: ExtractedBlock) -> dict[str, str | int | dict | list | bool]:
        return BlockUtils.build_block_dict(block)

    def slide_to_dict(self, slide: ExtractedSlide) -> dict[str, str | int | dict | list | bool | None]:
        """Convert slide object to dictionary, using only the text block with the most text for sentence count. Remove debug logs. Add slideColors extraction."""
        max_text_block = None
        max_len = 0
        for block in slide.blocks:
            if block.sql_type == "text":
                text_content = getattr(block, "text_content", None)
                if text_content and len(text_content) > max_len:
                    max_text_block = block
                    max_len = len(text_content)
        sentence_count = 1
        if max_text_block:
            text_content = getattr(max_text_block, "text_content", None)
            if text_content:
                sentence_count = TextUtils.count_sentences(text_content)
        if sentence_count == 0:
            sentence_count = 1

        images_count = sum(1 for block in slide.blocks if block.sql_type == "image")

        slide_config = {}
        presentation_palette_colors = []
        figma_node = getattr(slide, "_figma_node", None)
        if figma_node:
            slide_config, presentation_palette_colors = self._extract_slide_config(figma_node)
            if "figure" in slide_config:
                self._update_figure_config_with_names(slide_config, slide.blocks)

        slide_name = slide.frame_name.lower()
        for_generation = "upload" not in slide_name

        extracted_slide_type = self._extract_slide_type_from_name(slide.frame_name)

        columns = None
        container_lower = slide.container_name.lower().strip()
        if container_lower.endswith("cols"):
            try:
                columns = int(container_lower.replace("cols", ""))
            except ValueError:
                columns = None

        return {
            "slide_number": slide.number,
            "container_name": slide.container_name,
            "frame_name": slide.frame_name,
            "slide_type": extracted_slide_type,
            "columns": columns,
            "forGeneration": for_generation,
            "sentences": sentence_count,
            "imagesCount": images_count,
            "frame_id": slide.frame_id,
            "dimensions": slide.dimensions,
            "folder_name": config.SLIDE_NUMBER_TO_FOLDER.get(slide.number, "other"),
            "blocks": [self._block_to_dict(block) for block in slide.blocks],
            "block_count": len(slide.blocks),
            "slideConfig": slide_config,
            "presentationPaletteColors": presentation_palette_colors,
        }


slide_builder = SlideBuilder()
