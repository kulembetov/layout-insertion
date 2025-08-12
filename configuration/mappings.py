# pyright: strict
from __future__ import annotations

from typing import Final

from .defaults import DEFAULT_COLOR
from .types import BlockLayoutType, Dimensions, Style, TextHorizontal, TextTransform, TextVertical

SLIDE_LAYOUT_TYPES: Final[dict[str, str]] = {
    "classic": "classic",
    "many_text": "manyText",
    "few_text": "fewText",
    "optimal_text": "optimalText",
    "chart": "chart",
    "table": "table",
    "infographics": "infographics",
    "title": "title",
    "last": "last",
    "other": "other",
}


AUTO_BLOCKS: Final[dict[str, object]] = {
    "add_background": True,
    "add_watermark": False,
    "background": {"color": DEFAULT_COLOR, "dimensions": Dimensions(x=0, y=0, w=1200, h=675)},
    "watermark": {"dimensions": Dimensions(x=1065, y=636, w=118, h=26)},
    "last_slide": {"watermark1": {"dimensions": Dimensions(x=785, y=40, w=380, h=114)}},
}


BLOCK_TYPES: Final[dict[str, list[str]]] = {
    "null_style_types": ["infographik", "figure", "table", "background", "image", "icon"],
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
    "block_layout_type_options": [t.value for t in BlockLayoutType],
}


BLOCK_TYPE_MIN_WORDS: Final[dict[str, int]] = {
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


Z_INDEX_DEFAULTS: Final[dict[str, int]] = {
    "background": 0,
    "watermark": 10,
    "figure": 1,
    "image": 2,
    "icon": 2,
    "infographik": 2,
    "table": 2,
    "text": 3,
    "slideTitle": 3,
    "subTitle": 3,
    "blockTitle": 3,
    "number": 3,
    "email": 3,
    "date": 3,
    "name": 3,
    "percentage": 3,
    "default": 1,
}


DEFAULT_DIMENSIONS: Final[dict[str, Dimensions]] = {
    "background": Dimensions(0, 0, 1200, 675),
    "slideTitle": Dimensions(37, 37, 1125, 85),
    "subTitle": Dimensions(37, 250, 875, 65),
    "blockTitle": Dimensions(37, 37, 575, 30),
    "text": Dimensions(37, 37, 575, 85),
    "number": Dimensions(77, 315, 320, 50),
    "default": Dimensions(37, 230, 1125, 405),
}


DEFAULT_STYLES: Final[dict[str, Style]] = {
    "slideTitle": Style(TextVertical.top, TextHorizontal.left, 50, 700, TextTransform.none),
    "subTitle": Style(TextVertical.top, TextHorizontal.left, 25, 400, TextTransform.none),
    "blockTitle": Style(TextVertical.top, TextHorizontal.left, 25, 700, TextTransform.none),
    "text": Style(TextVertical.top, TextHorizontal.left, 20, 400, TextTransform.none),
    "number": Style(TextVertical.top, TextHorizontal.center, 50, 700, TextTransform.none),
    "default": Style(TextVertical.top, TextHorizontal.left, 20, 400, TextTransform.none),
}


SLIDE_NUMBER_TO_FOLDER: Final[dict[int, str]] = {
    1: "title",
    2: "1cols",
    3: "2cols",
    4: "3cols",
    5: "infographics",
    6: "4cols",
    7: "divider",
    8: "table",
    9: "5cols",
    10: "6cols",
    11: "7cols",
    12: "8cols",
    13: "chart",
    14: "10cols",
    -1: "last",
}


SLIDE_NUMBER_TO_NUMBER: Final[dict[int, int | None]] = {
    1: None,  # title
    2: 1,  # 1cols
    3: 2,  # 2cols
    4: 3,  # 3cols
    5: None,  # infographics
    6: 4,  # 4cols
    7: None,  # divider
    8: None,  # table
    9: 5,  # 5 cols
    10: 6,  # 6cols
    11: 7,  # 7cols
    12: 8,  # 8cols
    13: None,  # chart
    14: 10,  # 10cols
    -1: None,  # last
}


SLIDE_NUMBER_TO_TYPE: Final[dict[int, str]] = {
    1: "title",  # title
    2: "fewText",  # 1cols
    3: "optimalText",  # 2cols
    4: "manyText",  # 3cols
    5: "infographics",  # infographics
    6: "extraText",  # 4cols
    7: "other",  # divider
    8: "table",  # table
    9: "other",  # 5 cols
    10: "other",  # 6cols
    11: "other",  # 7cols
    12: "other",  # 8cols
    13: "chart",  # chart
    14: "other",  # 10cols
    -1: "last",  # last
}


CONTAINER_NAME_TO_SLIDE_NUMBER: Final[dict[str, int]] = {
    "title": 1,
    "1cols": 2,
    "2cols": 3,
    "3cols": 4,
    "infographics": 5,
    "4cols": 6,
    "divider": 7,
    "table": 8,
    "5cols": 9,
    "6cols": 10,
    "7cols": 11,
    "8cols": 12,
    "chart": 13,
    "10cols": 14,
    "last": -1,
}


FIGMA_TO_SQL_BLOCK_MAPPING: Final[dict[str, str]] = {
    "text": "text",
    "slideTitle": "slideTitle",
    "slidetitle": "slideTitle",
    "slide_title": "slideTitle",
    "blockTitle": "blockTitle",
    "blocktitle": "blockTitle",
    "block_title": "blockTitle",
    "subTitle": "subTitle",
    "subtitle": "subTitle",
    "sub_title": "subTitle",
    "image": "image",
    "background": "background",
    "figure": "figure",
    "table": "table",
    "infographik": "infographik",
    "chart": "chart",
    "watermark": "watermark",
    "icon": "icon",
    "number": "number",
    "num": "number",
    "email": "email",
    "date": "date",
    "name": "name",
    "percentage": "percentage",
}


SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE: Final[dict[str, dict[str, str]]] = {
    "step_by_step": {"infographicsType": "grid_timeline"},
    "grid_cards_horizontal": {"infographicsType": "grid"},
    "grid_cards_vertical": {"infographicsType": "grid"},
    "timeline": {"infographicsType": "timeline"},
    "table_bottom": {"infographicsType": "table"},
    "center_horizontal_chart": {"infographicsType": "bar_horizontal"},
    "center_linear_chart": {"infographicsType": "line"},
    "center_circle_chart": {"infographicsType": "pie"},
    "center_ring_chart": {"infographicsType": "doughnut"},
    "center_bar_chart": {"infographicsType": "bar"},
}
