MAX_SYMBOLS_IN_BLOCK = 200
CONTENT_TYPE = None

# Infographics type mapping based on slide layout name patterns
SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE = {
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

MINIATURES_BASE_PATH: str = "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/business/miniatures"
MINIATURE_EXTENSION: str = ".png"

SLIDE_NUMBER_TO_TYPE = {
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

SLIDE_NUMBER_TO_NUMBER = {
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

DEFAULT_COLOR: str = "#ffffff"
DEFAULT_COLOR_SETTINGS_ID: str = "019565bd-99ce-792c-86fd-0188712beb9b"
