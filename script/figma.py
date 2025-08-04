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
from typing import Dict, List, Tuple, Optional, Union
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
    block_logger = logging.getLogger("block_processing")
    block_logger.setLevel(logging.INFO)
    log_path = os.path.join(output_dir, "figma.log")
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    block_log_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    block_log_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    block_logger.addHandler(block_log_handler)


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
    ready_to_dev_marker: Optional[str] = (
        None  # marker for 'ready to dev' (e.g., '[ready]')
    )


@dataclass
class ExtractedBlock:
    id: str
    figma_type: str
    sql_type: str
    name: str
    dimensions: Dict[str, int]
    styles: Dict[str, Union[str, int, float, bool, list]]
    slide_number: int
    parent_container: str
    is_target: bool = False
    text_content: str = None
    figure_info: Dict[str, Union[str, int, float, bool]] = field(default_factory=dict)
    precompiled_image_info: Dict[str, Union[str, int, float, bool]] = field(
        default_factory=dict
    )
    comment: str = None


@dataclass
class ExtractedSlide:
    number: int
    container_name: str
    frame_name: str
    slide_type: str
    blocks: List[ExtractedBlock]
    frame_id: str
    dimensions: Dict[str, int]


# Place BlockTypeUtils before FigmaExtractor so it is always in scope
class BlockTypeUtils:
    @staticmethod
    def detect_block_type(node: dict) -> Tuple[str, str]:
        """Detect block type from a Figma node, returning (figma_type, sql_type). Always returns a valid sql_type."""
        name = node.get("name", "")
        node_type = node.get("type", "")
        clean_name = re.sub(r"\s*z-index.*$", "", name)
        # Check for explicit mappings first, prioritize longer patterns
        sorted_patterns = sorted(
            config.FIGMA_TO_SQL_BLOCK_MAPPING.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )
        for pattern, sql_type in sorted_patterns:
            if pattern in clean_name.lower():
                if sql_type in config.BLOCK_TYPES["block_layout_type_options"]:
                    return pattern, sql_type
        # Infer from Figma node type with helpers
        if node_type == "TEXT":
            sql_type = BlockTypeUtils._detect_text_block_type(clean_name)
            if sql_type in config.BLOCK_TYPES["block_layout_type_options"]:
                return sql_type, sql_type
        # For RECTANGLE, FRAME, and GROUP nodes, use the same pattern matching
        elif node_type in ["RECTANGLE", "FRAME", "GROUP"]:
            sql_type = BlockTypeUtils._detect_text_block_type(clean_name)
            if sql_type in config.BLOCK_TYPES["block_layout_type_options"]:
                return sql_type, sql_type
        # Default fallback
        return "text", "text"

    @staticmethod
    def _normalize_type_name(name: str) -> str:
        # Lowercase, replace underscores/hyphens/spaces, split camelCase
        name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)  # camelCase to snake_case
        name = name.replace("-", "_").replace(" ", "_").lower()
        return name

    @staticmethod
    def _detect_text_block_type(name: str) -> str:
        # Use config mapping for canonical types
        norm = BlockTypeUtils._normalize_type_name(name)
        norm_flat = norm.replace("_", "")
        for pattern, sql_type in config.FIGMA_TO_SQL_BLOCK_MAPPING.items():
            if pattern in norm_flat:
                return sql_type
        return "text"


# ================ Text Utils ================


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


# ================ Figure Utils ================


class FigureUtils:
    @staticmethod
    def extract_base_figure_name(name: str) -> str:
        """Extract the base figure name from a block name (e.g., 'figure (logoRfs_0)' -> 'logoRfs')."""
        if not name:
            return ""
        name_match = re.search(r"\(([^)]+)\)", name)
        if name_match:
            base_name = name_match.group(1)
            # Remove trailing _<number> if present
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


# ================ Block Utils ================


class BlockUtils:
    @staticmethod
    def build_block_dict(block, slide_config: dict = None) -> dict:
        """
        Build a block dictionary from an ExtractedBlock or dict and optional slide_config.
        This is the single source of truth for block dict construction.
        Adds figure_info and precompiled_image_info if relevant.
        Border radius is now included in styles dictionary.
        """
        get = (
            (lambda k: block.get(k, None))
            if isinstance(block, dict)
            else (lambda k: getattr(block, k, None))
        )
        styles = get("styles") or {}

        block_dict = {
            "id": get("id"),
            "name": get("name"),
            "figma_type": get("figma_type"),
            "sql_type": get("sql_type"),
            "dimensions": get("dimensions"),
            "styles": styles,
            "is_target": get("is_target"),
            "needs_null_styles": get("sql_type")
            in config.BLOCK_TYPES["null_style_types"],
            "needs_z_index": get("sql_type") in config.BLOCK_TYPES["z_index_types"],
            "comment": get("comment"),
        }
        text_content = get("text_content")
        # Use existing 'words' if present in dict, else recalculate
        if isinstance(block, dict) and "words" in block and block["words"] is not None:
            block_dict["words"] = block["words"]
        else:
            block_dict["words"] = TextUtils.count_words(text_content)
        # No color/fontFamily in block_dict for any type
        # Always add figure_info and precompiled_image_info for consistency
        block_dict["figure_info"] = BlockUtils.extract_figure_info(block, slide_config)
        block_dict["precompiled_image_info"] = (
            BlockUtils.extract_precompiled_image_info(block, slide_config)
        )
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
        # Check effects on current node
        effects = node.get("effects")
        if effects and isinstance(effects, list):
            for effect in effects:
                if (
                    effect.get("visible", True)
                    and effect.get("type") == "LAYER_BLUR"
                    and "radius" in effect
                ):
                    radius = effect["radius"]
                    if isinstance(radius, (int, float)) and radius > 0:
                        return int(radius)

        # Check nested children recursively
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


# Place ColorUtils before FigmaExtractor so it is always in scope
class ColorUtils:
    @staticmethod
    def extract_color_info(node: dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts the first visible solid fill color and its variable/style from a Figma node.
        Returns (hex_color, color_variable_id).
        """
        fills = node.get("fills")
        if fills and isinstance(fills, list):
            for fill in fills:
                if (
                    fill.get("visible", True)
                    and fill.get("type") == "SOLID"
                    and "color" in fill
                ):
                    c = fill["color"]
                    r = int(round(c.get("r", 0) * 255))
                    g = int(round(c.get("g", 0) * 255))
                    b = int(round(c.get("b", 0) * 255))
                    a = fill.get("opacity", c.get("a", 1))
                    if a < 1:
                        hex_color = "#{:02x}{:02x}{:02x}{:02x}".format(
                            r, g, b, int(a * 255)
                        )
                    else:
                        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                    # Extract variable/style if present
                    color_variable = None
                    if "boundVariables" in fill and "color" in fill["boundVariables"]:
                        color_variable = fill["boundVariables"]["color"].get("id")
                    elif "fillStyleId" in fill:
                        color_variable = fill["fillStyleId"]
                    return hex_color, color_variable
        # Fallback: check for direct color field
        color = node.get("color")
        if color and isinstance(color, str):
            return color.lower(), None
        return None, None


# ================ Font Utils ================


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


# ================ Block Filter Utils ================


class BlockFilterUtils:
    @staticmethod
    def should_include_node_or_block(node_or_block, filter_config) -> bool:
        """
        Centralized logic for whether a node/block should be included based on filter_config.
        Handles z-index, marker, visibility, and filter mode.
        Accepts either a Figma node (dict) or an ExtractedBlock/dict.
        """
        # Handle both node and block
        get = (
            (lambda k: node_or_block.get(k, None))
            if isinstance(node_or_block, dict)
            else (lambda k: getattr(node_or_block, k, None))
        )
        # Exclude hidden
        if getattr(filter_config, "exclude_hidden", True) and get("visible") is False:
            return False
        # Marker check
        marker = getattr(filter_config, "ready_to_dev_marker", None)
        if marker:
            name = get("name") or ""
            if marker.lower() not in name.lower():
                return False
        # Z-index requirement
        if getattr(filter_config, "require_z_index", True):
            name = get("name") or ""
            if "z-index" not in name:
                return False
        # Filter mode logic
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
                return parent_container in getattr(
                    filter_config, "target_containers", []
                )
        return True


# ================ Logging Utility ================
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


# ================ Figma Extractor Class ================
class FigmaExtractor:
    def __init__(
        self, file_id: str, token: str, filter_config: FilterConfig | None = None
    ):
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

    def normalize_font_weight(self, weight: Union[int, float, str, None]) -> int:
        """Normalize font weight to valid values from config"""
        if weight is None:
            return config.VALID_FONT_WEIGHTS[1]  # 400 as default

        try:
            weight_num = int(weight)
        except (ValueError, TypeError):
            return config.VALID_FONT_WEIGHTS[1]  # 400 as default

        # Map font weights to nearest valid value
        if weight_num <= 350:
            return config.VALID_FONT_WEIGHTS[0]  # 300
        elif weight_num <= 550:
            return config.VALID_FONT_WEIGHTS[1]  # 400
        else:
            return config.VALID_FONT_WEIGHTS[2]  # 700

    def extract_text_styles(
        self, node: Dict[str, Union[str, int, float, bool, dict, list]], sql_type: str
    ) -> Dict[str, Union[str, int, list]]:
        """Extract text styling information with config defaults (no color)."""
        defaults = config.DEFAULT_STYLES.get(sql_type, config.DEFAULT_STYLES["default"])
        styles = {
            "textVertical": defaults["text_vertical"],
            "textHorizontal": defaults["text_horizontal"],
            "fontSize": defaults["font_size"],
            "weight": defaults["weight"],
            "textTransform": defaults["text_transform"],
        }
        style = node.get("style", {})
        if style:
            # Prefer Figma's actual values if present
            text_align_vertical = style.get("textAlignVertical", "").lower()
            if text_align_vertical in ["top", "middle", "bottom"]:
                styles["textVertical"] = text_align_vertical
            elif text_align_vertical == "center":
                styles["textVertical"] = "middle"
            # Figma's textAlignHorizontal: 'LEFT', 'CENTER', 'RIGHT' (case-insensitive)
            text_align_horizontal = style.get("textAlignHorizontal", "").lower()
            if text_align_horizontal in ["left", "center", "right"]:
                styles["textHorizontal"] = text_align_horizontal
            if "fontSize" in style:
                styles["fontSize"] = round(style["fontSize"])
            if "fontWeight" in style:
                styles["weight"] = self.normalize_font_weight(style["fontWeight"])

        # Extract blur information
        styles["blur"] = self.extract_blur(node)

        return styles

    def extract_opacity(
        self, node: Dict[str, Union[str, int, float, bool, dict, list]]
    ) -> Union[int, float]:
        """Extract opacity from a Figma node"""
        # Check for direct opacity property
        if "opacity" in node:
            opacity = node["opacity"]
            if isinstance(opacity, (int, float)):
                return int(opacity) if opacity == 1.0 else float(opacity)

        # Check for opacity in fills
        fills = node.get("fills")
        if fills and isinstance(fills, list):
            for fill in fills:
                if fill.get("visible", True) and fill.get("type") == "SOLID":
                    opacity = fill.get("opacity", 1.0)
                    if isinstance(opacity, (int, float)):
                        return int(opacity) if opacity == 1.0 else float(opacity)

        # Default opacity
        return 1

    def extract_rotation(
        self, node: Dict[str, Union[str, int, float, bool, dict, list]]
    ) -> int:
        """Extract rotation from a Figma node"""
        # Check for rotation property
        if "rotation" in node:
            rotation = node["rotation"]
            if isinstance(rotation, (int, float)):
                return int(rotation)

        # Check for rotation in absoluteTransform
        if "absoluteTransform" in node:
            transform = node["absoluteTransform"]
            if isinstance(transform, list) and len(transform) >= 2:
                return 0

        # Default rotation
        return 0

    def extract_border_radius(
        self, node: Dict[str, Union[str, int, float, bool, dict, list]]
    ) -> Tuple[bool, List[int]]:
        """Extract border radius information"""
        border_radius = [0, 0, 0, 0]  # Default: all corners 0
        has_border_radius = False

        # Check for cornerRadius property
        if "cornerRadius" in node:
            radius = node["cornerRadius"]
            if isinstance(radius, (int, float)) and radius > 0:
                border_radius = [int(radius)] * 4
                has_border_radius = True

        # Check for individual corner radii
        if "rectangleCornerRadii" in node:
            radii = node["rectangleCornerRadii"]
            if isinstance(radii, list) and len(radii) == 4:
                border_radius = [int(r) for r in radii]
                has_border_radius = any(r > 0 for r in border_radius)

        return has_border_radius, border_radius

    def extract_blur(
        self, node: Dict[str, Union[str, int, float, bool, dict, list]]
    ) -> int:
        """Extract layer blur radius from a Figma node, checking nested layers. Returns 0 if no blur."""
        # Check effects on current node
        effects = node.get("effects")
        if effects and isinstance(effects, list):
            for effect in effects:
                if (
                    effect.get("visible", True)
                    and effect.get("type") == "LAYER_BLUR"
                    and "radius" in effect
                ):
                    radius = effect["radius"]
                    if isinstance(radius, (int, float)) and radius > 0:
                        return int(radius)

        # Check nested children recursively
        children = node.get("children")
        if children and isinstance(children, list):
            for child in children:
                blur_radius = self.extract_blur(child)
                if blur_radius > 0:
                    return blur_radius

        return 0

    def is_target_frame(
        self, node: Dict[str, Union[str, int, float, bool, dict, list]]
    ) -> bool:
        """Check if node is a target frame, now supports 'ready to dev' marker"""
        if not BlockUtils.get_node_property(node, "absoluteBoundingBox"):
            return False
        # Check for 'ready to dev' marker if set
        marker = getattr(self.filter_config, "ready_to_dev_marker", None)
        if marker:
            name = BlockUtils.get_node_property(node, "name", "").lower()
            if marker.lower() not in name:
                return False
        # Check z-index requirement
        if self.filter_config.require_z_index and not self.has_z_index_in_name(
            BlockUtils.get_node_property(node, "name", "")
        ):
            return False
        abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
        # Check dimensions
        width_match = abs(abs_box["width"] - config.FIGMA_CONFIG["TARGET_WIDTH"]) < 1
        height_match = abs(abs_box["height"] - config.FIGMA_CONFIG["TARGET_HEIGHT"]) < 1
        if not (width_match and height_match):
            return False
        # Check minimum area
        area = abs_box["width"] * abs_box["height"]
        if area < self.filter_config.min_area:
            return False
        return True

    def should_include_block(self, block: ExtractedBlock) -> bool:
        """Check if block should be included based on filter"""
        return BlockFilterUtils.should_include_node_or_block(block, self.filter_config)

    def detect_slide_type(self, container_name: str, slide_number: int) -> str:
        """Detect slide type using only config.py as the source of truth."""
        # Use config mapping for container name to slide number
        key = container_name.strip().lower()
        number = config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
        # Use config mapping for slide number to type
        return config.SLIDE_NUMBER_TO_TYPE.get(number, "classic")

    def get_slide_number(self, parent_name: str) -> int:
        """Get slide number from parent container name (case-insensitive, trimmed). Use config.py as the only source of truth."""
        key = parent_name.strip().lower()
        return config.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, None)

    def extract_color_from_fills(self, node: dict) -> tuple[str | None, str | None]:
        # Replaced by ColorUtils.extract_color_info
        return ColorUtils.extract_color_info(node)

    def fetch_all_comments(self) -> Dict[str, str]:
        """Fetch all comments from Figma API in a single call and return a mapping of node_id to comment."""
        comments_map = {}
        try:
            LogUtils.log_block_event("Fetching comments from Figma API...")
            response = requests.get(
                f"https://api.figma.com/v1/files/{self.file_id}/comments",
                headers=self.headers,
            )
            response.raise_for_status()
            comments_data = response.json()

            LogUtils.log_block_event(
                f"Comments API response keys: {list(comments_data.keys())}"
            )

            # Log the raw response for debugging
            if "comments" in comments_data:
                LogUtils.log_block_event(
                    f"Total comments in response: {len(comments_data['comments'])}"
                )
                for i, comment in enumerate(comments_data["comments"][:3]):
                    LogUtils.log_block_event(f"Comment {i+1}: {comment}")
            else:
                LogUtils.log_block_event(
                    f"No 'comments' key found in response. Available keys: {list(comments_data.keys())}"
                )

            # Create a mapping of node_id to first comment message
            for comment in comments_data.get("comments", []):
                client_meta = comment.get("client_meta", {})
                node_id = client_meta.get("node_id")
                message = comment.get("message", "")
                if node_id and message and node_id not in comments_map:
                    comments_map[node_id] = message
                    LogUtils.log_block_event(
                        f"Mapped comment for node {node_id}: {message[:50]}..."
                    )

            LogUtils.log_block_event(
                f"Successfully mapped {len(comments_map)} comments"
            )
            return comments_map

        except requests.exceptions.RequestException as e:
            LogUtils.log_block_event(f"Failed to fetch comments: {e}", level="debug")
            return {}
        except Exception as e:
            LogUtils.log_block_event(f"Error fetching comments: {e}", level="debug")
            return {}

    def collect_blocks(
        self,
        node: Dict[str, Union[str, int, float, bool, dict, list]],
        frame_origin: Dict[str, int],
        slide_number: int,
        parent_container: str,
        comments_map: Dict[str, str] = None,
    ) -> List[ExtractedBlock]:
        """Recursively collect blocks from a Figma node, filtering and normalizing as needed."""
        blocks = []
        if not BlockUtils.get_node_property(node, "absoluteBoundingBox"):
            return blocks
        if not BlockFilterUtils.should_include_node_or_block(node, self.filter_config):
            return blocks
        name = BlockUtils.get_node_property(node, "name", "")
        has_z = self.has_z_index_in_name(name)
        if has_z:
            figma_type, sql_type = BlockTypeUtils.detect_block_type(node)
            abs_box = BlockUtils.get_node_property(node, "absoluteBoundingBox")
            left = abs_box["x"] - frame_origin["x"]
            top = abs_box["y"] - frame_origin["y"]
            # Extract rotation
            rotation = self.extract_rotation(node)

            dimensions = {
                "x": round(left),
                "y": round(top),
                "w": round(abs_box["width"]),
                "h": round(abs_box["height"]),
                "rotation": rotation,
            }
            name_lower = name.lower()
            is_precompiled = "precompiled" in name_lower
            should_skip = (
                sql_type == "image"
                and dimensions["x"] == 0
                and dimensions["y"] == 0
                and dimensions["w"] == config.FIGMA_CONFIG["TARGET_WIDTH"]
                and dimensions["h"] == config.FIGMA_CONFIG["TARGET_HEIGHT"]
                and not is_precompiled
            )
            if should_skip:
                LogUtils.log_block_event(
                    f"Skipping {sql_type} block {name} (full image {config.FIGMA_CONFIG['TARGET_WIDTH']}x{config.FIGMA_CONFIG['TARGET_HEIGHT']})",
                    level="debug",
                )
            else:
                styles = self.extract_text_styles(node, sql_type)
                z_index = self.extract_z_index(name)
                if z_index == 0:
                    z_index = config.Z_INDEX_DEFAULTS.get(
                        sql_type, config.Z_INDEX_DEFAULTS["default"]
                    )
                styles["zIndex"] = z_index

                # Extract border radius and add to styles (always include, even if 0)
                has_border_radius, border_radius = (
                    BlockUtils.extract_border_radius_from_node(node)
                )
                styles["borderRadius"] = border_radius

                opacity = self.extract_opacity(node)
                styles["opacity"] = opacity

                # Extract blur for non-text blocks (text blocks already have blur from extract_text_styles)
                if sql_type not in [
                    "text",
                    "blockTitle",
                    "slideTitle",
                    "subTitle",
                    "number",
                    "email",
                    "date",
                    "name",
                    "percentage",
                ]:
                    styles["blur"] = self.extract_blur(node)

                text_content = None
                if sql_type in [
                    "text",
                    "blockTitle",
                    "slideTitle",
                    "subTitle",
                    "number",
                    "email",
                    "date",
                    "name",
                    "percentage",
                ] and BlockUtils.is_node_type(node, "TEXT"):
                    text_content = BlockUtils.get_node_property(
                        node, "characters", None
                    )

                # Get comment from the pre-fetched comments map
                comment = comments_map.get(node["id"], "") if comments_map else ""

                block = ExtractedBlock(
                    id=node["id"],
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
                if BlockFilterUtils.should_include_node_or_block(
                    block, self.filter_config
                ):
                    blocks.append(block)
                    LogUtils.log_block_event(f"Added {sql_type} block: {name}")
                    blur_info = (
                        f" | Blur: {styles.get('blur', 0)}px"
                        if styles.get("blur", 0) > 0
                        else ""
                    )
                    LogUtils.log_block_event(
                        f"Block processed | Slide: {slide_number} | Container: {parent_container} | Type: {sql_type} | Name: {name} | Dimensions: {dimensions} | Styles: {styles} | Text: {text_content if text_content else ''}{blur_info}",
                        level="debug",
                    )
        if BlockUtils.get_node_property(node, "children") and not (
            getattr(self.filter_config, "exclude_hidden", True)
            and BlockUtils.get_node_property(node, "visible") is False
        ):
            for node_child in BlockUtils.get_node_property(node, "children"):
                blocks.extend(
                    self.collect_blocks(
                        node_child,
                        frame_origin,
                        slide_number,
                        parent_container,
                        comments_map,
                    )
                )
        return blocks

    def _extract_slide_config(self, slide_node):
        """Extract slideConfig from the hidden slideColors table in the slide node, including color and fontFamily for each color layer."""
        config_dict = {}
        palette_colors = set()
        if not slide_node or not BlockUtils.get_node_property(slide_node, "children"):
            return config_dict, []
        for node_child in BlockUtils.get_node_property(slide_node, "children"):
            if BlockUtils.get_node_property(node_child, "name") == "slideColors":
                if block_logger:
                    block_logger.info(f"[slideColors] Found slideColors table in slide")
                for node_block in BlockUtils.get_node_property(
                    node_child, "children", []
                ):
                    block_type = BlockUtils.get_node_property(node_block, "name")
                    if block_logger:
                        block_logger.info(
                            f"[slideColors] Processing block type: {block_type}"
                        )
                    block_colors = {}
                    for color_group in BlockUtils.get_node_property(
                        node_block, "children", []
                    ):
                        color_hex = BlockUtils.get_node_property(color_group, "name")
                        if color_hex:
                            color_hex = color_hex.lower()
                            palette_colors.add(color_hex)
                        if block_logger:
                            block_logger.info(
                                f"[slideColors] Processing color group: {color_hex}"
                            )
                        block_objs = []
                        for text_child in BlockUtils.get_node_property(
                            color_group, "children", []
                        ):
                            if BlockUtils.is_node_type(text_child, "TEXT"):
                                text_obj = {}
                                color_val, color_var = ColorUtils.extract_color_info(
                                    text_child
                                )
                                text_obj["color"] = color_val
                                if color_var:
                                    text_obj["color_variable"] = color_var
                                font_family = None
                                if (
                                    "style" in text_child
                                    and "fontFamily" in text_child["style"]
                                ):
                                    font_family = text_child["style"]["fontFamily"]
                                text_obj["fontFamily"] = (
                                    FontUtils.normalize_font_family(font_family)
                                )
                                if block_type == "figure":
                                    idx = BlockUtils.get_node_property(
                                        text_child, "name", ""
                                    ).strip()
                                    text_obj["figureName"] = idx
                                    if block_logger:
                                        block_logger.info(
                                            f"[slideColors] Found figure in {color_hex}: name='{idx}', color={color_val}, font={font_family}"
                                        )
                                block_objs.append(text_obj)
                        block_colors[color_hex] = block_objs
                    config_dict[block_type] = block_colors
                    if block_logger:
                        block_logger.info(
                            f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups"
                        )
                        for color_hex, obj_list in block_colors.items():
                            block_logger.info(
                                f"[slideConfig]   Color '{color_hex}': {len(obj_list)} objects"
                            )
        return config_dict, sorted(palette_colors)

    def _update_figure_config_with_names(self, slide_config, blocks):
        # Collect all figure blocks with their info
        figure_blocks_info = []
        for block in blocks:
            if block.sql_type == "figure":
                base_name = FigureUtils.extract_base_figure_name(block.name)
                figure_blocks_info.append({"base_name": base_name, "block": block})
                if block_logger:
                    block_logger.info(
                        f"[figureBlocks] Found figure block: '{block.name}' -> base_name: '{base_name}'"
                    )
        new_figure_config = {}
        for color_hex, obj_list in slide_config["figure"].items():
            figure_objects = []

            # Process ALL figure entries from slideColors, not just the ones that have corresponding blocks
            for obj in obj_list:
                figure_name = obj.get("figureName", "")
                if figure_name:
                    # Try to find a matching block in the main structure
                    matching_block = None
                    for fig in figure_blocks_info:
                        base_name = fig["base_name"]
                        index_match = re.search(r"_(\d+)$", base_name)
                        if index_match and index_match.group(1) == figure_name:
                            matching_block = fig["block"]
                            break

                    # Create figure object for this entry
                    font_family = obj.get("fontFamily")
                    font_family = FontUtils.normalize_font_family(font_family)
                    fill = obj.get("color")

                    # Always try to extract the proper figure name from the figure blocks
                    clean_figure_name = figure_name  # Default to slideColors name

                    # Try to find a matching block to get the proper name
                    found_match = False
                    for fig in figure_blocks_info:
                        base_name = fig["base_name"]
                        index_match = re.search(r"_(\d+)$", base_name)
                        if index_match and index_match.group(1) == figure_name:
                            # Found matching block, extract proper name
                            clean_figure_name = re.sub(r"_(\d+)$", "", base_name)
                            if block_logger:
                                block_logger.info(
                                    f"[figureConfig] Found exact index match for '{figure_name}', using name: '{clean_figure_name}'"
                                )
                            found_match = True
                            break

                    # If no exact match, try to find by z-index or other patterns
                    if not found_match:
                        for fig in figure_blocks_info:
                            base_name = fig["base_name"]
                            # Try to match by z-index if available
                            z_index_match = re.search(
                                r"z-index\s*(\d+)", fig["block"].name
                            )
                            if z_index_match and z_index_match.group(1) == figure_name:
                                clean_figure_name = re.sub(r"_(\d+)$", "", base_name)
                                if block_logger:
                                    block_logger.info(
                                        f"[figureConfig] Found z-index match for '{figure_name}', using name: '{clean_figure_name}'"
                                    )
                                found_match = True
                                break

                    # If still no match, try to find by position in the list (assuming order matters)
                    if not found_match and len(figure_blocks_info) > 0:
                        # Use the first available block name as fallback
                        first_block = figure_blocks_info[0]
                        clean_figure_name = re.sub(
                            r"_(\d+)$", "", first_block["base_name"]
                        )
                        if block_logger:
                            block_logger.info(
                                f"[figureConfig] No match found for '{figure_name}', using fallback name: '{clean_figure_name}'"
                            )

                    if block_logger:
                        if matching_block:
                            block_logger.info(
                                f"[figureConfig] MATCHED: color {color_hex}, figure '{figure_name}' -> color: {fill}, font: {font_family}"
                            )
                        else:
                            block_logger.info(
                                f"[figureConfig] NO BLOCK MATCH: color {color_hex}, figure '{figure_name}' -> color: {fill}, font: {font_family}"
                            )

                    figure_obj = {
                        "color": fill,
                        "fontFamily": font_family,
                        "figureName": clean_figure_name,
                    }
                    figure_objects.append(figure_obj)

            new_figure_config[color_hex] = figure_objects
        slide_config["figure"] = new_figure_config

        # Summary logging
        if block_logger:
            block_logger.info(
                f"[figureConfig] SUMMARY: Processed {len(figure_blocks_info)} figure blocks"
            )
            for fig_info in figure_blocks_info:
                clean_name = re.sub(r"_(\d+)$", "", fig_info["base_name"])
                block_logger.info(
                    f"[figureConfig] Block '{fig_info['base_name']}' -> looking for '{clean_name}' in slideColors"
                )

    def traverse_and_extract(
        self,
        node: Dict[str, Union[str, int, float, bool, dict, list]],
        parent_name: str = "",
        comments_map: Dict[str, str] = None,
    ) -> List[ExtractedSlide]:
        """Traversal with filtering"""
        slides = []

        if self.is_target_frame(node):
            LogUtils.log_block_event(f"Found target frame: \"{node['name']}\"")
            LogUtils.log_block_event(f'Parent container: "{parent_name}"')

            frame_origin = {
                "x": node["absoluteBoundingBox"]["x"],
                "y": node["absoluteBoundingBox"]["y"],
            }

            slide_number = self.get_slide_number(parent_name)

            # Skip if not in target slides (when filtering by specific slides)
            if (
                self.filter_config.mode == FilterMode.SPECIFIC_SLIDES
                and slide_number not in self.filter_config.target_slides
            ):
                return slides

            slide_type = self.detect_slide_type(parent_name, slide_number)

            blocks = self.collect_blocks(
                node, frame_origin, slide_number, parent_name, comments_map
            )

            if blocks or self.filter_config.mode == FilterMode.ALL:
                slide = ExtractedSlide(
                    number=slide_number,
                    container_name=parent_name,
                    frame_name=node["name"],
                    slide_type=slide_type,
                    blocks=blocks,
                    frame_id=node["id"],
                    dimensions={
                        "w": config.FIGMA_CONFIG["TARGET_WIDTH"],
                        "h": config.FIGMA_CONFIG["TARGET_HEIGHT"],
                    },
                )
                # Attach the original node for color extraction
                slide._figma_node = node
                slides.append(slide)
                LogUtils.log_block_event(
                    f"Slide {slide_number} ({slide_type}) with {len(blocks)} blocks"
                )

            return slides

        # Continue traversing children
        if node.get("children"):
            for child in node["children"]:
                child_slides = self.traverse_and_extract(
                    child, node["name"], comments_map
                )
                slides.extend(child_slides)

        return slides

    def extract_data(self) -> Dict[str, Union[str, dict, list, int]]:
        """Main extraction method. Returns extracted slides and metadata, or error info on failure."""
        try:
            response = requests.get(
                f"https://api.figma.com/v1/files/{self.file_id}", headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            # Fetch all comments in a single API call for efficiency
            comments_map = self.fetch_all_comments()

            pages = BlockUtils.get_node_property(
                data["document"], config.FIGMA_KEY_CHILDREN, []
            )
            all_slides = []

            for page in pages:
                LogUtils.log_block_event(
                    f"\nProcessing page: {BlockUtils.get_node_property(page, config.FIGMA_KEY_NAME, 'Unnamed')}"
                )
                page_slides = self.traverse_and_extract(page, comments_map)
                all_slides.extend(page_slides)

            # Generate summary
            summary = {
                "total_slides": len(all_slides),
                "total_blocks": sum(len(slide.blocks) for slide in all_slides),
                "slide_types": {},
                "block_types": {},
                "slide_distribution": {},
            }

            for slide in all_slides:
                slide_type = slide.slide_type
                summary["slide_types"][slide_type] = (
                    summary["slide_types"].get(slide_type, 0) + 1
                )
                summary["slide_distribution"][slide.number] = slide.container_name

                for block in slide.blocks:
                    block_type = block.sql_type
                    summary["block_types"][block_type] = (
                        summary["block_types"].get(block_type, 0) + 1
                    )

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
                        "valid_block_types": config.BLOCK_TYPES[
                            "block_layout_type_options"
                        ],
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

    def _slide_to_dict(
        self, slide: ExtractedSlide
    ) -> Dict[str, Union[str, int, dict, list, bool]]:
        """Convert slide object to dictionary, using only the text block with the most text for sentence count. Remove debug logs. Add slideColors extraction."""
        # Find the text block with the longest text_content
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
            sentence_count = TextUtils.count_sentences(text_content)
        if sentence_count == 0:
            sentence_count = 1

        # Count images in the slide
        images_count = sum(1 for block in slide.blocks if block.sql_type == "image")

        # Extract slideConfig and palette colors if available
        slide_config = {}
        presentation_palette_colors = []
        figma_node = getattr(slide, "_figma_node", None)
        if figma_node:
            slide_config, presentation_palette_colors = self._extract_slide_config(
                figma_node
            )
            # Build mapping from figure numbers to actual figure names and update slideConfig
            if "figure" in slide_config:
                self._update_figure_config_with_names(slide_config, slide.blocks)
        return {
            "slide_number": slide.number,
            "container_name": slide.container_name,
            "frame_name": slide.frame_name,
            "slide_type": slide.slide_type,
            "sentences": sentence_count,
            "imagesCount": images_count,
            "frame_id": slide.frame_id,
            "dimensions": slide.dimensions,
            "folder_name": config.SLIDE_NUMBER_TO_FOLDER.get(slide.number, "other"),
            "blocks": [
                self._block_to_dict(block, slide_config) for block in slide.blocks
            ],
            "block_count": len(slide.blocks),
            "slideConfig": slide_config,
            "presentationPaletteColors": presentation_palette_colors,
        }

    def _block_to_dict(
        self, block: ExtractedBlock, slide_config=None
    ) -> Dict[str, Union[str, int, dict, list, bool]]:
        # Now just call build_block_dict for all block dict construction
        return BlockUtils.build_block_dict(block, slide_config)

    def save_results(
        self, data: Dict[str, Union[str, dict, list, int]], output_file: str | None
    ) -> str:
        """Save extracted data to file"""
        if not data:
            return ""
        if not os.path.exists(config.FIGMA_CONFIG["OUTPUT_DIR"]):
            os.makedirs(config.FIGMA_CONFIG["OUTPUT_DIR"])

        if not output_file:
            output_file = f"{config.FIGMA_CONFIG['OUTPUT_DIR']}/{config.FIGMA_CONFIG['OUTPUT_FILE']}_config_compatible.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        LogUtils.log_block_event(f"\nData saved: {output_file}")

        # Print detailed summary
        metadata = data.get("metadata", {})
        summary = metadata.get("extraction_summary", {})
        LogUtils.log_block_event(f"\nEXTRACTION SUMMARY:")
        LogUtils.log_block_event(f"   Total slides: {summary.get('total_slides', 0)}")
        LogUtils.log_block_event(f"   Total blocks: {summary.get('total_blocks', 0)}")
        LogUtils.log_block_event(f"   Slide types: {summary.get('slide_types', {})}")
        LogUtils.log_block_event(f"   Block types: {summary.get('block_types', {})}")
        LogUtils.log_block_event(
            f"   Distribution: {summary.get('slide_distribution', {})}"
        )

        return output_file


# ================ Integration Classes ================


class FigmaToSQLIntegrator:
    """Integrates Figma extraction with SQL generation"""

    def __init__(self, figma_file_id: str, figma_token: str):
        self.figma_file_id = figma_file_id
        self.figma_token = figma_token

    def extract_specific_slides(
        self, slide_numbers: List[int]
    ) -> Dict[str, Union[str, dict, list, int]]:
        """Extract specific slides from Figma"""
        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_SLIDES,
            target_slides=slide_numbers,
            require_z_index=True,
        )

        extractor = FigmaExtractor(self.figma_file_id, self.figma_token, filter_config)

        return extractor.extract_data()

    def extract_by_block_types(
        self, block_types: List[str]
    ) -> Dict[str, Union[str, dict, list, int]]:
        """Extract slides containing specific block types"""
        filter_config = FilterConfig(
            mode=FilterMode.SPECIFIC_BLOCKS, target_block_types=block_types
        )

        extractor = FigmaExtractor(self.figma_file_id, self.figma_token, filter_config)

        return extractor.extract_data()

    def extract_by_containers(
        self, container_names: List[str]
    ) -> Dict[str, Union[str, dict, list, int]]:
        """Extract slides from specific containers"""
        filter_config = FilterConfig(
            mode=FilterMode.BY_TYPE, target_containers=container_names
        )

        extractor = FigmaExtractor(self.figma_file_id, self.figma_token, filter_config)

        return extractor.extract_data()

    def prepare_sql_generator_input(
        self, figma_data: Dict[str, Union[str, dict, list, int]]
    ) -> List[Dict[str, Union[str, int, dict, list, bool]]]:
        """Convert Figma data to format suitable for SQL Generator with config compatibility. Now includes slideConfig and presentationPaletteColors for each slide."""
        sql_input = []
        for slide in figma_data.get("slides", []):
            is_last = slide["slide_number"] == -1
            presentation_layout_id = config.DEFAULT_VALUES.get("presentation_layout_id")
            slide_input = {
                "slide_layout_name": slide["frame_name"],
                "slide_layout_number": slide["slide_number"],
                "slide_type": slide["slide_type"],
                "presentation_layout_id": presentation_layout_id,
                "is_last": is_last,
                "folder_name": slide.get("folder_name", "other"),
                "imagesCount": slide.get("imagesCount", 0),
                "blocks": [],
                "auto_blocks": self._get_auto_blocks_for_slide(slide, is_last),
                "sql_config": {
                    "needs_background": config.AUTO_BLOCKS.get("add_background", True),
                    "needs_watermark": config.AUTO_BLOCKS.get("add_watermark", False)
                    or is_last,
                    "default_color": config.DEFAULT_COLOR,
                    "color_settings_id": config.DEFAULT_COLOR_SETTINGS_ID,
                },
                "slideConfig": slide.get("slideConfig", {}),
                "presentationPaletteColors": slide.get("presentationPaletteColors", []),
            }
            slide_config = slide.get("slideConfig", {})
            for block in slide["blocks"]:
                # Always use build_block_dict for block dict construction
                block_dict = BlockUtils.build_block_dict(block, slide_config)
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
                # Do NOT add color/fontFamily to block_input["styles"]
                slide_input["blocks"].append(block_input)
            sql_input.append(slide_input)
        return sql_input

    def _get_auto_blocks_for_slide(
        self, slide: Dict[str, Union[str, int, dict, list, bool]], is_last: bool
    ) -> Dict[str, Union[str, dict]]:
        """Get automatic blocks configuration for a slide"""
        auto_blocks = {}

        # Background block
        if config.AUTO_BLOCKS.get("add_background", True):
            auto_blocks["background"] = {
                "type": "background",
                "color": config.AUTO_BLOCKS["background"]["color"],
                "dimensions": config.AUTO_BLOCKS["background"]["dimensions"],
            }

        # Watermark blocks
        if is_last:
            auto_blocks["watermark"] = {
                "type": "watermark",
                "dimensions": config.AUTO_BLOCKS["last_slide"]["watermark1"][
                    "dimensions"
                ],
            }
        elif config.AUTO_BLOCKS.get("add_watermark", False):
            auto_blocks["watermark"] = {
                "type": "watermark",
                "dimensions": config.AUTO_BLOCKS["watermark"]["dimensions"],
            }

        return auto_blocks

    def _convert_styles_for_sql(
        self, figma_styles: Dict[str, Union[str, int, float, bool]], block_type: str
    ) -> Dict[str, Union[str, int]]:
        """Convert Figma styles to SQL Generator format with config defaults"""
        # Use config defaults as base
        defaults = config.DEFAULT_STYLES.get(
            block_type, config.DEFAULT_STYLES["default"]
        )

        # Ensure font weight is valid from config
        weight = figma_styles.get("weight", defaults["weight"])
        if weight not in config.VALID_FONT_WEIGHTS:
            if weight <= 350:
                weight = config.VALID_FONT_WEIGHTS[0]  # 300
            elif weight <= 550:
                weight = config.VALID_FONT_WEIGHTS[1]  # 400
            else:
                weight = config.VALID_FONT_WEIGHTS[2]  # 700

        return {
            "textVertical": figma_styles.get("textVertical", defaults["text_vertical"]),
            "textHorizontal": figma_styles.get(
                "textHorizontal", defaults["text_horizontal"]
            ),
            "fontSize": figma_styles.get("fontSize", defaults["font_size"]),
            "weight": weight,
            "textTransform": figma_styles.get(
                "textTransform", defaults["text_transform"]
            ),
        }

    def generate_sql_for_slides(
        self,
        slide_numbers: List[int],
        output_dir: str = config.OUTPUT_CONFIG["output_dir"],
    ):
        """Complete pipeline: extract from Figma and generate SQL with config compatibility"""
        LogUtils.log_block_event(f"Extracting slides {slide_numbers} from Figma...")
        # Remove output directory if it exists
        if os.path.exists(output_dir):
            LogUtils.log_block_event(
                f"Removing existing output directory: {output_dir}"
            )
            shutil.rmtree(output_dir)
            LogUtils.log_block_event(f"Removed output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        LogUtils.log_block_event(f"Created output directory: {output_dir}")
        # Set up block logger in the output directory
        setup_block_logger(output_dir)
        # Extract from Figma
        figma_data = self.extract_specific_slides(slide_numbers)
        if not figma_data:
            LogUtils.log_block_event("Failed to extract data from Figma")
            return
        # Print how many slides were extracted
        print(f"Extracted {len(figma_data.get('slides', []))} slides from Figma.")
        # Save extracted data
        with open(f"{output_dir}/figma_extract.json", "w") as f:
            json.dump(figma_data, f, indent=2)
        # Prepare for SQL Generator
        sql_input = self.prepare_sql_generator_input(figma_data)
        # Save SQL input format
        with open(f"{output_dir}/sql_generator_input.json", "w") as f:
            json.dump(sql_input, f, indent=2)
        # Generate ready-to-use SQL files for each slide
        self._generate_sql_files(sql_input, output_dir)
        LogUtils.log_block_event("\nProcessing complete!")
        LogUtils.log_block_event(
            f"   Extracted {len(figma_data.get('slides', []))} slides"
        )
        LogUtils.log_block_event(
            f"   Generated {len(sql_input)} SQL-ready configurations"
        )
        LogUtils.log_block_event(f"   Files saved to {output_dir}/")
        # Generate instructions for SQL Generator
        self._generate_sql_instructions(sql_input, output_dir)

    def _generate_sql_files(
        self,
        sql_input: List[Dict[str, Union[str, int, dict, list, bool]]],
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

    def _create_sql_for_slide(
        self, slide: Dict[str, Union[str, int, dict, list, bool]]
    ) -> str:
        """Create SQL content for a single slide using config templates"""
        lines = []
        lines.append(
            f"-- Slide {slide['slide_layout_number']}: {slide['slide_layout_name']}"
        )
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
        if slide.get("auto_blocks"):
            lines.append("-- AUTO BLOCKS:")
            for block_name, block_config in slide["auto_blocks"].items():
                lines.append(f"--   {block_name}: {block_config}")
            lines.append("")

        # Add blocks info
        lines.append("-- BLOCKS TO CREATE:")
        for i, block in enumerate(slide["blocks"]):
            lines.append(f"-- Block {i+1}: {block['type']}")
            lines.append(f"--   Name: {block['name']}")
            lines.append(f"--   Dimensions: {block['dimensions']}")
            lines.append(f"--   Z-Index: {block['styles'].get('zIndex', 'N/A')}")
            lines.append(f"--   Styles: {block['styles']}")
            if block.get("border_radius"):
                lines.append(f"--   Border Radius: {block['border_radius']}")
            # Add blur information if present
            blur_radius = block["styles"].get("blur", 0)
            if blur_radius > 0:
                lines.append(f"--   Blur: {blur_radius}px")
            lines.append("")

        lines.append(
            "-- Run the SQL Generator with these parameters to create the actual SQL inserts"
        )

        return "\n".join(lines)

    def _generate_sql_instructions(
        self,
        sql_input: List[Dict[str, Union[str, int, dict, list, bool]]],
        output_dir: str,
    ):
        """Generate comprehensive instructions for using with SQL Generator"""
        instructions = []
        instructions.append("# SQL Generator Instructions")
        instructions.append(
            "Based on extracted Figma data with full config.py compatibility"
        )
        instructions.append("=" * 60)
        instructions.append("")

        instructions.append("## Quick Start")
        instructions.append("1. Import the config module into your SQL Generator")
        instructions.append("2. Use the data from sql_generator_input.json")
        instructions.append(
            f"3. All font weights are normalized to valid values {config.VALID_FONT_WEIGHTS}"
        )
        instructions.append(
            "4. All block types are validated against config.VALID_BLOCK_TYPES"
        )
        instructions.append("")

        instructions.append("## Configuration Summary")
        instructions.append(f"- Default Color: {config.DEFAULT_COLOR}")
        instructions.append(f"- Color Settings ID: {config.DEFAULT_COLOR_SETTINGS_ID}")
        instructions.append(f"- Miniatures Base Path: {config.MINIATURES_BASE_PATH}")
        instructions.append(
            f"- Add Background: {config.AUTO_BLOCKS.get('add_background', True)}"
        )
        instructions.append(
            f"- Add Watermark: {config.AUTO_BLOCKS.get('add_watermark', False)}"
        )
        instructions.append("")

        # Generate per-slide instructions
        for i, slide in enumerate(sql_input):
            instructions.append(f"## Slide {i+1}: {slide['slide_layout_name']}")
            instructions.append(f"**Configuration:**")
            instructions.append(f"- Slide Number: {slide['slide_layout_number']}")
            instructions.append(
                f"- Slide Type: {slide['slide_type']} ({config.SLIDE_LAYOUT_TYPES.get(slide['slide_type'], 'unknown')})"
            )
            instructions.append(f"- Is Last: {slide['is_last']}")
            instructions.append(f"- Folder: {slide.get('folder_name', 'other')}")
            instructions.append(f"- Total Blocks: {len(slide['blocks'])}")

            # Auto blocks
            if slide.get("auto_blocks"):
                instructions.append(f"**Auto Blocks:**")
                for block_name, block_info in slide["auto_blocks"].items():
                    instructions.append(f"- {block_name.title()}: {block_info['type']}")

            instructions.append(f"**User Blocks:**")
            for j, block in enumerate(slide["blocks"]):
                instructions.append(f"  {j+1}. **{block['type']}** - {block['name']}")
                instructions.append(f"     - Dimensions: {block['dimensions']}")
                instructions.append(
                    f"     - Z-Index: {block['styles'].get('zIndex', 'N/A')}"
                )
                instructions.append(f"     - Null Styles: {block['needs_null_styles']}")

                if not block["needs_null_styles"]:
                    styles = block["styles"]
                    font_size = styles.get("fontSize") or styles.get("font_size") or "-"
                    weight = styles.get("weight") or "-"
                    instructions.append(f"     - Font: {font_size}px, weight {weight}")
                    instructions.append(
                        f"     - Alignment: {styles.get('textVertical', '-') } / {styles.get('textHorizontal', '-')}"
                    )

                if block.get("border_radius"):
                    instructions.append(
                        f"     - Border Radius: {block['border_radius']}"
                    )

                # Add blur information if present
                blur_radius = block["styles"].get("blur", 0)
                if blur_radius > 0:
                    instructions.append(f"     - Blur: {blur_radius}px")
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
        instructions.append(
            "- `sql_generator_input.json`: Processed data ready for SQL Generator"
        )
        instructions.append(
            "- `sql_files/`: Individual SQL configuration files for each slide"
        )
        instructions.append("- `sql_instructions.md`: This instruction file")

        with open(f"{output_dir}/sql_instructions.md", "w") as f:
            f.write("\n".join(instructions))


# Usage Examples
def example_usage():
    """Examples of how to use the integration with config compatibility"""

    # Initialize integrator
    integrator = FigmaToSQLIntegrator(
        figma_file_id="YOUR_FIGMA_FILE_ID", figma_token="YOUR_FIGMA_TOKEN"
    )

    # Example 1: Extract specific slides with full SQL generation
    LogUtils.log_block_event(
        "Example 1: Extract slides 1, 3, and 5 with SQL generation"
    )
    integrator.generate_sql_for_slides([1, 3, 5], "output/hero_and_cols")

    # Example 2: Extract slides with tables (will be automatically typed as 'table')
    LogUtils.log_block_event("\nExample 2: Extract slides containing tables")
    table_data = integrator.extract_by_block_types(["table"])
    if table_data:
        sql_input = integrator.prepare_sql_generator_input(table_data)
        LogUtils.log_block_event(
            f"Found {len(sql_input)} slides with tables, ready for SQL Generator"
        )

        # Save for SQL Generator
        os.makedirs("output/tables", exist_ok=True)
        with open("output/tables/table_slides_config.json", "w") as f:
            json.dump(sql_input, f, indent=2)

    # Example 3: Extract hero and infographics slides
    LogUtils.log_block_event(
        "\nExample 3: Extract from hero and infographics containers"
    )
    container_data = integrator.extract_by_containers(["hero", "infographics"])
    if container_data:
        sql_input = integrator.prepare_sql_generator_input(container_data)
        LogUtils.log_block_event(
            f"Found {len(sql_input)} slides from specified containers"
        )

        # Show configuration details
        for slide in sql_input:
            LogUtils.log_block_event(
                f"  Slide {slide['slide_layout_number']}: {slide['slide_layout_name']}"
            )
            LogUtils.log_block_event(
                f"    Type: {slide['slide_type']}, Blocks: {len(slide['blocks'])}"
            )
            LogUtils.log_block_event(
                f"    Auto blocks: {list(slide['auto_blocks'].keys())}"
            )

    # Example 4: Extract all slides and generate comprehensive SQL package
    LogUtils.log_block_event("\nExample 4: Extract all slides for full presentation")
    all_data = integrator.extract_specific_slides(
        list(range(1, 15)) + [-1]
    )  # All slides including last
    if all_data:
        sql_input = integrator.prepare_sql_generator_input(all_data)

        # Generate complete SQL package
        output_dir = "output/complete_presentation"
        os.makedirs(output_dir, exist_ok=True)

        # Save by slide type for organization
        by_type = {}
        for slide in sql_input:
            slide_type = slide["slide_type"]
            if slide_type not in by_type:
                by_type[slide_type] = []
            by_type[slide_type].append(slide)

        for slide_type, slides in by_type.items():
            type_dir = f"{output_dir}/{slide_type}"
            os.makedirs(type_dir, exist_ok=True)
            with open(f"{type_dir}/slides_config.json", "w") as f:
                json.dump(slides, f, indent=2)
            LogUtils.log_block_event(
                f"  • {slide_type}: {len(slides)} slides saved to {type_dir}/"
            )

    # Example 5: Validate extraction against config
    LogUtils.log_block_event("\nExample 5: Config validation")
    validation_data = integrator.extract_specific_slides(
        [1, 5, 8, 14]
    )  # Different types
    if validation_data:
        LogUtils.log_block_event("Config Validation Results:")
        for slide in validation_data["slides"]:
            LogUtils.log_block_event(
                f"  Slide {slide['slide_number']} ({slide['slide_type']}):"
            )
            for block in slide["blocks"]:
                is_valid_type = (
                    block["sql_type"] in config.BLOCK_TYPES["block_layout_type_options"]
                )
                is_valid_weight = block["styles"]["weight"] in config.VALID_FONT_WEIGHTS
                LogUtils.log_block_event(
                    f"    • {block['sql_type']}: Type OK: {is_valid_type}, Weight OK: {is_valid_weight}"
                )


# Advanced integration class for batch processing
class BatchFigmaProcessor:
    """Process multiple Figma files or large sets of slides"""

    def __init__(self, figma_token: str):
        self.figma_token = figma_token

    def process_presentation_by_types(
        self, file_id: str, output_base: str = "batch_output"
    ):
        """Process a presentation by extracting different slide types separately"""
        integrator = FigmaToSQLIntegrator(file_id, self.figma_token)

        # Define slide type groups based on config
        type_groups = {
            "title_and_last": [-1, 1],  # Special slides
            "text_layouts": [2, 3, 4, 6, 7, 9, 10, 11, 12, 13],  # Text-based
            "special_content": [5, 8, 14],  # Infographics, tables, charts
        }

        results = {}
        for group_name, slide_numbers in type_groups.items():
            LogUtils.log_block_event(f"\nProcessing {group_name}...")
            data = integrator.extract_specific_slides(slide_numbers)
            if data:
                sql_input = integrator.prepare_sql_generator_input(data)
                results[group_name] = sql_input

                # Save to organized folders
                group_dir = f"{output_base}/{group_name}"
                os.makedirs(group_dir, exist_ok=True)
                with open(f"{group_dir}/figma_extract.json", "w") as f:
                    json.dump(data, f, indent=2)

                with open(f"{group_dir}/sql_config.json", "w") as f:
                    json.dump(sql_input, f, indent=2)
                LogUtils.log_block_event(
                    f"   {len(sql_input)} slides processed for {group_name}"
                )

        return results

    def validate_font_weights_across_presentation(
        self, file_id: str
    ) -> Dict[str, Union[str, int, list, dict]]:
        """Extract all slides and validate font weight compliance"""
        integrator = FigmaToSQLIntegrator(file_id, self.figma_token)
        all_data = integrator.extract_specific_slides(list(range(1, 15)) + [-1])

        if not all_data:
            return {"error": "Failed to extract data"}

        weight_analysis = {
            "total_blocks": 0,
            "weight_distribution": {weight: 0 for weight in config.VALID_FONT_WEIGHTS},
            "invalid_weights_found": [],
            "slides_analyzed": len(all_data["slides"]),
        }

        for slide in all_data["slides"]:
            for block in slide["blocks"]:
                weight_analysis["total_blocks"] += 1
                weight = block["styles"]["weight"]

                if weight in config.VALID_FONT_WEIGHTS:
                    weight_analysis["weight_distribution"][weight] += 1
                else:
                    weight_analysis["invalid_weights_found"].append(
                        {
                            "slide": slide["slide_number"],
                            "block": block["name"],
                            "invalid_weight": weight,
                        }
                    )

        return weight_analysis


# Command-line interface for integration
if __name__ == "__main__":
    import argparse
    import config

    parser = argparse.ArgumentParser(
        description="Figma to SQL Generator Integration (Config Compatible)"
    )
    parser.add_argument(
        "--file-id", required=False, help="Figma file ID (optional if set in config.py)"
    )
    parser.add_argument(
        "--token", required=False, help="Figma API token (optional if set in config.py)"
    )
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
    parser.add_argument(
        "--batch", action="store_true", help="Enable batch processing mode"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate, don't generate files",
    )
    args = parser.parse_args()

    # Use config values if not provided
    file_id = args.file_id or getattr(config, "FIGMA_FILE_ID", None)
    token = args.token or getattr(config, "FIGMA_TOKEN", None)

    if not file_id or not token:
        print(
            "Please provide --file-id and --token, or set FIGMA_FILE_ID and FIGMA_TOKEN in config.py"
        )
        exit(1)

    integrator = FigmaToSQLIntegrator(file_id, token)

    if args.mode == "slides" and args.slides:
        LogUtils.log_block_event(f"Processing specific slides: {args.slides}")
        integrator.generate_sql_for_slides(args.slides, args.output_dir)

    elif args.mode == "blocks" and args.block_types:
        LogUtils.log_block_event(
            f"Processing slides with block types: {args.block_types}"
        )
        data = integrator.extract_by_block_types(args.block_types)
        if data:
            sql_input = integrator.prepare_sql_generator_input(data)
            os.makedirs(args.output_dir, exist_ok=True)
            with open(f"{args.output_dir}/blocks_config.json", "w") as f:
                json.dump(sql_input, f, indent=2)
            LogUtils.log_block_event(
                f"Processed {len(sql_input)} slides with specified block types"
            )

    elif args.mode == "containers" and args.containers:
        LogUtils.log_block_event(
            f"Processing slides from containers: {args.containers}"
        )
        data = integrator.extract_by_containers(args.containers)
        if data:
            sql_input = integrator.prepare_sql_generator_input(data)
            os.makedirs(args.output_dir, exist_ok=True)
            with open(f"{args.output_dir}/containers_config.json", "w") as f:
                json.dump(sql_input, f, indent=2)
            LogUtils.log_block_event(
                f"Processed {len(sql_input)} slides from specified containers"
            )

    elif args.mode == "batch":
        LogUtils.log_block_event("Running batch processing...")
        processor = BatchFigmaProcessor(token)
        results = processor.process_presentation_by_types(file_id, args.output_dir)
        LogUtils.log_block_event(
            f"Batch processing complete. Results: {list(results.keys())}"
        )

    elif args.mode == "validate":
        LogUtils.log_block_event("Running validation...")
        processor = BatchFigmaProcessor(token)
        validation = processor.validate_font_weights_across_presentation(file_id)

        LogUtils.log_block_event(f"Validation Results:")
        LogUtils.log_block_event(
            f"   Total blocks analyzed: {validation.get('total_blocks', 0)}"
        )
        LogUtils.log_block_event(
            f"   Slides analyzed: {validation.get('slides_analyzed', 0)}"
        )
        LogUtils.log_block_event(
            f"   Font weight distribution: {validation.get('weight_distribution', {})}"
        )

        invalid = validation.get("invalid_weights_found", [])
        if invalid:
            LogUtils.log_block_event(
                f"   Found {len(invalid)} blocks with invalid font weights:"
            )
            for item in invalid[:5]:  # Show first 5
                LogUtils.log_block_event(
                    f"     - Slide {item['slide']}, Block: {item['block']}, Weight: {item['invalid_weight']}"
                )
            if len(invalid) > 5:
                LogUtils.log_block_event(f"     ... and {len(invalid) - 5} more")
        else:
            LogUtils.log_block_event("   All font weights are valid!")

    else:
        print("Please specify a valid mode and required parameters")
        print("Examples:")
        print(
            "  python integration.py --file-id ID --token TOKEN --mode slides --slides 1 2 3"
        )
        print(
            "  python integration.py --file-id ID --token TOKEN --mode blocks --block-types table chart"
        )
        print(
            "  python integration.py --file-id ID --token TOKEN --mode containers --containers hero infographics"
        )
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
