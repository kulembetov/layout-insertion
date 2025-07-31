import re
from typing import Optional, Any

from api_v1.constants import CONSTANTS
from api_v1.utils.font import normalize_font_weight, normalize_font_family
from api_v1.constants import TYPES


# codeblock for 'extract_color_info', don't use/import this
def _hex_and_color_var(fill: dict) -> tuple[Optional[str], Optional[str]]:
    c = fill['color']
    r = int(round(c.get('r', 0) * 255))
    g = int(round(c.get('g', 0) * 255))
    b = int(round(c.get('b', 0) * 255))
    a = fill.get('opacity', c.get('a', 1))
    if a < 1:
        hex_color = '#{:02x}{:02x}{:02x}{:02x}'.format(r, g, b, int(a * 255))
    else:
        hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
    # Extract variable/style if present
    color_variable = None
    if 'boundVariables' in fill and 'color' in fill['boundVariables']:
        color_variable = fill['boundVariables']['color'].get('id')
    elif 'fillStyleId' in fill:
        color_variable = fill['fillStyleId']
    return hex_color, color_variable


class Extractor:
    @staticmethod
    def extract_base_figure_name(name: str) -> str:
        """Extract the base figure name from a block name (e.g., 'figure (logoRfs_0)' -> 'logoRfs')."""
        if not name:
            return ''
        name_match = re.search(r'\(([^)]+)\)', name)
        if name_match:
            base_name = name_match.group(1)
            # Remove trailing _<number> if present
            base_name = re.sub(r'_(\d+)$', '', base_name)
            return base_name
        return name

    @staticmethod
    def extract_figure_index(name: str) -> str:
        """Extract the trailing index (e.g., '_2') from a figure name, or return ''."""
        if not name:
            return ''
        index_match = re.search(r'_(\d+)$', name)
        if index_match:
            return index_match.group(1)
        return ''

    @staticmethod
    def extract_text_styles(node: dict[str, Any], sql_type: str) -> dict[str, Any]:
        """Extract text styling information with config defaults (no color)."""
        defaults = CONSTANTS.DEFAULT_STYLES.get(sql_type, CONSTANTS.DEFAULT_STYLES['default'])
        styles = {
            'textVertical': defaults['text_vertical'],
            'textHorizontal': defaults['text_horizontal'],
            'fontSize': defaults['font_size'],
            'weight': defaults['weight'],
            'textTransform': defaults['text_transform']
        }
        style = node.get(TYPES.FK_STYLE, {})
        if style:
            # Prefer Figma's actual values if present
            text_align_vertical = style.get('textAlignVertical', '').lower()
            if text_align_vertical in ['top', 'middle', 'bottom']:
                styles['textVertical'] = text_align_vertical
            elif text_align_vertical == 'center':
                styles['textVertical'] = 'middle'
            # Figma's textAlignHorizontal: 'LEFT', 'CENTER', 'RIGHT' (case-insensitive)
            text_align_horizontal = style.get('textAlignHorizontal', '').lower()
            if text_align_horizontal in ['left', 'center', 'right']:
                styles['textHorizontal'] = text_align_horizontal
            if 'fontSize' in style:
                styles['fontSize'] = round(style['fontSize'])
            if 'fontWeight' in style:
                styles['weight'] = normalize_font_weight(style['fontWeight'])
        return styles

    @staticmethod
    def extract_border_radius(node: dict[str, Any]) -> tuple[bool, list[int]]:
        """Extract corner radius information"""
        border_radius = [0, 0, 0, 0]  # Default: all corners 0
        has_border_radius = False

        # Check for cornerRadius property
        if TYPES.FK_BORDER_RADIUS in node:
            radius = node[TYPES.FK_BORDER_RADIUS]
            if isinstance(radius, (int, float)) and radius > 0:
                border_radius = [int(radius)] * 4
                has_border_radius = True

        # Check for individual corner radii
        if TYPES.FK_RECT_CORNER_RADII in node:
            radii = node[TYPES.FK_RECT_CORNER_RADII]
            if isinstance(radii, list) and len(radii) == 4:
                border_radius = [int(r) for r in radii]
                has_border_radius = any(r > 0 for r in border_radius)

        return has_border_radius, border_radius

    @staticmethod
    def extract_z_index(name: str) -> int:
        """Extract z-index from node name"""
        if 'z-index' in name:
            parts = name.split('z-index')
            if len(parts) > 1:
                after = parts[1].strip()
                match = re.findall(r'\d+', after)
                if match:
                    return int(match[0])
        return 0

    @staticmethod
    def extract_color_info(node: dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts the first visible solid fill color and its variable/style from a Figma node.
        Returns (hex_color, color_variable_id).
        """
        fills: Optional[list] = node.get('fills')
        if fills and isinstance(fills, list):
            for fill in fills:
                if fill.get(TYPES.FK_VISIBLE, True) and fill.get(TYPES.FK_TYPE) == 'SOLID' and 'color' in fill:
                    return _hex_and_color_var(fill)

        # Fallback: check for direct color field
        color = node.get('color')
        if color and isinstance(color, str):
            return color.lower(), None
        return None, None

    @staticmethod
    def extract_slide_config(slide_node):
        # !REFACTOR
        """
        Extract slideConfig from the hidden slideColors table in the slide node, including color and fontFamily for each color layer.
        Also extracts presentation palette colors found in the slideColors table.
        :param slide_node: Slide XML representation containing hidden slideColors table
        :return: tuple(config_dict, list_of_palette_colors)
        """
        config_dict = {}
        palette_colors = set()

        if not slide_node or not slide_node.get(TYPES.FK_CHILDREN):
            return config_dict, []

        for child in slide_node[TYPES.FK_CHILDREN]:
            if child.get(TYPES.FK_NAME) != TYPES.FK_SLIDE_COLORS:
                continue

            # logg.info("[slideColors] Found slideColors table in slide")

            for block in child.get(TYPES.FK_CHILDREN, []):
                block_type = block.get(TYPES.FK_NAME)
                # logg.info(f"[slideColors] Processing block type: {block_type}")

                block_colors = {}
                for color_group in block.get(TYPES.FK_CHILDREN, []):
                    color_hex = color_group.get(TYPES.FK_NAME).lower() if color_group.get(TYPES.FK_NAME) else ""
                    palette_colors.add(color_hex)

                    # logg.info(f"[slideColors] Processing color group: {color_hex}")

                    block_objs = []
                    for text_child in color_group.get(TYPES.FK_CHILDREN, []):
                        if text_child.get(TYPES.FK_TYPE) != TYPES.FT_TEXT:
                            continue

                        obj = {
                            "color": Extractor.extract_color_info(text_child)[0],  # Use 'color' instead of 'fill'
                            "fontFamily": normalize_font_family(
                                text_child[TYPES.FK_STYLE].get(TYPES.FK_FONT_FAMILY),
                            ),
                        }

                        if block_type == TYPES.BT_FIGURE:
                            obj["figureName"] = text_child.get(TYPES.FK_NAME, "").strip()

                        color_var = Extractor.extract_color_info(text_child)[1]
                        if color_var:
                            obj["color_variable"] = color_var

                        # logg.info(
                        #     f"[slideColors] Found figure in {color_hex}: "
                        #     f"name='{obj.get('figureName')}'; color={obj['color']}; font={obj['fontFamily']}"
                        # )

                        block_objs.append(obj)

                    block_colors[color_hex] = block_objs

                config_dict[block_type] = block_colors
                # logg.info(f"[slideConfig] Block type '{block_type}': Found {len(block_colors)} color groups")

        return config_dict, sorted(palette_colors)
