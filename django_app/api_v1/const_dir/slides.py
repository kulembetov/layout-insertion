from typing import Any

# Default values for new tables
SLIDE_LAYOUT_ADDITIONAL_INFO: dict[str, Any] = {"percentesCount": 0, "maxSymbolsInBlock": 0, "hasHeaders": False, "type": "classic", "infographicsType": None}

# Slide type detection patterns
SLIDE_TYPE_PATTERNS: dict[str, list[str]] = {"title": ["hero", "title", "cover"], "table": ["table", "grid"], "chart": ["chart", "graph", "data"], "infographics": ["infographic", "infographik", "visual"], "few_text": ["1cols", "2cols"], "optimal_text": ["3cols"], "many_text": ["4cols", "5cols", "6cols", "7cols", "8cols", "9cols", "10cols"]}

SLIDE_LAYOUT_TYPES: dict[str, str] = {
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

SLIDE_LAYOUT_DIMENSIONS: dict[str, int] = {"x": 0, "y": 0, "w": 1200, "h": 675}

SLIDE_NUMBER_TO_FOLDER: dict[int, str] = {1: "title", 2: "1cols", 3: "2cols", 4: "3cols", 5: "infographics", 6: "4cols", 7: "divider", 8: "table", 9: "6cols", 10: "7cols", 11: "8cols", 12: "chart", -1: "last"}

CONTAINER_NAME_TO_SLIDE_NUMBER: dict[str, int] = {"title": 1, "1cols": 2, "2cols": 3, "3cols": 4, "infographics": 5, "4cols": 6, "divider": 7, "table": 8, "6cols": 9, "7cols": 10, "8cols": 11, "chart": 12, "last": -1}

SLIDE_FOLDER_TO_MINIATURE_NUMBER: dict[str, int] = {
    "5cols": 5,
    "6cols": 6,
    "7cols": 7,
    "8cols": 8,
    "9cols": 9,
}

SLIDE_NUMBER_TO_NUMBER: dict[int, Any] = {1: None, 2: 1, 3: 2, 4: 3, 5: None, 6: 4, 7: None, 8: None, 9: 6, 10: 7, 11: 8, 12: None, -1: None}  # title  # 1cols  # 2cols  # 3cols  # infographics  # 4cols  # divider  # table  # 6cols  # 7cols  # 8cols  # chart  # last

SLIDE_NUMBER_TO_TYPE: dict[int, str] = {1: "title", 2: "fewText", 3: "optimalText", 4: "manyText", 5: "infographics", 6: "extraText", 7: "other", 8: "table", 9: "other", 10: "other", 11: "other", 12: "chart", -1: "last"}  # title  # 1cols  # 2cols  # 3cols  # infographics  # 4cols  # divider  # table  # 6cols  # 7cols  # 8cols  # chart  # last

WATERMARK_SLIDES: list = []

# Infographics type mapping based on slide layout name patterns
SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE: dict[str, dict[str, str]] = {
    "step_by_step": {"infographicsType": "grid_timeline"},
    "grid_cards_horizontal": {"infographicsType": "grid"},
    "grid_cards_vertical": {"infographicsType": "grid"},
    "timeline": {"infographicsType": "timeline"},
    "table_bottom": {"infographicsType": "table"},
    "center_horizontal_chart": {"infographicsType": "bar_horizontal"},
    "center_linear_chart": {"infographicsType": "line"},
    "center_circle_chart": {"infographicsType": "pie"},
    "center_ring_chart": {"infographicsType": "pie"},
    "center_bar_chart": {"infographicsType": "bar"},
}
