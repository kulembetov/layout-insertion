"""
Complete Figma to SQL Generator Integration
Self-contained file with all necessary classes included.
Fully compatible with config.py specifications.
"""

import argparse
import json
import logging
import math
import os
import re
import shutil
from dataclasses import dataclass, field
from enum import Enum

import config
import requests

TEXT_BLOCK_TYPES = [
    "text",
    "blockTitle",
    "slideTitle",
    "subTitle",
    "number",
    "email",
    "date",
    "name",
    "percentage",
]

block_logger = None
block_log_handler = None


def setup_block_logger(output_dir):
    global block_logger, block_log_handler
    if block_logger and block_log_handler:
        block_logger.removeHandler(block_log_handler)
    block_logger = logging.getLogger("block_processing")
    block_logger.setLevel(logging.INFO)
    log_path = os.path.join(output_dir, "figma.log")
    os.makedirs(output_dir, exist_ok=True)
    block_log_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    block_log_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    block_logger.addHandler(block_log_handler)


class FilterMode(Enum):
    ALL = "all"
    SPECIFIC_SLIDES = "specific_slides"
    SPECIFIC_BLOCKS = "specific_blocks"
    BY_TYPE = "by_type"


@dataclass
class FilterConfig:
    mode: FilterMode = FilterMode.ALL
    target_slides: list[int] = field(default_factory=list)
    target_block_types: list[str] = field(default_factory=list)
    target_containers: list[str] = field(default_factory=list)
    require_z_index: bool = True
    min_area: int = 0
    exclude_hidden: bool = True
    ready_to_dev_marker: str | None = None


@dataclass
class ExtractedBlock:
    id: str
    figma_type: str
    sql_type: str
    name: str
    dimensions: dict[str, int]
    styles: dict[str, str | int | float | bool | list]
    slide_number: int
    parent_container: str
    is_target: bool = False
    text_content: str | None = None
    figure_info: dict[str, str | int | float | bool] = field(default_factory=dict)
    precompiled_image_info: dict[str, str | int | float | bool] = field(default_factory=dict)
    comment: str | None = None


@dataclass
class ExtractedSlide:
    number: int
    container_name: str
    frame_name: str
    slide_type: str
    blocks: list[ExtractedBlock]
    frame_id: str
    dimensions: dict[str, int]
    _figma_node: dict | None = None


class BlockTypeUtils:
    @staticmethod
    def detect_block_type(node: dict) -> tuple[str, str]:
        """Detect block type from a Figma node, returning (figma_type, sql_type). Always returns a valid sql_type."""
        name = node.get("name", "")
        node_type = node.get("type", "")
        clean_name = re.sub(r"\s*z-index.*$", "", name)
        sorted_patterns = sorted(
            config.FIGMA_TO_SQL_BLOCK_MAPPING.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )
        for pattern, sql_type in sorted_patterns:
            if pattern in clean_name.lower():
                if sql_type in config.BLOCK_TYPES["block_layout_type_options"]:
                    return pattern, sql_type
        if node_type == "TEXT":
            sql_type = BlockTypeUtils._detect_text_block_type(clean_name)
            if sql_type in config.BLOCK_TYPES["block_layout_type_options"]:
                return sql_type, sql_type
        elif node_type in ["RECTANGLE", "FRAME", "GROUP"]:
            sql_type = BlockTypeUtils._detect_text_block_type(clean_name)
            if sql_type in config.BLOCK_TYPES["block_layout_type_options"]:
                return sql_type, sql_type
        return "text", "text"

    @staticmethod
    def _normalize_type_name(name: str) -> str:
        name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
        name = name.replace("-", "_").replace(" ", "_").lower()
        return name

    @staticmethod
    def _detect_text_block_type(name: str) -> str:
        norm = BlockTypeUtils._normalize_type_name(name)
        norm_flat = norm.replace("_", "")
        for pattern, sql_type in config.FIGMA_TO_SQL_BLOCK_MAPPING.items():
            if pattern in norm_flat:
                return sql_type
        return "text"


class TextUtils:
    @staticmethod
    def count_words(text: str) -> int:
        if not text:
            return 0
        return len([w for w in re.split(r"\s+", text) if w.strip()])

    @staticmethod
    def count_sentences(text: str) -> int:
        if not text:
            return 0
        split_result = [s for s in re.split(r"[.!?]", text)]
        n = len([s for s in split_result if s.strip()])
        return n if n > 0 else 1


class FigureUtils:
    @staticmethod
    def extract_base_figure_name(name: str) -> str:
        """Extract the base figure name from a block name (e.g., 'figure (logoRfs_0)' -> 'logoRfs')."""
        if not name:
            return ""
        name_match = re.search(r"\(([^)]+)\)", name)
        if name_match:
            base_name = name_match.group(1)
            base_name = re.sub(r"_(\d+)$", "", base_name)
            return base_name
        return name

    @staticmethod
    def extract_figure_index(name: str) -> str:
        """Extract the trailing index (e.g., '_2') from a figure name, or return ''."""
        if not name:
            return ""
        index_match = re.search(r"_(\d+)$", name)
        if index_match:
            return index_match.group(1)
        return ""


class BlockUtils:
    @staticmethod
    def build_block_dict(block, slide_config: dict | None = None) -> dict:
        """
        Build a block dictionary from an ExtractedBlock or dict and optional slide_config.
        This is the single source of truth for block dict construction.
        Adds figure_info and precompiled_image_info if relevant.
        Border radius is now included in styles dictionary.
        """
        get = (lambda k: block.get(k, None)) if isinstance(block, dict) else (lambda k: getattr(block, k, None))
        styles = get("styles") or {}

        block_dict = {
            "id": get("id"),
            "name": get("name"),
            "figma_type": get("figma_type"),
            "sql_type": get("sql_type"),
            "dimensions": get("dimensions"),
            "styles": styles,
            "is_target": get("is_target"),
            "needs_null_styles": get("sql_type") in config.BLOCK_TYPES["null_style_types"],
            "needs_z_index": get("sql_type") in config.BLOCK_TYPES["z_index_types"],
            "comment": get("comment"),
        }
        text_content = get("text_content")
        if isinstance(block, dict) and "words" in block and block["words"] is not None:
            block_dict["words"] = block["words"]
        else:
            block_dict["words"] = TextUtils.count_words(text_content)
        block_dict["figure_info"] = BlockUtils.extract_figure_info(block, slide_config)
        block_dict["precompiled_image_info"] = BlockUtils.extract_precompiled_image_info(block, slide_config)
        return block_dict

    @staticmethod
    def extract_figure_info(block, slide_config=None):
        """Extract and return figure_info dict for a figure block, or None if not a figure."""
        if getattr(block, "sql_type", None) != "figure":
            return None
        info = {
            "id": getattr(block, "id", None),
            "name": getattr(block, "name", None),
        }
        return info

    @staticmethod
    def extract_precompiled_image_info(block, slide_config=None):
        """Extract and return precompiled_image_info dict for a precompiled image block, or None if not applicable."""
        if getattr(block, "sql_type", None) != "image":
            return None
        name = getattr(block, "name", "")
        if not name.lower().startswith("image precompiled"):
            return None
        info = {
            "id": getattr(block, "id", None),
            "name": name,
        }
        return info

    @staticmethod
    def extract_border_radius_from_node(node: dict) -> tuple[bool, list[int]]:
        """Extract corner radius from a Figma node, map to border radius and returns (has_border_radius, [tl, tr, br, bl])"""
        border_radius = [0, 0, 0, 0]
        has_border_radius = False
        if "cornerRadius" in node:
            radius = node["cornerRadius"]
            if isinstance(radius, (int, float)) and radius > 0:
                border_radius = [int(radius)] * 4
                has_border_radius = True
        if "rectangleCornerRadii" in node:
            radii = node["rectangleCornerRadii"]
            if isinstance(radii, list) and len(radii) == 4:
                border_radius = [int(r) for r in radii]
                has_border_radius = any(r > 0 for r in border_radius)
        return has_border_radius, border_radius

    @staticmethod
    def extract_blur_from_node(node: dict) -> int:
        """Extract layer blur radius from a Figma node, checking nested layers. Returns 0 if no blur."""
        effects = node.get("effects")
        if effects and isinstance(effects, list):
            for effect in effects:
                if effect.get("visible", True) and effect.get("type") == "LAYER_BLUR" and "radius" in effect:
                    radius = effect["radius"]
                    if isinstance(radius, (int, float)) and radius > 0:
                        return int(radius)

        children = node.get("children")
        if children and isinstance(children, list):
            for child in children:
                blur_radius = BlockUtils.extract_blur_from_node(child)
                if blur_radius > 0:
                    return blur_radius

        return 0

    @staticmethod
    def get_node_property(node: dict, key: str, default=None):
        return node.get(key, default)

    @staticmethod
    def is_node_type(node: dict, node_type: str) -> bool:
        return node.get("type") == node_type


class ColorUtils:
    @staticmethod
    def extract_color_info(node: dict) -> tuple[str | None, str | None]:
        """
        Extracts the first visible fill color/gradient and its variable/style from a Figma node.
        Returns (hex_or_gradient_color, color_variable_id, gradient_css).
        """

        fills = node.get("fills")
        if fills and isinstance(fills, list):
            fill = fills[0]

            fill_type = fill.get("type")

            if fill_type == "SOLID" and fill.get("visible", True) and "color" in fill:
                c = fill["color"]
                r = int(round(c.get("r", 0) * 255))
                g = int(round(c.get("g", 0) * 255))
                b = int(round(c.get("b", 0) * 255))
                a = fill.get("opacity", c.get("a", 1))
                if a < 1:
                    hex_or_gradient_color = f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
                else:
                    hex_or_gradient_color = f"#{r:02x}{g:02x}{b:02x}"
                color_variable = None
                if "boundVariables" in fill and "color" in fill["boundVariables"]:
                    color_variable = fill["boundVariables"]["color"].get("id")
                elif "fillStyleId" in fill:
                    color_variable = fill["fillStyleId"]
                return hex_or_gradient_color, color_variable

            elif fill.get("visible", True) and fill_type in ["GRADIENT_LINEAR", "GRADIENT_RADIAL", "GRADIENT_ANGULAR", "GRADIENT_DIAMOND"]:
                hex_or_gradient_color = ColorUtils._create_gradient_css(fill)
                color_variable = None

                if "boundVariables" in fill and "color" in fill["boundVariables"]:
                    color_variable = fill["boundVariables"]["color"].get("id")
                elif "fillStyleId" in fill:
                    color_variable = fill["fillStyleId"]
                return hex_or_gradient_color, color_variable

        color = node.get("color")
        if color and isinstance(color, str):
            return color.lower(), None
        return None, None

    @staticmethod
    def _create_gradient_css(fill: dict) -> str:
        """
        Creates CSS gradient string from Figma gradient fill.
        """
        gradient_type = fill.get("type")
        gradient_stops = fill.get("gradientStops", [])
        gradient_handle_positions = fill.get("gradientHandlePositions", [])

        if not gradient_stops:
            return ""

        css_stops = []
        for stop in gradient_stops:
            color = stop.get("color", {})
            position = stop.get("position", 0)

            r = int(round(color.get("r", 0) * 255))
            g = int(round(color.get("g", 0) * 255))
            b = int(round(color.get("b", 0) * 255))
            a = color.get("a", 1)

            if a < 1:
                hex_color = f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
            else:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"

            percentage = int(position * 100)
            css_stops.append(f"{hex_color} {percentage}%")

        if gradient_type == "GRADIENT_LINEAR":
            angle = ColorUtils._calculate_linear_angle(gradient_handle_positions)
            return f"linear-gradient({angle}deg\\, {'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_RADIAL":
            return f"radial-gradient(circle\\, {'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_ANGULAR":
            return f"conic-gradient({'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_DIAMOND":
            return f"radial-gradient(ellipse at center\\, {'\\, '.join(css_stops)})"

        return ""

    @staticmethod
    def _calculate_linear_angle(handle_positions: list) -> int:
        """
        Calculate the angle for linear gradient from handle positions.
        Returns angle in degrees (0-360).
        """
        if len(handle_positions) < 2:
            return 0

        start = handle_positions[0]
        end = handle_positions[1]

        dx = end.get("x", 0) - start.get("x", 0)
        dy = end.get("y", 0) - start.get("y", 0)

        angle_rad = math.atan2(dy, dx)

        angle_deg = math.degrees(angle_rad)
        angle_deg = (angle_deg + 360) % 360

        return int(angle_deg)


class FontUtils:
    @staticmethod
    def normalize_font_family(font_family: str) -> str:
        if not font_family:
            return ""
        return re.sub(
            r"[^a-z0-9_]",
            "",
            font_family.strip().lower().replace(" ", "_").replace("-", "_"),
        )


class BlockFilterUtils:
    @staticmethod
    def should_include_node_or_block(node_or_block, filter_config) -> bool:
        """
        Centralized logic for whether a node/block should be included based on filter_config.
        Handles z-index, marker, visibility, and filter mode.
        Accepts either a Figma node (dict) or an ExtractedBlock/dict.
        """
        get = (lambda k: node_or_block.get(k, None)) if isinstance(node_or_block, dict) else (lambda k: getattr(node_or_block, k, None))
        if getattr(filter_config, "exclude_hidden", True) and get("visible") is False:
            return False
        marker = getattr(filter_config, "ready_to_dev_marker", None)
        if marker:
            name = get("name") or ""
            if marker.lower() not in name.lower():
                return False
        if getattr(filter_config, "require_z_index", True):
            name = get("name") or ""
            if "z-index" not in name:
                return False
        mode = getattr(filter_config, "mode", None)
        if mode == FilterMode.ALL:
            return True
        if mode == FilterMode.SPECIFIC_SLIDES:
            slide_number = get("slide_number") or get("slideNumber")
            if slide_number is not None:
                return slide_number in getattr(filter_config, "target_slides", [])
        if mode == FilterMode.SPECIFIC_BLOCKS:
            sql_type = get("sql_type")
            if sql_type is not None:
                return sql_type in getattr(filter_config, "target_block_types", [])
        if mode == FilterMode.BY_TYPE:
            parent_container = get("parent_container")
            if parent_container is not None:
                return parent_container in getattr(filter_config, "target_containers", [])
        return True


class LogUtils:
    @staticmethod
    def log_block_event(message, level="info"):
        """Unified logging for block/frame events, respects config.VERBOSE."""
        global block_logger
        if block_logger:
            if level == "debug":
                block_logger.debug(message)
            else:
                block_logger.info(message)
        if hasattr(config, "VERBOSE") and getattr(config, "VERBOSE", False):
            print(message)


class FigmaExtractor:
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
        self.headers = {"X-Figma-Token": token}

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
        defaults = config.DEFAULT_STYLES.get(sql_type, config.DEFAULT_STYLES["default"])
        styles = {
            "textVertical": defaults["text_vertical"],
            "textHorizontal": defaults["text_horizontal"],
            "fontSize": defaults["font_size"],
            "weight": defaults["weight"],
            "textTransform": defaults["text_transform"],
        }
        style_raw = node.get("style", {})
        if isinstance(style_raw, dict):
            text_align_vertical_raw = style_raw.get("textAlignVertical", "")
            if isinstance(text_align_vertical_raw, str):
                text_align_vertical = text_align_vertical_raw.lower()
                if text_align_vertical in ["top", "middle", "bottom"]:
                    styles["textVertical"] = text_align_vertical
                elif text_align_vertical == "center":
                    styles["textVertical"] = "middle"

            text_align_horizontal_raw = style_raw.get("textAlignHorizontal", "")
            if isinstance(text_align_horizontal_raw, str):
                text_align_horizontal = text_align_horizontal_raw.lower()
                if text_align_horizontal in ["left", "center", "right"]:
                    styles["textHorizontal"] = text_align_horizontal

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
        marker = getattr(self.filter_config, "ready_to_dev_marker", None)
        if marker:
            name = BlockUtils.get_node_property(node, "name", "").lower()
            if marker.lower() not in name:
                return False
        if self.filter_config.require_z_index and not self.has_z_index_in_name(BlockUtils.get_node_property(node, "name", "")):
            return False
        abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
        width_match = abs(abs_box["width"] - config.FIGMA_CONFIG["TARGET_WIDTH"]) < 1
        height_match = abs(abs_box["height"] - config.FIGMA_CONFIG["TARGET_HEIGHT"]) < 1
        if not (width_match and height_match):
            return False
        area = abs_box["width"] * abs_box["height"]
        if area < self.filter_config.min_area:
            return False
        return True

    def should_include_block(self, block: ExtractedBlock) -> bool:
        """Check if block should be included based on filter"""
        return BlockFilterUtils.should_include_node_or_block(block, self.filter_config)

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
            LogUtils.log_block_event("Fetching comments from Figma API...")
            response = requests.get(
                f"https://api.figma.com/v1/files/{self.file_id}/comments",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            comments_data = response.json()

            LogUtils.log_block_event(f"Comments API response keys: {list(comments_data.keys())}")

            if "comments" in comments_data:
                LogUtils.log_block_event(f"Total comments in response: {len(comments_data['comments'])}")
                for i, comment in enumerate(comments_data["comments"][:3]):
                    LogUtils.log_block_event(f"Comment {i+1}: {comment}")
            else:
                LogUtils.log_block_event(f"No 'comments' key found in response. Available keys: {list(comments_data.keys())}")

            for comment in comments_data.get("comments", []):
                client_meta = comment.get("client_meta", {})
                node_id = client_meta.get("node_id")
                message = comment.get("message", "")
                if node_id and message and node_id not in comments_map:
                    comments_map[node_id] = message
                    LogUtils.log_block_event(f"Mapped comment for node {node_id}: {message[:50]}...")

            LogUtils.log_block_event(f"Successfully mapped {len(comments_map)} comments")
            return comments_map

        except requests.exceptions.RequestException as e:
            LogUtils.log_block_event(f"Failed to fetch comments: {e}", level="debug")
            return {}
        except Exception as e:
            LogUtils.log_block_event(f"Error fetching comments: {e}", level="debug")
            return {}

    def _should_skip_full_image_block(self, sql_type: str, dimensions: dict[str, int], name: str) -> bool:
        """Check if an image block should be skipped (full-size background images)."""
        return False

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
        if not BlockFilterUtils.should_include_node_or_block(node, self.filter_config):
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
                LogUtils.log_block_event(
                    f"Skipping {sql_type} block {name} (full image {config.FIGMA_CONFIG['TARGET_WIDTH']}x{config.FIGMA_CONFIG['TARGET_HEIGHT']})",
                    level="debug",
                )
            else:
                styles = self._extract_block_styles(node, sql_type, name)
                text_content = self._extract_text_content(node, sql_type)

                block = self._create_extracted_block(node, figma_type, sql_type, name, dimensions, styles, slide_number, parent_container, text_content, comments_map)

                if BlockFilterUtils.should_include_node_or_block(block, self.filter_config):
                    blocks.append(block)
                    LogUtils.log_block_event(f"Added {sql_type} block: {name}")

                    blur_value = styles.get("blur", 0)
                    blur_info = f" | Blur: {blur_value}px" if isinstance(blur_value, (int, float)) and blur_value > 0 else ""
                    LogUtils.log_block_event(
                        f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{blur_info}",
                        level="debug",
                    )

        if BlockUtils.get_node_property(node, "children") and not (getattr(self.filter_config, "exclude_hidden", True) and BlockUtils.get_node_property(node, "visible") is False):
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
                if block_logger:
                    block_logger.info("[slideColors] Found slideColors table in slide")

                children_raw2 = BlockUtils.get_node_property(node_child, "children", [])
                if not isinstance(children_raw2, list):
                    continue

                for node_block in children_raw2:
                    if not isinstance(node_block, dict):
                        continue

                    block_type = BlockUtils.get_node_property(node_block, "name")
                    if not block_type:
                        continue

                    if block_logger:
                        block_logger.info(f"[slideColors] Processing block type: {block_type}")

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

                        if block_logger:
                            block_logger.info(f"[slideColors] Processing color group: {color_hex}")

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
                                    if block_logger:
                                        block_logger.info(f"[slideColors] Found color variable: {color_var} for color: {color_val}")

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
                                    if block_logger:
                                        block_logger.info(f"[slideColors] Found figure in {color_hex}: name='{figure_name}', color={color_val}, color_var={color_var}, font={font_family}")

                                if color_val or color_var or normalized_font or text_obj.get("figureName"):
                                    block_objs.append(text_obj)

                        if block_objs:
                            block_colors[color_hex] = block_objs

                    if block_colors:
                        config_dict[block_type] = block_colors
                        if block_logger:
                            block_logger.info(f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups")
                            for color_hex, obj_list in block_colors.items():
                                block_logger.info(f"[slideConfig]   Color '{color_hex}': {len(obj_list)} objects")
                                if obj_list and block_logger:
                                    first_obj = obj_list[0]
                                    block_logger.info(f"[slideConfig]     Sample object: {first_obj}")

        return config_dict, sorted(palette_colors)

    def _update_figure_config_with_names(self, slide_config, blocks):
        figure_blocks_info = []
        for block in blocks:
            if block.sql_type == "figure":
                base_name = FigureUtils.extract_base_figure_name(block.name)
                figure_blocks_info.append({"base_name": base_name, "block": block})
                if block_logger:
                    block_logger.info(f"[figureBlocks] Found figure block: '{block.name}' -> base_name: '{base_name}'")
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
                            if block_logger:
                                block_logger.info(f"[figureConfig] Found exact index match for '{figure_name}', using name: '{clean_figure_name}'")
                            found_match = True
                            break

                    if not found_match:
                        for fig in figure_blocks_info:
                            base_name = fig["base_name"]
                            z_index_match = re.search(r"z-index\s*(\d+)", fig["block"].name)
                            if z_index_match and z_index_match.group(1) == figure_name:
                                clean_figure_name = re.sub(r"_(\d+)$", "", base_name)
                                if block_logger:
                                    block_logger.info(f"[figureConfig] Found z-index match for '{figure_name}', using name: '{clean_figure_name}'")
                                found_match = True
                                break

                    if not found_match and len(figure_blocks_info) > 0:
                        first_block = figure_blocks_info[0]
                        clean_figure_name = re.sub(r"_(\d+)$", "", first_block["base_name"])
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
                        "figureName": None if not figure_blocks_info else clean_figure_name,
                    }
                    figure_objects.append(figure_obj)

            new_figure_config[color_hex] = figure_objects
        slide_config["figure"] = new_figure_config

        if block_logger:
            block_logger.info(f"[figureConfig] SUMMARY: Processed {len(figure_blocks_info)} figure blocks")
            for fig_info in figure_blocks_info:
                clean_name = re.sub(r"_(\d+)$", "", fig_info["base_name"])
                block_logger.info(f"[figureConfig] Block '{fig_info['base_name']}' -> looking for '{clean_name}' in slideColors")

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
            LogUtils.log_block_event(f"Found target frame: \"{node['name']}\"")
            LogUtils.log_block_event(f'Parent container: "{parent_name}"')

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

            if self.filter_config.mode == FilterMode.SPECIFIC_SLIDES and slide_number not in self.filter_config.target_slides:
                return slides

            slide_type = self.detect_slide_type(parent_name, slide_number)

            target_width_raw = config.FIGMA_CONFIG["TARGET_WIDTH"]
            target_height_raw = config.FIGMA_CONFIG["TARGET_HEIGHT"]
            if isinstance(target_width_raw, (int, float)) and isinstance(target_height_raw, (int, float)):
                dimensions = {
                    "w": int(target_width_raw),
                    "h": int(target_height_raw),
                }
            else:
                dimensions = {"w": 1200, "h": 675}

            blocks = self.collect_blocks(node, frame_origin, slide_number, parent_name, comments_map)

            if blocks or self.filter_config.mode == FilterMode.ALL:
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
                LogUtils.log_block_event(f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks")

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
            response = requests.get(f"https://api.figma.com/v1/files/{self.file_id}", headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            comments_map = self.fetch_all_comments()

            pages = BlockUtils.get_node_property(data["document"], config.FIGMA_KEY_CHILDREN, [])
            all_slides = []

            for page in pages:
                LogUtils.log_block_event(f"\nProcessing page: {BlockUtils.get_node_property(page, config.FIGMA_KEY_NAME, 'Unnamed')}")
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
                    "file_id": self.file_id,
                    "figma_config": config.FIGMA_CONFIG,
                    "extraction_summary": summary,
                    "filter_config": {
                        "mode": self.filter_config.mode.value,
                        "target_slides": self.filter_config.target_slides,
                        "target_block_types": self.filter_config.target_block_types,
                        "target_containers": self.filter_config.target_containers,
                    },
                    "sql_generator_compatibility": {
                        "valid_block_types": config.BLOCK_TYPES["block_layout_type_options"],
                        "valid_font_weights": config.VALID_FONT_WEIGHTS,
                        "slide_layout_types": config.SLIDE_LAYOUT_TYPES,
                    },
                },
                "slides": [self._slide_to_dict(slide) for slide in all_slides],
            }

        except requests.exceptions.RequestException as e:
            LogUtils.log_block_event(f"Request error: {e}", level="debug")
            return {
                "metadata": {"file_id": self.file_id, "error": f"Request error: {e}"},
                "slides": [],
            }
        except Exception as e:
            LogUtils.log_block_event(f"Unexpected error: {e}", level="debug")
            return {
                "metadata": {
                    "file_id": self.file_id,
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
        output_dir_raw = config.FIGMA_CONFIG["OUTPUT_DIR"]
        if not isinstance(output_dir_raw, str):
            output_dir_raw = str(output_dir_raw)
        if not os.path.exists(output_dir_raw):
            os.makedirs(output_dir_raw)

        if not output_file:
            output_file_raw = config.FIGMA_CONFIG["OUTPUT_FILE"]
            if not isinstance(output_file_raw, str):
                output_file_raw = str(output_file_raw)
            output_file = f"{output_dir_raw}/{output_file_raw}_config_compatible.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        LogUtils.log_block_event(f"\nData saved: {output_file}")

        if isinstance(data, dict):
            metadata = data.get("metadata", {})
            if isinstance(metadata, dict):
                summary = metadata.get("extraction_summary", {})
                if isinstance(summary, dict):
                    LogUtils.log_block_event("\nEXTRACTION SUMMARY:")
                    LogUtils.log_block_event(f"   Total slides: {summary.get('total_slides', 0)}")
                    LogUtils.log_block_event(f"   Total blocks: {summary.get('total_blocks', 0)}")
                    LogUtils.log_block_event(f"   Slide types: {summary.get('slide_types', {})}")
                    LogUtils.log_block_event(f"   Block types: {summary.get('block_types', {})}")
                    LogUtils.log_block_event(f"   Distribution: {summary.get('slide_distribution', {})}")

        return output_file


class FigmaToSQLIntegrator:
    """Integrates Figma extraction with SQL generation"""

    def __init__(self, figma_file_id: str, figma_token: str):
        self.figma_file_id = figma_file_id
        self.figma_token = figma_token

    def extract_specific_slides(self, slide_numbers: list[int]) -> dict[str, str | dict | list | int]:
        """Extract specific slides from Figma"""
        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_SLIDES,
            target_slides=slide_numbers,
            require_z_index=True,
        )

        extractor = FigmaExtractor(self.figma_file_id, self.figma_token, filter_config)

        return extractor.extract_data()

    def extract_by_block_types(self, block_types: list[str]) -> dict[str, str | dict | list | int]:
        """Extract slides containing specific block types"""
        filter_config = FilterConfig(mode=FilterMode.SPECIFIC_BLOCKS, target_block_types=block_types)

        extractor = FigmaExtractor(self.figma_file_id, self.figma_token, filter_config)

        return extractor.extract_data()

    def extract_by_containers(self, container_names: list[str]) -> dict[str, str | dict | list | int]:
        """Extract slides from specific containers"""
        filter_config = FilterConfig(mode=FilterMode.BY_TYPE, target_containers=container_names)

        extractor = FigmaExtractor(self.figma_file_id, self.figma_token, filter_config)

        return extractor.extract_data()

    def prepare_sql_generator_input(self, figma_data: dict[str, str | dict | list | int]) -> list[dict[str, str | int | dict | list | bool]]:
        """Convert Figma data to format suitable for SQL Generator with config compatibility. Now includes slideConfig and presentationPaletteColors for each slide."""
        sql_input: list[dict[str, str | int | dict | list | bool]] = []

        if not isinstance(figma_data, dict):
            return sql_input

        slides_raw = figma_data.get("slides", [])
        if not isinstance(slides_raw, list):
            return sql_input

        for slide_raw in slides_raw:
            if not isinstance(slide_raw, dict):
                continue

            slide_number_raw = slide_raw.get("slide_number")
            if not isinstance(slide_number_raw, int):
                continue

            is_last = slide_number_raw == -1
            presentation_layout_id = config.DEFAULT_VALUES.get("presentation_layout_id")

            frame_name_raw = slide_raw.get("frame_name")
            slide_type_raw = slide_raw.get("slide_type")
            if not isinstance(frame_name_raw, str) or not isinstance(slide_type_raw, str):
                continue

            slide_input = {
                "slide_layout_name": frame_name_raw,
                "slide_layout_number": slide_number_raw,
                "slide_type": slide_type_raw,
                "forGeneration": slide_raw.get("forGeneration", True),
                "presentation_layout_id": presentation_layout_id,
                "is_last": is_last,
                "folder_name": slide_raw.get("folder_name", "other"),
                "imagesCount": slide_raw.get("imagesCount", 0),
                "blocks": [],
                "auto_blocks": self._get_auto_blocks_for_slide(slide_raw, is_last),
                "sql_config": {
                    "needs_background": config.AUTO_BLOCKS.get("add_background", True),
                    "default_color": config.DEFAULT_COLOR,
                    "color_settings_id": config.DEFAULT_COLOR_SETTINGS_ID,
                },
                "slideConfig": slide_raw.get("slideConfig", {}),
                "presentationPaletteColors": slide_raw.get("presentationPaletteColors", []),
            }
            slide_config = slide_raw.get("slideConfig", {})
            blocks_raw = slide_raw.get("blocks")
            if not isinstance(blocks_raw, list):
                continue

            for block_raw in blocks_raw:
                if not isinstance(block_raw, dict):
                    continue
                block_dict = BlockUtils.build_block_dict(block_raw, slide_config)
                block_input = {
                    "id": block_dict.get("id", ""),
                    "type": block_dict.get("sql_type", ""),
                    "name": block_dict.get("name", ""),
                    "dimensions": block_dict.get("dimensions", {}),
                    "styles": dict(block_dict.get("styles", {})),
                    "needs_null_styles": block_dict.get("needs_null_styles", False),
                    "needs_z_index": block_dict.get("needs_z_index", False),
                    "border_radius": block_dict.get("border_radius"),
                    "sql_ready": True,
                    "words": block_dict.get("words", 0),
                    "figure_info": block_dict.get("figure_info"),
                    "precompiled_image_info": block_dict.get("precompiled_image_info"),
                }
                slide_input["blocks"].append(block_input)
            sql_input.append(slide_input)
        return sql_input

    def _get_auto_blocks_for_slide(self, slide: dict[str, str | int | dict | list | bool], is_last: bool) -> dict[str, str | dict]:
        """Get automatic blocks configuration for a slide"""
        auto_blocks: dict[str, str | dict] = {}

        add_background = config.AUTO_BLOCKS.get("add_background", True)
        if add_background:
            background_config = config.AUTO_BLOCKS.get("background", {})
            if isinstance(background_config, dict):
                color = background_config.get("color", "#FFFFFF")
                dimensions = background_config.get("dimensions", {})
                auto_blocks["background"] = {
                    "type": "background",
                    "color": color,
                    "dimensions": dimensions,
                }

        return auto_blocks

    def _generate_instruction_header(self) -> list[str]:
        """Generate the header section of SQL instructions."""
        return [
            "# SQL Generator Instructions",
            "Based on extracted Figma data with full config.py compatibility",
            "=" * 60,
            "",
            "## Quick Start",
            "1. Import the config module into your SQL Generator",
            "2. Use the data from sql_generator_input.json",
            f"3. All font weights are normalized to valid values {config.VALID_FONT_WEIGHTS}",
            "4. All block types are validated against config.VALID_BLOCK_TYPES",
            "",
        ]

    def _generate_config_summary(self) -> list[str]:
        """Generate the configuration summary section."""
        return [
            "## Configuration Summary",
            f"- Default Color: {config.DEFAULT_COLOR}",
            f"- Color Settings ID: {config.DEFAULT_COLOR_SETTINGS_ID}",
            f"- Miniatures Base Path: {config.MINIATURES_BASE_PATH}",
            f"- Add Background: {config.AUTO_BLOCKS.get('add_background', True)}",
            "",
        ]

    def _generate_slide_instructions(self, slide: dict, slide_index: int) -> list[str]:
        """Generate instruction section for a single slide."""
        instructions = []
        instructions.append(f"## Slide {slide_index + 1}: {slide['slide_layout_name']}")
        instructions.append("**Configuration:**")

        instructions.append(f"- Slide Number: {slide['slide_layout_number']}")
        slide_type_raw = slide.get("slide_type", "unknown")
        slide_type_str = str(slide_type_raw) if slide_type_raw is not None else "unknown"
        slide_type_info = config.SLIDE_LAYOUT_TYPES.get(slide_type_str, "unknown")
        instructions.append(f"- Slide Type: {slide_type_str} ({slide_type_info})")
        instructions.append(f"- Save For Generation: {slide.get('forGeneration', True)}")
        instructions.append(f"- Is Last: {slide['is_last']}")
        instructions.append(f"- Folder: {slide.get('folder_name', 'other')}")

        blocks = slide.get("blocks", [])
        block_count = len(blocks) if isinstance(blocks, list) else 0
        instructions.append(f"- Total Blocks: {block_count}")

        auto_blocks = slide.get("auto_blocks")
        if isinstance(auto_blocks, dict):
            instructions.append("**Auto Blocks:**")
            for block_name, block_info in auto_blocks.items():
                instructions.append(f"- {block_name.title()}: {block_info['type']}")

        instructions.append("**User Blocks:**")
        if isinstance(blocks, list):
            for j, block in enumerate(blocks):
                instructions.extend(self._generate_block_instructions(block, j + 1))

        instructions.append("")
        return instructions

    def _generate_block_instructions(self, block: dict, block_index: int) -> list[str]:
        """Generate instruction lines for a single block."""
        instructions = []
        instructions.append(f"  {block_index}. **{block['type']}** - {block['name']}")
        instructions.append(f"     - Dimensions: {block['dimensions']}")
        instructions.append(f"     - Z-Index: {block['styles'].get('zIndex', 'N/A')}")
        instructions.append(f"     - Null Styles: {block['needs_null_styles']}")

        if not block["needs_null_styles"]:
            styles = block["styles"]
            font_size = styles.get("fontSize") or styles.get("font_size") or "-"
            weight = styles.get("weight") or "-"
            instructions.append(f"     - Font: {font_size}px, weight {weight}")
            instructions.append(f"     - Alignment: {styles.get('textVertical', '-')} / {styles.get('textHorizontal', '-')}")

        if block.get("border_radius"):
            instructions.append(f"     - Border Radius: {block['border_radius']}")

        blur_radius = block["styles"].get("blur", 0)
        if blur_radius > 0:
            instructions.append(f"- Blur: {blur_radius}px")

        instructions.append("")
        return instructions

    def _generate_command_examples(self) -> list[str]:
        """Generate SQL Generator command examples."""
        return [
            "## SQL Generator Commands",
            "Run these commands in your SQL Generator:",
            "```python",
            "import config",
            "from sql_generator import SQLGenerator",
            "",
            "generator = SQLGenerator(config)",
            "# Use the extracted data to populate the generator",
            "generator.run()",
            "```",
            "",
        ]

    def _generate_files_summary(self) -> list[str]:
        """Generate summary of generated files."""
        return [
            "## Files Generated",
            "- `figma_extract.json`: Raw Figma extraction data",
            "- `sql_generator_input.json`: Processed data ready for SQL Generator",
            "- `sql_files/`: Individual SQL configuration files for each slide",
            "- `sql_instructions.md`: This instruction file",
        ]

    def _convert_styles_for_sql(self, figma_styles: dict[str, str | int | float | bool], block_type: str) -> dict[str, str | int]:
        """Convert Figma styles to SQL Generator format with config defaults"""
        defaults_raw = config.DEFAULT_STYLES.get(block_type, config.DEFAULT_STYLES["default"])
        if not isinstance(defaults_raw, dict):
            defaults_raw = config.DEFAULT_STYLES["default"]
        defaults = defaults_raw

        weight_raw = figma_styles.get("weight")
        default_weight_raw = defaults.get("weight", 400)
        if isinstance(weight_raw, (int, float)):
            weight = int(weight_raw)
        elif isinstance(default_weight_raw, (int, float)):
            weight = int(default_weight_raw)
        else:
            weight = 400

        valid_weights = config.VALID_FONT_WEIGHTS
        if isinstance(valid_weights, list) and len(valid_weights) >= 3:
            if weight not in valid_weights:
                if weight <= 350:
                    weight = valid_weights[0]
                elif weight <= 550:
                    weight = valid_weights[1]
                else:
                    weight = valid_weights[2]

        text_vertical = figma_styles.get("textVertical", defaults.get("text_vertical", "top"))
        text_horizontal = figma_styles.get("textHorizontal", defaults.get("text_horizontal", "left"))
        font_size_raw = figma_styles.get("fontSize", defaults.get("font_size", 16))
        text_transform = figma_styles.get("textTransform", defaults.get("text_transform", "none"))

        if isinstance(font_size_raw, float):
            font_size = int(font_size_raw)
        elif isinstance(font_size_raw, int):
            font_size = font_size_raw
        else:
            font_size = 16

        return {
            "textVertical": str(text_vertical),
            "textHorizontal": str(text_horizontal),
            "fontSize": int(font_size),
            "weight": int(weight),
            "textTransform": str(text_transform),
        }

    def generate_sql_for_slides(
        self,
        slide_numbers: list[int],
        output_dir: str = config.OUTPUT_CONFIG["output_dir"],
    ):
        """Complete pipeline: extract from Figma and generate SQL with config compatibility"""
        LogUtils.log_block_event(f"Extracting slides {slide_numbers} from Figma...")
        if os.path.exists(output_dir):
            LogUtils.log_block_event(f"Removing existing output directory: {output_dir}")
            shutil.rmtree(output_dir)
            LogUtils.log_block_event(f"Removed output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        LogUtils.log_block_event(f"Created output directory: {output_dir}")
        setup_block_logger(output_dir)
        figma_data = self.extract_specific_slides(slide_numbers)
        if not figma_data:
            LogUtils.log_block_event("Failed to extract data from Figma")
            return
        slides_raw = figma_data.get("slides", []) if isinstance(figma_data, dict) else []
        slides_count = len(slides_raw) if isinstance(slides_raw, list) else 0
        print(f"Extracted {slides_count} slides from Figma.")
        with open(f"{output_dir}/figma_extract.json", "w") as f:
            json.dump(figma_data, f, indent=2)
        sql_input = self.prepare_sql_generator_input(figma_data)
        with open(f"{output_dir}/sql_generator_input.json", "w") as f:
            json.dump(sql_input, f, indent=2)
        self._generate_sql_files(sql_input, output_dir)
        LogUtils.log_block_event("\nProcessing complete!")
        LogUtils.log_block_event(f"   Extracted {slides_count} slides")
        LogUtils.log_block_event(f"   Generated {len(sql_input)} SQL-ready configurations")
        LogUtils.log_block_event(f"   Files saved to {output_dir}/")
        self._generate_sql_instructions(sql_input, output_dir)

    def _generate_sql_files(
        self,
        sql_input: list[dict[str, str | int | dict | list | bool]],
        output_dir: str,
    ):
        """Generate individual SQL files for each slide"""
        sql_dir = f"{output_dir}/sql_files"
        os.makedirs(sql_dir, exist_ok=True)

        for i, slide in enumerate(sql_input):
            sql_content = self._create_sql_for_slide(slide)
            filename = f"slide_{slide['slide_layout_number']:02d}_{slide['slide_layout_name']}.sql"

            with open(f"{sql_dir}/{filename}", "w") as f:
                f.write(sql_content)

            LogUtils.log_block_event(f"   Generated SQL: {filename}")

    def _create_sql_for_slide(self, slide: dict[str, str | int | dict | list | bool]) -> str:
        """Create SQL content for a single slide using config templates"""
        lines = []
        lines.append(f"-- Slide {slide['slide_layout_number']}: {slide['slide_layout_name']}")
        lines.append(f"-- Type: {slide['slide_type']}")
        blocks = slide.get("blocks", [])
        blocks_count = len(blocks) if isinstance(blocks, list) else 0
        lines.append(f"-- Blocks: {blocks_count}")
        lines.append("-- Generated from Figma extraction")
        lines.append("")

        lines.append("-- CONFIGURATION FOR SQL GENERATOR:")
        lines.append(f"-- Slide Layout Name: {slide['slide_layout_name']}")
        lines.append(f"-- Slide Layout Number: {slide['slide_layout_number']}")
        lines.append(f"-- Slide Type: {slide['slide_type']}")
        lines.append(f"-- Save For Generation: {slide.get('forGeneration', True)}")
        lines.append(f"-- Is Last: {slide['is_last']}")
        lines.append(f"-- Presentation Layout ID: {slide['presentation_layout_id']}")
        lines.append("")

        auto_blocks = slide.get("auto_blocks")
        if isinstance(auto_blocks, dict):
            lines.append("-- AUTO BLOCKS:")
            for block_name, block_config in auto_blocks.items():
                lines.append(f"--   {block_name}: {block_config}")
            lines.append("")

        lines.append("-- BLOCKS TO CREATE:")
        blocks = slide.get("blocks", [])
        if isinstance(blocks, list):
            for i, block in enumerate(blocks):
                lines.append(f"-- Block {i+1}: {block['type']}")
                lines.append(f"--   Name: {block['name']}")
                lines.append(f"--   Dimensions: {block['dimensions']}")
                lines.append(f"--   Z-Index: {block['styles'].get('zIndex', 'N/A')}")
                lines.append(f"--   Styles: {block['styles']}")
                if block.get("border_radius"):
                    lines.append(f"--   Border Radius: {block['border_radius']}")
                blur_radius = block["styles"].get("blur", 0)
                if blur_radius > 0:
                    lines.append(f"--   Blur: {blur_radius}px")
                lines.append("")

        lines.append("-- Run the SQL Generator with these parameters to create the actual SQL inserts")

        return "\n".join(lines)

    def _generate_sql_instructions(
        self,
        sql_input: list[dict[str, str | int | dict | list | bool]],
        output_dir: str,
    ):
        """Generate comprehensive instructions for using with SQL Generator"""
        instructions = []

        instructions.extend(self._generate_instruction_header())
        instructions.extend(self._generate_config_summary())

        for i, slide in enumerate(sql_input):
            instructions.extend(self._generate_slide_instructions(slide, i))

        instructions.extend(self._generate_command_examples())
        instructions.extend(self._generate_files_summary())

        with open(f"{output_dir}/sql_instructions.md", "w") as f:
            f.write("\n".join(instructions))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Figma to SQL Generator Integration (Config Compatible)")
    parser.add_argument("--file-id", required=False, help="Figma file ID (optional if set in config.py)")
    parser.add_argument("--token", required=False, help="Figma API token (optional if set in config.py)")
    parser.add_argument(
        "--mode",
        choices=["slides", "blocks", "containers", "batch", "validate"],
        default="slides",
        help="Processing mode",
    )
    parser.add_argument("--slides", type=int, nargs="*", help="Specific slide numbers")
    parser.add_argument("--block-types", nargs="*", help="Specific block types")
    parser.add_argument("--containers", nargs="*", help="Specific containers")
    parser.add_argument(
        "--output-dir",
        default=config.OUTPUT_CONFIG["output_dir"],
        help="Output directory",
    )
    parser.add_argument("--batch", action="store_true", help="Enable batch processing mode")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate, don't generate files",
    )
    args = parser.parse_args()

    file_id = args.file_id or getattr(config, "FIGMA_FILE_ID", None)
    token = args.token or getattr(config, "FIGMA_TOKEN", None)

    if not file_id or not token:
        print("Please provide --file-id and --token, or set FIGMA_FILE_ID and FIGMA_TOKEN in config.py")
        exit(1)

    integrator = FigmaToSQLIntegrator(file_id, token)

    if args.mode == "slides" and args.slides:
        LogUtils.log_block_event(f"Processing specific slides: {args.slides}")
        integrator.generate_sql_for_slides(args.slides, args.output_dir)

    elif args.mode == "blocks" and args.block_types:
        LogUtils.log_block_event(f"Processing slides with block types: {args.block_types}")
        data = integrator.extract_by_block_types(args.block_types)
        if data:
            sql_input = integrator.prepare_sql_generator_input(data)
            os.makedirs(args.output_dir, exist_ok=True)
            with open(f"{args.output_dir}/blocks_config.json", "w") as f:
                json.dump(sql_input, f, indent=2)
            LogUtils.log_block_event(f"Processed {len(sql_input)} slides with specified block types")

    elif args.mode == "containers" and args.containers:
        LogUtils.log_block_event(f"Processing slides from containers: {args.containers}")
        data = integrator.extract_by_containers(args.containers)
        if data:
            sql_input = integrator.prepare_sql_generator_input(data)
            os.makedirs(args.output_dir, exist_ok=True)
            with open(f"{args.output_dir}/containers_config.json", "w") as f:
                json.dump(sql_input, f, indent=2)
            LogUtils.log_block_event(f"Processed {len(sql_input)} slides from specified containers")

        LogUtils.log_block_event("Validation Results:")

        if not isinstance(data, dict):
            LogUtils.log_block_event("   Error: Invalid data format")
        else:
            total_blocks = data.get("total_blocks", 0)
            slides_analyzed = data.get("slides_analyzed", 0)
            weight_distribution = data.get("weight_distribution", {})

            LogUtils.log_block_event(f"   Total blocks analyzed: {total_blocks}")
            LogUtils.log_block_event(f"   Slides analyzed: {slides_analyzed}")
            LogUtils.log_block_event(f"   Font weight distribution: {weight_distribution}")

            invalid_raw = data.get("invalid_weights_found", [])
        if isinstance(invalid_raw, list) and invalid_raw:
            LogUtils.log_block_event(f"   Found {len(invalid_raw)} blocks with invalid font weights:")
            for item in invalid_raw[:5]:
                if isinstance(item, dict):
                    slide = item.get("slide", "unknown")
                    block = item.get("block", "unknown")
                    weight = item.get("invalid_weight", "unknown")
                    LogUtils.log_block_event(f"     - Slide {slide}, Block: {block}, Weight: {weight}")
            if len(invalid_raw) > 5:
                LogUtils.log_block_event(f"     ... and {len(invalid_raw) - 5} more")
        else:
            LogUtils.log_block_event("   All font weights are valid!")

    else:
        print("Please specify a valid mode and required parameters")
        print("Examples:")
        print("  python integration.py --file-id ID --token TOKEN --mode slides --slides 1 2 3")
        print("  python integration.py --file-id ID --token TOKEN --mode blocks --block-types table chart")
        print("  python integration.py --file-id ID --token TOKEN --mode containers --containers hero infographics")
        print("  python integration.py --file-id ID --token TOKEN --mode batch")
        print("  python integration.py --file-id ID --token TOKEN --mode validate")
