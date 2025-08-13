import configuration as config

from .text import TextUtils


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
