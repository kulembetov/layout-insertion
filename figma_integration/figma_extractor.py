import os
import re

import requests

import configuration as config
from configuration import TEXT_BLOCK_TYPES, TextHorizontal, TextVertical
from log_utils import logs, setup_logger

from .base import FigmaSession
from .filters import FilterMode
from .models import ExtractedBlock, ExtractedSlide
from .utils.block import BlockUtils
from .utils.block_filter import BlockFilterUtils
from .utils.block_type import BlockTypeUtils
from .utils.color import ColorUtils
from .utils.figure import FigureUtils
from .utils.font import FontUtils
from .utils.helper import HelpUtils
from .utils.text import TextUtils

logger = setup_logger(__name__)


@logs(logger, on=True)
class FigmaExtractor:
    def __init__(self, session: FigmaSession):
        self.session = session

    def round_to_nearest_five(self, value: float) -> int:
        """Round value to nearest 5"""
        return round(value / 5) * 5

    def extract_z_index(self, name: str) -> int:
        """Extract z-index from node name"""
        if "z-index" in name:
            parts = name.split("z-index")
            if len(parts) > 1:
                after = parts[1].strip()
                match = re.findall(r"\d+", after)
                if match:
                    return int(match[0])
        return 0

    def has_z_index_in_name(self, name: str) -> bool:
        """Check if name contains z-index"""
        return "z-index" in name

    def normalize_font_weight(self, weight: int | float | str | None) -> int:
        """Normalize font weight to valid values from config"""
        if weight is None:
            return config.VALID_FONT_WEIGHTS[1]

        try:
            weight_num = int(weight)
        except (ValueError, TypeError):
            return config.VALID_FONT_WEIGHTS[1]

        if weight_num <= 350:
            return config.VALID_FONT_WEIGHTS[0]
        elif weight_num <= 550:
            return config.VALID_FONT_WEIGHTS[1]
        else:
            return config.VALID_FONT_WEIGHTS[2]

    def extract_text_styles(self, node: dict[str, str | int | float | bool | dict | list], sql_type: str) -> dict[str, str | int | float | bool | list]:
        """Extract text styling information with config defaults (no color)."""
        default_style = config.DEFAULT_STYLES.get(sql_type, config.DEFAULT_STYLES["default"])
        styles = {
            "textVertical": default_style.text_vertical,
            "textHorizontal": default_style.text_horizontal,
            "fontSize": default_style.font_size,
            "weight": default_style.weight,
            "textTransform": default_style.text_transform,
        }
        style_raw = node.get("style", {})
        if isinstance(style_raw, dict):
            text_align_vertical_raw = style_raw.get("textAlignVertical", "")
            if isinstance(text_align_vertical_raw, str):
                text_align_vertical = text_align_vertical_raw.lower()
                match text_align_vertical:
                    case "top":
                        styles["textVertical"] = TextVertical.top
                    case "middle" | "center":
                        styles["textVertical"] = TextVertical.middle
                    case "bottom":
                        styles["textVertical"] = TextVertical.bottom
                    case _:
                        pass

            text_align_horizontal_raw = style_raw.get("textAlignHorizontal", "")
            if isinstance(text_align_horizontal_raw, str):
                text_align_horizontal = text_align_horizontal_raw.lower()
                match text_align_horizontal:
                    case "left":
                        styles["textHorizontal"] = TextHorizontal.left
                    case "center":
                        styles["textHorizontal"] = TextHorizontal.center
                    case "right":
                        styles["textHorizontal"] = TextHorizontal.right
                    case _:
                        pass

            if "fontSize" in style_raw:
                font_size_raw = style_raw["fontSize"]
                if isinstance(font_size_raw, (int, float)):
                    styles["fontSize"] = round(font_size_raw)

            if "fontWeight" in style_raw:
                font_weight_raw = style_raw["fontWeight"]
                styles["weight"] = self.normalize_font_weight(font_weight_raw)

        styles["blur"] = self.extract_blur(node)

        result: dict[str, str | int | float | bool | list] = {}
        for key, value in styles.items():
            if isinstance(value, (str, int, float, bool, list)):
                result[key] = value
            else:
                result[key] = str(value)

        return result

    def extract_opacity(self, node: dict[str, str | int | float | bool | dict | list]) -> int | float:
        """Extract opacity from a Figma node"""
        if "opacity" in node:
            opacity = node["opacity"]
            if isinstance(opacity, (int, float)):
                return int(opacity) if opacity == 1.0 else float(opacity)

        fills_raw = node.get("fills")
        if isinstance(fills_raw, list):
            for fill in fills_raw:
                if isinstance(fill, dict):
                    visible = fill.get("visible", True)
                    fill_type = fill.get("type")
                    if visible and fill_type == "SOLID":
                        opacity_raw = fill.get("opacity", 1.0)
                        if isinstance(opacity_raw, (int, float)):
                            return int(opacity_raw) if opacity_raw == 1.0 else float(opacity_raw)

        return 1

    def extract_rotation(self, node: dict[str, str | int | float | bool | dict | list]) -> int:
        """Extract rotation from a Figma node"""
        if "rotation" in node:
            rotation = node["rotation"]
            if isinstance(rotation, (int, float)):
                return int(rotation)

        if "absoluteTransform" in node:
            transform_raw = node["absoluteTransform"]
            if isinstance(transform_raw, list) and len(transform_raw) >= 2:
                return 0

        return 0

    def extract_blur(self, node: dict[str, str | int | float | bool | dict | list]) -> int:
        """Extract layer blur radius from a Figma node, checking nested layers. Returns 0 if no blur."""
        effects_raw = node.get("effects")
        if isinstance(effects_raw, list):
            for effect in effects_raw:
                if isinstance(effect, dict):
                    visible = effect.get("visible", True)
                    effect_type = effect.get("type")
                    if visible and effect_type == "LAYER_BLUR" and "radius" in effect:
                        radius_raw = effect["radius"]
                        if isinstance(radius_raw, (int, float)) and radius_raw > 0:
                            return int(radius_raw)

        children_raw = node.get("children")
        if isinstance(children_raw, list):
            for child in children_raw:
                if isinstance(child, dict):
                    blur_radius = self.extract_blur(child)
                    if blur_radius > 0:
                        return blur_radius

        return 0

    def is_target_frame(self, node: dict[str, str | int | float | bool | dict | list]) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker"""
        if not BlockUtils.get_node_property(node, "absoluteBoundingBox"):
            return False
        marker = getattr(self.session.filter_config, "ready_to_dev_marker", None)
        if marker:
            name = BlockUtils.get_node_property(node, "name", "").lower()
            if marker.lower() not in name:
                return False
        if self.session.filter_config.require_z_index and not self.has_z_index_in_name(BlockUtils.get_node_property(node, "name", "")):
            return False
        abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
        width_match = abs(abs_box["width"] - config.FIGMA_CONFIG.TARGET_WIDTH) < 1
        height_match = abs(abs_box["height"] - config.FIGMA_CONFIG.TARGET_HEIGHT) < 1
        if not (width_match and height_match):
            return False
        area = abs_box["width"] * abs_box["height"]
        if area < self.session.filter_config.min_area:
            return False
        return True

    def should_include_block(self, block: ExtractedBlock) -> bool:
        """Check if block should be included based on filter"""
        return BlockFilterUtils.should_include(block, self.session.filter_config)

    def detect_slide_type(self, container_name: str, slide_number: int) -> str:
        """Detect slide type using only config.py as the source of truth."""
        key = container_name.strip().lower()
        number = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
        return config.SLIDE_NUMBER_TO_TYPE.get(number, "classic")

    def get_slide_number(self, parent_name: str) -> int:
        """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
        key = parent_name.strip().lower()
        result = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)
        if result is None:
            return 1
        return result

    def extract_color_from_fills(self, node: dict) -> tuple[str | None, str | None]:
        return ColorUtils.extract_color_info(node)

    def fetch_all_comments(self) -> dict[str, str]:
        """Fetch all comments from Figma API in a single call and return a mapping of node_id to comment."""
        comments_map = {}
        try:
            logger.info("Fetching comments from Figma API...")
            response = requests.get(
                f"https://api.figma.com/v1/files/{self.session.file_id}/comments",
                headers=self.session.headers,
                timeout=30,
            )
            response.raise_for_status()
            comments_data = response.json()

            logger.info(f"Comments API response keys: {list(comments_data.keys())}")

            if "comments" in comments_data:
                logger.info(f"Total comments in response: {len(comments_data['comments'])}")
                for i, comment in enumerate(comments_data["comments"][:3]):
                    logger.info(f"Comment {i+1}: {comment}")
            else:
                logger.info(f"No 'comments' key found in response. Available keys: {list(comments_data.keys())}")

            for comment in comments_data.get("comments", []):
                client_meta = comment.get("client_meta", {})
                node_id = client_meta.get("node_id")
                message = comment.get("message", "")
                if node_id and message and node_id not in comments_map:
                    comments_map[node_id] = message
                    logger.info(f"Mapped comment for node {node_id}: {message[:50]}...")

            logger.info(f"Successfully mapped {len(comments_map)} comments")
            return comments_map

        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to fetch comments: {e}")
            return {}
        except Exception as e:
            logger.debug(f"Error fetching comments: {e}")
            return {}

    def _should_skip_full_image_block(self, sql_type: str, dimensions: dict[str, int], name: str) -> bool:
        """Check if an image block should be skipped (full-size background images)."""
        name_lower = name.lower()
        is_precompiled = "precompiled" in name_lower
        return sql_type == "image" and dimensions["x"] == 0 and dimensions["y"] == 0 and dimensions["w"] == config.FIGMA_CONFIG.TARGET_WIDTH and dimensions["h"] == config.FIGMA_CONFIG.TARGET_HEIGHT and not is_precompiled

    def _extract_block_styles(self, node: dict, sql_type: str, name: str) -> dict:
        """Extract and compile all styles for a block."""
        base_styles = self.extract_text_styles(node, sql_type)
        styles: dict[str, str | int | float | bool | list] = {}

        for key, value in base_styles.items():
            if isinstance(value, (str, int, float, bool, list)):
                styles[key] = value
            else:
                styles[key] = str(value)

        z_index = self.extract_z_index(name)
        if z_index == 0:
            z_index = config.Z_INDEX_DEFAULTS.get(sql_type, config.Z_INDEX_DEFAULTS["default"])
        styles["zIndex"] = z_index

        has_border_radius, border_radius = BlockUtils.extract_border_radius_from_node(node)
        styles["borderRadius"] = border_radius

        styles["opacity"] = self.extract_opacity(node)

        if sql_type not in TEXT_BLOCK_TYPES:
            styles["blur"] = self.extract_blur(node)

        return styles

    def _extract_text_content(self, node: dict, sql_type: str) -> str | None:
        """Extract text content if the block is a text type."""
        if sql_type in TEXT_BLOCK_TYPES and BlockUtils.is_node_type(node, "TEXT"):
            return BlockUtils.get_node_property(node, "characters", None)
        return None

    def _create_extracted_block(self, node: dict, figma_type: str, sql_type: str, name: str, dimensions: dict, styles: dict, slide_number: int, parent_container: str, text_content: str | None, comments_map: dict[str, str] | None) -> ExtractedBlock:
        """Create an ExtractedBlock instance with all required data."""
        comment = comments_map.get(str(node["id"]), "") if comments_map else ""

        return ExtractedBlock(
            id=str(node["id"]),
            figma_type=figma_type,
            sql_type=sql_type,
            name=name,
            dimensions=dimensions,
            styles=styles,
            slide_number=slide_number,
            parent_container=parent_container,
            is_target=True,
            text_content=text_content,
            comment=comment,
        )

    def collect_blocks(
        self,
        node: dict[str, str | int | float | bool | dict | list],
        frame_origin: dict[str, int],
        slide_number: int,
        parent_container: str,
        comments_map: dict[str, str] | None = None,
    ) -> list[ExtractedBlock]:
        """Recursively collect blocks from a Figma node, filtering and normalizing as needed."""
        blocks: list[ExtractedBlock] = []

        if not BlockUtils.get_node_property(node, "absoluteBoundingBox"):
            return blocks
        if not BlockFilterUtils.should_include(node, self.session.filter_config):
            return blocks

        name = BlockUtils.get_node_property(node, "name", "")
        has_z = self.has_z_index_in_name(name)

        if has_z:
            figma_type, sql_type = BlockTypeUtils.detect_block_type(node)
            abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
            rotation = self.extract_rotation(node)

            dimensions = {
                "x": round(abs_box["x"] - frame_origin["x"]),
                "y": round(abs_box["y"] - frame_origin["y"]),
                "w": round(abs_box["width"]),
                "h": round(abs_box["height"]),
                "rotation": rotation,
            }

            if self._should_skip_full_image_block(sql_type, dimensions, name):
                logger.debug(f"Skipping {sql_type} block {name} (full image {config.FIGMA_CONFIG.TARGET_WIDTH}x{config.FIGMA_CONFIG.TARGET_HEIGHT})")
            else:
                styles = self._extract_block_styles(node, sql_type, name)
                text_content = self._extract_text_content(node, sql_type)

                block = self._create_extracted_block(node, figma_type, sql_type, name, dimensions, styles, slide_number, parent_container, text_content, comments_map)

                if BlockFilterUtils.should_include(block, self.session.filter_config):
                    blocks.append(block)
                    logger.info(f"Added {sql_type} block: {name}")

                    blur_value = styles.get("blur", 0)
                    blur_info = f" | Blur: {blur_value}px" if isinstance(blur_value, (int, float)) and blur_value > 0 else ""
                    logger.debug(f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{blur_info}")

        if BlockUtils.get_node_property(node, "children") and not (getattr(self.session.filter_config, "exclude_hidden", True) and BlockUtils.get_node_property(node, "visible") is False):
            for node_child in BlockUtils.get_node_property(node, "children"):
                blocks.extend(self.collect_blocks(node_child, frame_origin, slide_number, parent_container, comments_map))

        return blocks

    def _extract_slide_config(self, slide_node):
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

    def _update_figure_config_with_names(self, slide_config, blocks):
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

    def extract_slide_type_from_name(self, frame_name: str) -> str:
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

    def traverse_and_extract(
        self,
        node: dict[str, str | int | float | bool | dict | list],
        parent_name: str = "",
        comments_map: dict[str, str] | None = None,
    ) -> list[ExtractedSlide]:
        """Traversal with filtering"""
        slides: list[ExtractedSlide] = []

        if self.is_target_frame(node):
            logger.info(f"Found target frame: \"{node['name']}\"")
            logger.info(f'Parent container: "{parent_name}"')

            abs_box_raw = node.get("absoluteBoundingBox")
            if isinstance(abs_box_raw, dict):
                x_raw = abs_box_raw.get("x")
                y_raw = abs_box_raw.get("y")
                if isinstance(x_raw, (int, float)) and isinstance(y_raw, (int, float)):
                    frame_origin = {
                        "x": int(x_raw),
                        "y": int(y_raw),
                    }
                else:
                    frame_origin = {"x": 0, "y": 0}
            else:
                frame_origin = {"x": 0, "y": 0}

            slide_number = self.get_slide_number(parent_name)

            if self.session.filter_config.mode == FilterMode.SLIDE_GROUP and slide_number not in self.session.filter_config.target_slides:
                return slides

            slide_type = self.detect_slide_type(parent_name, slide_number)

            target_width_raw = config.FIGMA_CONFIG.TARGET_WIDTH
            target_height_raw = config.FIGMA_CONFIG.TARGET_HEIGHT
            if isinstance(target_width_raw, (int, float)) and isinstance(target_height_raw, (int, float)):
                dimensions = {
                    "w": int(target_width_raw),
                    "h": int(target_height_raw),
                }
            else:
                dimensions = {"w": 1200, "h": 675}

            blocks = self.collect_blocks(node, frame_origin, slide_number, parent_name, comments_map)

            if blocks or self.session.filter_config.mode == FilterMode.ALL:
                slide = ExtractedSlide(
                    number=slide_number,
                    container_name=parent_name,
                    frame_name=str(node["name"]),
                    slide_type=slide_type,
                    blocks=blocks,
                    frame_id=str(node["id"]),
                    dimensions=dimensions,
                )
                slide._figma_node = node
                slides.append(slide)
                logger.info(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")

            return slides

        children_raw = node.get("children")
        if isinstance(children_raw, list):
            for child in children_raw:
                if isinstance(child, dict):
                    name_raw = node.get("name", "")
                    parent_name_str = str(name_raw) if name_raw is not None else ""
                    child_slides = self.traverse_and_extract(child, parent_name_str, comments_map)
                    slides.extend(child_slides)

        return slides

    def extract_data(self) -> dict[str, str | dict | list | int]:
        """Main extraction method. Returns extracted slides and metadata, or error info on failure."""
        try:
            response = requests.get(f"https://api.figma.com/v1/files/{self.session.file_id}", headers=self.session.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            comments_map = self.fetch_all_comments()

            pages = BlockUtils.get_node_property(data["document"], config.FigmaKey.CHILDREN, [])
            all_slides = []

            for page in pages:
                logger.info(f"\nProcessing page: {BlockUtils.get_node_property(page, config.FigmaKey.NAME, 'Unnamed')}")
                page_slides = self.traverse_and_extract(page, "", comments_map)
                all_slides.extend(page_slides)

            summary: dict[str, str | int | dict] = {
                "total_slides": len(all_slides),
                "total_blocks": sum(len(slide.blocks) for slide in all_slides),
                "slide_types": {},
                "block_types": {},
                "slide_distribution": {},
            }

            for slide in all_slides:
                slide_type = slide.slide_type
                slide_types_dict = summary.get("slide_types", {})
                if isinstance(slide_types_dict, dict):
                    slide_types_dict[slide_type] = slide_types_dict.get(slide_type, 0) + 1
                    summary["slide_types"] = slide_types_dict

                slide_dist_dict = summary.get("slide_distribution", {})
                if isinstance(slide_dist_dict, dict):
                    slide_dist_dict[slide.number] = slide.container_name
                    summary["slide_distribution"] = slide_dist_dict

                for block in slide.blocks:
                    block_type = block.sql_type
                    block_types_dict = summary.get("block_types", {})
                    if isinstance(block_types_dict, dict):
                        block_types_dict[block_type] = block_types_dict.get(block_type, 0) + 1
                        summary["block_types"] = block_types_dict

            return {
                "metadata": {
                    "file_id": self.session.file_id,
                    "figma_config": config.FIGMA_CONFIG,
                    "extraction_summary": summary,
                    "filter_config": {"mode": self.session.filter_config.mode.value, "target_slides": self.session.filter_config.target_slides, "target_names": self.session.filter_config.target_names, "target_statuses": self.session.filter_config.target_statuses},
                    "sql_generator_compatibility": {
                        "valid_block_types": config.BLOCK_TYPES["block_layout_type_options"],
                        "valid_font_weights": config.VALID_FONT_WEIGHTS,
                        "slide_layout_types": config.SLIDE_LAYOUT_TYPES,
                    },
                },
                "slides": [self._slide_to_dict(slide) for slide in all_slides],
            }

        except requests.exceptions.RequestException as e:
            logger.debug(f"Request error: {e}")
            return {
                "metadata": {"file_id": self.session.file_id, "error": f"Request error: {e}"},
                "slides": [],
            }
        except Exception as e:
            logger.debug(f"Unexpected error: {e}")
            return {
                "metadata": {
                    "file_id": self.session.file_id,
                    "error": f"Unexpected error: {e}",
                },
                "slides": [],
            }

    def _slide_to_dict(self, slide: ExtractedSlide) -> dict[str, str | int | dict | list | bool]:
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

        extracted_slide_type = self.extract_slide_type_from_name(slide.frame_name)

        return {
            "slide_number": slide.number,
            "container_name": slide.container_name,
            "frame_name": slide.frame_name,
            "slide_type": extracted_slide_type,
            "forGeneration": for_generation,
            "sentences": sentence_count,
            "imagesCount": images_count,
            "frame_id": slide.frame_id,
            "dimensions": slide.dimensions,
            "folder_name": config.SLIDE_NUMBER_TO_FOLDER.get(slide.number, "other"),
            "blocks": [self._block_to_dict(block, slide_config) for block in slide.blocks],
            "block_count": len(slide.blocks),
            "slideConfig": slide_config,
            "presentationPaletteColors": presentation_palette_colors,
        }

    def _block_to_dict(self, block: ExtractedBlock, slide_config=None) -> dict[str, str | int | dict | list | bool]:
        return BlockUtils.build_block_dict(block, slide_config)

    def save_results(self, data: dict[str, str | dict | list | int], output_file: str | None = None) -> str:
        """Save extracted data to file"""
        if not data:
            return ""
        output_dir_raw = config.FIGMA_CONFIG.OUTPUT_DIR
        if not isinstance(output_dir_raw, str):
            output_dir_raw = str(output_dir_raw)
        if not os.path.exists(output_dir_raw):
            os.makedirs(output_dir_raw)

        if not output_file:
            output_file_raw = config.FIGMA_CONFIG.OUTPUT_FILE
            if not isinstance(output_file_raw, str):
                output_file_raw = str(output_file_raw)
            output_file = f"{output_dir_raw}/{output_file_raw}_config_compatible.json"

        HelpUtils.json_dump(data, output_file)

        logger.info(f"\nData saved: {output_file}")

        if isinstance(data, dict):
            metadata = data.get("metadata", {})
            if isinstance(metadata, dict):
                summary = metadata.get("extraction_summary", {})
                if isinstance(summary, dict):
                    logger.info("\nEXTRACTION SUMMARY:")
                    logger.info(f"   Total slides: {summary.get('total_slides', 0)}")
                    logger.info(f"   Total blocks: {summary.get('total_blocks', 0)}")
                    logger.info(f"   Slide types: {summary.get('slide_types', {})}")
                    logger.info(f"   Block types: {summary.get('block_types', {})}")
                    logger.info(f"   Distribution: {summary.get('slide_distribution', {})}")

        return output_file
