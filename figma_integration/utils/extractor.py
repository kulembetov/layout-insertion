import re

import configuration as config
from configuration import TextHorizontal, TextVertical
from figma_integration import BlockUtils, ColorUtils, FontUtils
from log_utils import logs, setup_logger

logger = setup_logger(__name__)


@logs(logger, on=False)
class Extractor:
    @staticmethod
    def _normalize_font_weight(weight: int | float | str | None) -> int:
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

    @staticmethod
    def extract_z_index(name: str) -> int:
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
    def extract_opacity(node: dict[str, str | int | float | bool | dict | list]) -> int | float:
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
                styles["weight"] = self._normalize_font_weight(font_weight_raw)

        styles["blur"] = self.extract_blur(node)

        result: dict[str, str | int | float | bool | list] = {}
        for key, value in styles.items():
            if isinstance(value, (str, int, float, bool, list)):
                result[key] = value
            else:
                result[key] = str(value)

        return result

    @staticmethod
    def extract_text_content(node: dict, sql_type: str) -> str | None:
        """Extract text content if the block is a text type."""
        if sql_type in config.TEXT_BLOCK_TYPES and BlockUtils.is_node_type(node, config.FigmaNodeType.TEXT):
            return BlockUtils.get_node_property(node, "characters", None)
        return None

    def extract_block_styles(self, node: dict, sql_type: str, name: str) -> dict:
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

        if sql_type not in config.TEXT_BLOCK_TYPES:
            styles["blur"] = self.extract_blur(node)

        return styles

    @staticmethod
    @logs(logger, on=True)
    def extract_slide_config(slide_node):
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
