import math
import re
from typing import Any

from django_app.api_v1.constants import CONSTANTS, TYPES
from django_app.api_v1.utils.font import normalize_font_family, normalize_font_weight
from log_utils import logs, setup_logger

logger = setup_logger(__name__)


# codeblock for 'extract_color_info', don't use/import this
def _hex_and_color_var(fill: dict) -> tuple[str | None, str | None]:
    c = fill["color"]
    r = int(round(c.get("r", 0) * 255))
    g = int(round(c.get("g", 0) * 255))
    b = int(round(c.get("b", 0) * 255))
    a = fill.get("opacity", c.get("a", 1))
    if a < 1:
        hex_color = f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
    else:
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
    # Extract variable/style if present
    color_variable = None
    if "boundVariables" in fill and "color" in fill["boundVariables"]:
        color_variable = fill["boundVariables"]["color"].get("id")
    elif "fillStyleId" in fill:
        color_variable = fill["fillStyleId"]
    return hex_color, color_variable


@logs(logger, on=False)
class Extractor:
    @staticmethod
    @logs(logger, on=True)
    def extract_base_figure_name(name: str | None) -> str:
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
    @logs(logger, on=True)
    def extract_figure_index(name: str) -> str:
        """Extract the trailing index (e.g., '_2') from a figure name, or return ''."""
        if not name:
            return ""
        index_match = re.search(r"_(\d+)$", name)
        if index_match:
            return index_match.group(1)
        return ""

    @staticmethod
    @logs(logger, on=True)
    def extract_text_styles(node: dict[str, Any], sql_type: str) -> dict[str, Any]:
        """Extract text styling information with config defaults (no color)."""
        defaults = CONSTANTS.DEFAULT_STYLES.get(sql_type, CONSTANTS.DEFAULT_STYLES["default"])
        styles = {"textVertical": defaults["text_vertical"], "textHorizontal": defaults["text_horizontal"], "fontSize": defaults["font_size"], "weight": defaults["weight"], "textTransform": defaults["text_transform"]}
        style = node.get(TYPES.FK_STYLE, {})
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
                styles["weight"] = normalize_font_weight(style["fontWeight"])
        return styles

    # @staticmethod
    # def extract_border_radius(node: dict[str, Any]) -> tuple[bool, list[int]]:
    #     """Extract corner radius information"""
    #     border_radius = [0, 0, 0, 0]  # Default: all corners 0
    #     has_border_radius = False

    #     # Check for cornerRadius property
    #     if TYPES.FK_BORDER_RADIUS in node:
    #         radius = node[TYPES.FK_BORDER_RADIUS]
    #         if isinstance(radius, (int, float)) and radius > 0:
    #             border_radius = [int(radius)] * 4
    #             has_border_radius = True

    #     # Check for individual corner radii
    #     if TYPES.FK_RECT_CORNER_RADII in node:
    #         radii = node[TYPES.FK_RECT_CORNER_RADII]
    #         if isinstance(radii, list) and len(radii) == 4:
    #             border_radius = [int(r) for r in radii]
    #             has_border_radius = any(r > 0 for r in border_radius)

    #     return has_border_radius, border_radius

    @staticmethod
    @logs(logger, on=True)
    def extract_blur_from_node(node: dict) -> int:
        """Extract layer blur radius from a Figma node, checking nested layers. Returns 0 if no blur."""
        # Check effects on current node
        effects = node.get("effects")
        if effects and isinstance(effects, list):
            for effect in effects:
                if effect.get("visible", True) and effect.get("type") == "LAYER_BLUR" and "radius" in effect:
                    radius = effect["radius"]
                    if isinstance(radius, (int, float)) and radius > 0:
                        return int(radius)

        # Check nested children recursively
        children = node.get("children")
        if children and isinstance(children, list):
            for child in children:
                blur_radius = Extractor.extract_blur_from_node(child)
                if blur_radius > 0:
                    return blur_radius

        return 0

    @staticmethod
    @logs(logger, on=True)
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
    @logs(logger, on=True)
    def extract_rotation(node: dict[str, str | int | float | bool | dict | list]) -> int:
        """Extract rotation from a Figma node"""
        # Check for rotation property
        if "rotation" in node:
            rotation = node["rotation"]
            if isinstance(rotation, (int, float)):
                return int(rotation)

        # Check for rotation in absoluteTransform
        if "absoluteTransform" in node:
            transform_raw = node["absoluteTransform"]
            if isinstance(transform_raw, list) and len(transform_raw) >= 2:
                return 0

        # Default rotation
        return 0

    @staticmethod
    @logs(logger, on=True)
    def extract_opacity(node: dict[str, str | int | float | bool | dict | list]) -> int | float:
        """Extract opacity from a Figma node"""
        # Check for direct opacity property
        if "opacity" in node:
            opacity = node["opacity"]
            if isinstance(opacity, (int, float)):
                return int(opacity) if opacity == 1.0 else float(opacity)

        # Check for opacity in fills
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

        # Default opacity
        return 1

    @staticmethod
    @logs(logger, on=True)
    def extract_blur(node: dict[str, str | int | float | bool | dict | list]) -> int:
        """Extract layer blur radius from a Figma node, checking nested layers. Returns 0 if no blur."""
        # Check effects on current node
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

        # Check nested children recursively
        children_raw = node.get("children")
        if isinstance(children_raw, list):
            for child in children_raw:
                if isinstance(child, dict):
                    blur_radius = Extractor.extract_blur(child)
                    if blur_radius > 0:
                        return blur_radius

        return 0

    @staticmethod
    @logs(logger, on=True)
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
    @logs(logger, on=True)
    def extract_color_info(node: dict) -> tuple[str | None, str | None]:
        """
        Extracts the first visible solid fill color and its variable/style from a Figma node.
        Returns (hex_color, color_variable_id).
        """

        fills = node.get("fills")
        if fills and isinstance(fills, list):

            if len(fills) > 1:
                fill = fills[1]
            else:
                fill = fills[0]

            fill_type = fill.get("type")

            # Handle SOLID fills
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
                # Extract variable/style if present
                color_variable = None
                if "boundVariables" in fill and "color" in fill["boundVariables"]:
                    color_variable = fill["boundVariables"]["color"].get("id")
                elif "fillStyleId" in fill:
                    color_variable = fill["fillStyleId"]
                return hex_or_gradient_color, color_variable

            # Handle gradient fills
            elif fill.get("visible", True) and fill_type in ["GRADIENT_LINEAR", "GRADIENT_RADIAL", "GRADIENT_ANGULAR", "GRADIENT_DIAMOND"]:
                hex_or_gradient_color = Extractor._create_gradient_css(fill)
                # Extract variable/style if present
                color_variable = None

                if "boundVariables" in fill and "color" in fill["boundVariables"]:
                    color_variable = fill["boundVariables"]["color"].get("id")
                elif "fillStyleId" in fill:
                    color_variable = fill["fillStyleId"]
                return hex_or_gradient_color, color_variable
        return None, None

    @staticmethod
    @logs(logger, on=True)
    def _create_gradient_css(fill: dict) -> str:
        """
        Creates CSS gradient string from Figma gradient fill.
        """
        gradient_type = fill.get("type")
        gradient_stops = fill.get("gradientStops", [])
        gradient_handle_positions = fill.get("gradientHandlePositions", [])

        if not gradient_stops:
            return ""

        # Convert gradient stops to CSS format
        css_stops = []
        for stop in gradient_stops:
            color = stop.get("color", {})
            position = stop.get("position", 0)

            # Convert color to hex
            r = int(round(color.get("r", 0) * 255))
            g = int(round(color.get("g", 0) * 255))
            b = int(round(color.get("b", 0) * 255))
            a = color.get("a", 1)

            if a < 1:
                hex_color = f"#{r:02x}{g:02x}{b:02x}{int(a * 255):02x}"
            else:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"

            # Convert position to percentage
            percentage = int(position * 100)
            css_stops.append(f"{hex_color} {percentage}%")

        # Create gradient based on type
        if gradient_type == "GRADIENT_LINEAR":
            # Calculate angle from handle positions
            angle = Extractor._calculate_linear_angle(gradient_handle_positions)
            return f"linear-gradient({angle}deg\\, {'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_RADIAL":
            # For radial gradients, we'll use a simple radial format
            # Figma's radial gradients are more complex, but this is a good approximation
            return f"radial-gradient(circle\\, {'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_ANGULAR":
            # Angular gradients in CSS are conic gradients
            return f"conic-gradient({'\\, '.join(css_stops)})"

        elif gradient_type == "GRADIENT_DIAMOND":
            # Diamond gradients can be approximated with radial gradients
            return f"radial-gradient(ellipse at center\\, {'\\, '.join(css_stops)})"

        return ""

    @staticmethod
    @logs(logger, on=True)
    def _calculate_linear_angle(handle_positions: list) -> int:
        """
        Calculate the angle for linear gradient from handle positions.
        Returns angle in degrees (0-360).
        """
        if len(handle_positions) < 2:
            return 0

        # Get start and end positions
        start = handle_positions[0]
        end = handle_positions[1]

        # Calculate vector
        dx = end.get("x", 0) - start.get("x", 0)
        dy = end.get("y", 0) - start.get("y", 0)

        # Calculate angle in radians
        angle_rad = math.atan2(dy, dx)

        # Convert to degrees and normalize to 0-360
        angle_deg = math.degrees(angle_rad)
        angle_deg = (angle_deg + 360) % 360

        return int(angle_deg)

    @logs(logger, on=True)
    def extract_slide_config(slide_node):
        """
        Extract slideConfig from the hidden slideColors table in the slide node, including color and fontFamily for each color layer.
        Also extracts presentation palette colors found in the slideColors table.
        :param slide_node: Slide XML representation containing hidden slideColors table
        :return: tuple(config_dict, list_of_palette_colors)
        """

        config_dict = {}
        palette_colors = set()
        if not slide_node or not Extractor.get_node_property(slide_node, "children"):
            return config_dict, []

        children_raw = Extractor.get_node_property(slide_node, "children")
        if not isinstance(children_raw, list):
            return config_dict, []

        for node_child in children_raw:
            if not isinstance(node_child, dict):
                continue
            if Extractor.get_node_property(node_child, "name") == "slideColors":
                logger.info("[slideColors] Found slideColors table in slide")
                children_raw2 = Extractor.get_node_property(node_child, "children", [])
                if not isinstance(children_raw2, list):
                    continue
                for node_block in children_raw2:
                    if not isinstance(node_block, dict):
                        continue
                    block_type = Extractor.get_node_property(node_block, "name")
                    logger.info(f"[slideColors] Processing block type: {block_type}")
                    block_colors = {}
                    children_raw3 = Extractor.get_node_property(node_block, "children", [])
                    if not isinstance(children_raw3, list):
                        continue
                    for color_group in children_raw3:
                        if not isinstance(color_group, dict):
                            continue
                        color_hex = Extractor.get_node_property(color_group, "name")
                        if color_hex:
                            color_hex = color_hex.lower()
                            palette_colors.add(color_hex)
                        logger.info(f"[slideColors] Processing color group: {color_hex}")
                        block_objs = []
                        children_raw4 = Extractor.get_node_property(color_group, "children", [])
                        if not isinstance(children_raw4, list):
                            continue
                        for text_child in children_raw4:
                            if not isinstance(text_child, dict):
                                continue
                            if Extractor.is_node_type(text_child, "TEXT"):
                                text_obj = {}
                                color_val, color_var = Extractor.extract_color_info(text_child)
                                text_obj["color"] = color_val
                                if color_var:
                                    text_obj["color_variable"] = color_var
                                font_family = None
                                style_raw = text_child.get("style")
                                if isinstance(style_raw, dict) and "fontFamily" in style_raw:
                                    font_family = style_raw["fontFamily"]
                                text_obj["fontFamily"] = normalize_font_family(font_family)
                                if block_type == "figure":
                                    idx = Extractor.get_node_property(text_child, "name", "").strip()
                                    text_obj["figureName"] = idx
                                    logger.info(f"[slideColors] Found figure in {color_hex}: name='{idx}', color={color_val}, font={font_family}")
                                block_objs.append(text_obj)
                        block_colors[color_hex] = block_objs
                    config_dict[block_type] = block_colors
                    logger.info(f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups")
                    for color_hex, obj_list in block_colors.items():
                        logger.info(f"[slideConfig]   Color '{color_hex}': {len(obj_list)} objects")
        return config_dict, sorted(palette_colors)

    @staticmethod
    @logs(logger, on=True)
    def get_node_property(node: dict, key: str, default=None):
        return node.get(key, default)

    @staticmethod
    @logs(logger, on=True)
    def is_node_type(node: dict, node_type: str) -> bool:
        return node.get("type") == node_type
