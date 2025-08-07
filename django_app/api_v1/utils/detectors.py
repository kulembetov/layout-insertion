import re

from django_app.api_v1.constants import BLOCKS, CONSTANTS, SLIDES, TYPES


def detect_slide_type(container_name: str, slide_number: int) -> str:
    """Detect slide type using only config.py as the source of truth."""
    # Use config mapping for container name to slide number
    key = container_name.strip().lower()
    number = SLIDES.CONTAINER_NAME_TO_SLIDE_NUMBER.get(key, slide_number)
    # Use config mapping for slide number to type
    return SLIDES.SLIDE_NUMBER_TO_TYPE.get(number, "classic")


def detect_block_type(node: dict) -> tuple[str, str]:
    """Detect block type from a Figma node, returning (figma_type, sql_type). Always returns a valid sql_type."""

    name = node.get(TYPES.FK_NAME, "").lower()
    node_type = node.get(TYPES.FK_TYPE, "")
    clean_name = re.sub(r"\s*z-index.*$", "", name)

    # Check for explicit mappings first, prioritize longer patterns
    sorted_patterns = sorted(CONSTANTS.FIGMA_TO_SQL_BLOCK_MAPPING.items(), key=lambda x: len(x[0]), reverse=True)
    for pattern, sql_type in sorted_patterns:
        if pattern in clean_name:
            if sql_type in BLOCKS.BLOCK_TYPES["block_layout_type_options"]:
                return pattern, sql_type

    type_mappings: dict[str, list[tuple[list[str], dict[str, str]]]] = {
        TYPES.FT_TEXT: [
            (["title", "heading", "header", "h1", "h2"], {"sql_type": "blockTitle"}),
            (["slide", "main"], {"sql_type": "slideTitle"} if any(kw in clean_name for kw in ["title", "heading", "header", "h1", "h2"]) else {}),
            (["subtitle", "sub", "subheading"], {"sql_type": "subTitle"}),
            (["number", "num", "count"], {"sql_type": "number"}),
            (["email", "@", "mail"], {"sql_type": "email"}),
            (["date", "time", "year", "month"], {"sql_type": "date"}),
            (["name", "author", "person"], {"sql_type": "name"}),
            (["percent", "%", "percentage"], {"sql_type": "percentage"}),
            ([], {"sql_type": "text"}),
        ],
        TYPES.FT_RECTANGLE: [(["background", "bg", "backdrop"], {"sql_type": "background"}), (["icon", "symbol"], {"sql_type": "icon"}), (["image", "img", "photo", "picture"], {"sql_type": "image"}), ([], {"sql_type": "figure"})],
        TYPES.FT_FRAME: [(["table", "grid", "data"], {"sql_type": "table"}), (["chart", "graph"], {"sql_type": "table"}), (["infographic", "infographik", "visual"], {"sql_type": "infographik"}), (["watermark", "mark"], {"sql_type": "watermark"}), ([], {"sql_type": "figure"})],
        TYPES.FT_GROUP: [(["table", "grid", "data"], {"sql_type": "table"}), (["chart", "graph"], {"sql_type": "table"}), (["infographic", "infographik", "visual"], {"sql_type": "infographik"}), (["watermark", "mark"], {"sql_type": "watermark"}), ([], {"sql_type": "figure"})],
    }

    mappings_for_node: list[tuple[list[str], dict[str, str]]] = type_mappings.get(node_type, [])
    for keywords, mapping in mappings_for_node:
        if not keywords or any(keyword in clean_name for keyword in keywords):
            mapped_sql_type: str = mapping.get("sql_type", "")
            if mapped_sql_type and mapped_sql_type in BLOCKS.BLOCK_TYPES["block_layout_type_options"]:
                return clean_name, mapped_sql_type
    return "text", "text"
