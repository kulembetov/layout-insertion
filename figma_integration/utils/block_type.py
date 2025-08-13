import re

import configuration as config


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
