import re

import configuration as config
from configuration import TextHorizontal, TextVertical
from log_utils import logs, setup_logger

from .block import BlockUtils

logger = setup_logger(__name__)


@logs(logger, on=False)
class Extractor:
    @staticmethod
    def _normalize_font_weight(weight: int | float | str | None) -> int:
        """Normalize font weight to valid values from config"""
        if weight is None:
            return 400  # Default normal weight

        try:
            weight_num = int(weight)
        except (ValueError, TypeError):
            return 400  # Default normal weight

        # Accept all standard font weight values
        if weight_num in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
            return weight_num

        # Round to nearest valid weight for non-standard values
        valid_weights = [100, 200, 300, 400, 500, 600, 700, 800, 900]
        return min(valid_weights, key=lambda x: abs(x - weight_num))

    @staticmethod
    def _extract_z_index(name: str) -> int:
        """Extract z-index from node name"""
        if "z-index" in name:
            parts = name.split("z-index")
            if len(parts) > 1:
                after = parts[1].strip()
                match = re.findall(r"\d+", after)
                if match:
                    return int(match[0])
        return 0

    @staticmethod
    def _extract_opacity(node: dict[str, str | int | float | bool | dict | list]) -> int | float:
        """Extract opacity from a Figma node"""
        if "opacity" in node:
            opacity = node["opacity"]
            if isinstance(opacity, (int, float)):
                return int(opacity) if opacity == 1.0 else float(opacity)

        fills_raw = node.get("fills")
        if isinstance(fills_raw, list):
            for fill in fills_raw:
                if isinstance(fill, dict):
                    visible = fill.get(config.FigmaKey.VISIBLE, True)
                    fill_type = fill.get(config.FigmaKey.TYPE)
                    if visible and fill_type == "SOLID":
                        opacity_raw = fill.get("opacity", 1.0)
                        if isinstance(opacity_raw, (int, float)):
                            return int(opacity_raw) if opacity_raw == 1.0 else float(opacity_raw)

        return 1

    def _extract_blur(self, node: dict[str, str | int | float | bool | dict | list]) -> int:
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
                    blur_radius = self._extract_blur(child)
                    if blur_radius > 0:
                        return blur_radius

        return 0

    def _extract_text_styles(self, node: dict[str, str | int | float | bool | dict | list], sql_type: str) -> dict[str, str | int | float | bool | list]:
        """Extract text styling information with config defaults (no color)."""
        default_style = config.DEFAULT_STYLES.get(sql_type, config.DEFAULT_STYLES["default"])
        styles = {
            "textVertical": default_style.text_vertical,
            "textHorizontal": default_style.text_horizontal,
            "fontSize": default_style.font_size,
            "weight": default_style.weight,
            "textTransform": default_style.text_transform,
            # "lineHeight": defaults.get("line_height", "120%"),
            "lineHeight": "120%",
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
                styles["weight"] = self._normalize_font_weight(font_weight_raw)

        styles["blur"] = self._extract_blur(node)

        line_height_percent_font_size = "lineHeightPercentFontSize"
        if isinstance(style_raw, dict) and line_height_percent_font_size in style_raw:
            line_height_percent_raw = style_raw[line_height_percent_font_size]
            if isinstance(line_height_percent_raw, (int, float)):
                styles["lineHeight"] = f"{round(line_height_percent_raw)}%"
            else:
                # styles["lineHeight"] = defaults.get("line_height", "120%")
                styles["lineHeight"] = "120%"

        result: dict[str, str | int | float | bool | list] = {}
        for key, value in styles.items():
            if isinstance(value, (str, int, float, bool, list)):
                result[key] = value
            else:
                result[key] = str(value)

        return result

    def extract_block_styles(self, node: dict, sql_type: str, name: str) -> dict:
        """Extract and compile all styles for a block."""
        base_styles = self._extract_text_styles(node, sql_type)
        styles: dict[str, str | int | float | bool | list] = {}

        for key, value in base_styles.items():
            if isinstance(value, (str, int, float, bool, list)):
                styles[key] = value
            else:
                styles[key] = str(value)

        z_index = self._extract_z_index(name)
        if z_index == 0:
            z_index = config.Z_INDEX_DEFAULTS.get(sql_type, config.Z_INDEX_DEFAULTS["default"])
        styles["zIndex"] = z_index

        has_border_radius, border_radius = BlockUtils.extract_border_radius_from_node(node)
        styles["borderRadius"] = border_radius

        styles["opacity"] = self._extract_opacity(node)

        if sql_type not in config.TEXT_BLOCK_TYPES:
            styles["blur"] = self._extract_blur(node)

        return styles

    @staticmethod
    def extract_text_content(node: dict, sql_type: str) -> str | None:
        """Extract text content if the block is a text type."""
        if sql_type in config.TEXT_BLOCK_TYPES and BlockUtils.is_node_type(node, config.FigmaNodeType.TEXT):
            return BlockUtils.get_node_property(node, "characters", None)
        return None

    @staticmethod
    def extract_rotation(node: dict[str, str | int | float | bool | dict | list]) -> int:
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


extractor = Extractor()
