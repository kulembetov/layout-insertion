from typing import Any

# Automatic blocks configuration
AUTO_BLOCKS: dict[str, Any] = {
    "add_background": True,  # Always add background by default
    "add_watermark": False,  # Default to not adding watermark
    "background": {
        "color": "#ffffff",
        "dimensions": {"x": 0, "y": 0, "w": 1200, "h": 675},
        "z_index": 0,
    },
    "watermark": {"dimensions": {"x": 1065, "y": 636, "w": 118, "h": 26}},
    # Special configuration for last slide (slide number -1)
    "last_slide": {"watermark1": {"dimensions": {"x": 785, "y": 40, "w": 380, "h": 114}}},
}

# Block type groups
BLOCK_TYPES: dict[str, list[str]] = {
    "null_style_types": [
        "infographik",
        "figure",
        "table",
        "background",
        "image",
        "icon",
    ],
    "z_index_types": [
        "text",
        "slideTitle",
        "blockTitle",
        "email",
        "date",
        "name",
        "percentage",
        "image",
        "infographik",
        "table",
        "figure",
        "background",
        "icon",
        "subTitle",
        "number",
        "chart",
    ],
    # Synced with schema.prisma BlockLayoutType enum
    "block_layout_type_options": [
        "text",
        "slideTitle",
        "blockTitle",
        "email",
        "date",
        "name",
        "percentage",
        "image",
        "infographik",
        "table",
        "figure",
        "icon",
        "background",
        "watermark",
        "subTitle",
        "number",
        "chart",
    ],
}

BLOCK_TYPE_MIN_WORDS: dict[str, int] = {
    "slideTitle": 3,
    "subTitle": 5,
    "blockTitle": 1,
    "text": 8,
    "percentage": 1,
    "number": 1,
    "date": 1,
    "name": 1,
    "email": 1,
}
