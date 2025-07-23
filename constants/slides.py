# Slide layout types enum
SLIDE_LAYOUT_TYPES = {
    "classic": "classic",
    "many_text": "manyText",
    "few_text": "fewText",
    "optimal_text": "optimalText",
    "chart": "chart",
    "table": "table",
    "infographics": "infographics",
    "title": "title",
    "last": "last",
    "other": "other"
}

# Default values for user inputs
DEFAULT_VALUES = {
    "slide_layout_name": "grid_cards_horizontal",
    "slide_layout_number": 9,
    "presentation_layout_id": "0197c55e-1c1b-7760-9525-f51752cf23e2",
    "slide_layout_type": SLIDE_LAYOUT_TYPES["classic"],
    "num_blocks": 5,
}

# Default values for new tables
SLIDE_LAYOUT_ADDITIONAL_INFO = {
    "percentesCount": 0,
    "maxSymbolsInBlock": 0,
    "hasHeaders": False,
    "type": "classic",
    "infographicsType": None
}

SLIDE_LAYOUT_DIMENSIONS = {
    "x": 0,
    "y": 0,
    "w": 1200,
    "h": 675
}


SLIDE_NUMBER_TO_FOLDER = {
    1: "title",
    2: "1cols",
    3: "2cols",
    4: "3cols",
    5: "infographics",
    6: "4cols",
    7: "divider",
    8: "table",
    9: "6cols",
    10: "7cols",
    11: "8cols",
    12: "chart",
    -1: "last"
}

SLIDE_NUMBER_TO_NUMBER = {
    1: None,        # title
    2: 1,           # 1cols
    3: 2,           # 2cols
    4: 3,           # 3cols
    5: None,        # infographics
    6: 4,           # 4cols
    7: None,        # divider
    8: None,        # table
    9: 6,           # 6cols
    10: 7,          # 7cols
    11: 8,          # 8cols
    12: None,       # chart
    -1: None        # last
}

SLIDE_NUMBER_TO_TYPE = {
    1: 'title',         # title
    2: 'fewText',      # 1cols
    3: 'optimalText',  # 2cols
    4: 'manyText',     # 3cols
    5: 'infographics', # infographics
    6: 'extraText',    # 4cols
    7: 'other',        # divider
    8: 'table',        # table
    9: 'other',        # 6cols
    10: 'other',       # 7cols
    11: 'other',       # 8cols
    12: 'chart',       # chart
    -1: 'last'         # last
}

CONTAINER_NAME_TO_SLIDE_NUMBER = {
    "title": 1,
    "1cols": 2,
    "2cols": 3,
    "3cols": 4,
    "infographics": 5,
    "4cols": 6,
    "divider": 7,
    "table": 8,
    "6cols": 9,
    "7cols": 10,
    "8cols": 11,
    "chart": 12,
    "last": -1
}

# Infographics type mapping based on slide layout name patterns
SLIDE_LAYOUT_TO_INFOCRAPHICS_TYPE = {
    'step_by_step': {
        'infographicsType': 'grid_timeline'
    },
    'grid_cards_horizontal': {
        'infographicsType': 'grid'
    },
    'grid_cards_vertical': {
        'infographicsType': 'grid'
    },
    'timeline': {
        'infographicsType': 'timeline'
    },
    'table_bottom': {
        'infographicsType': 'table'
    },
    'center_horizontal_chart': {
        'infographicsType': 'bar_horizontal'
    },
    'center_linear_chart': {
        'infographicsType': 'line'
    },
    'center_circle_chart': {
        'infographicsType': 'pie'
    },
    'center_ring_chart': {
        'infographicsType': 'pie'
    },
    'center_bar_chart': {
        'infographicsType': 'bar'
    }
}

SLIDE_FOLDER_TO_MINIATURE_NUMBER = {
    "5cols": 5,
    "6cols": 6,
    "7cols": 7,
    "8cols": 8,
    "9cols": 9,
}

# Slide type detection patterns
SLIDE_TYPE_PATTERNS = {
    'title': ['hero', 'title', 'cover'],
    'table': ['table', 'grid'],
    'chart': ['chart', 'graph', 'data'],
    'infographics': ['infographic', 'infographik', 'visual'],
    'few_text': ['1cols', '2cols'],
    'optimal_text': ['3cols'],
    'many_text': ['4cols', '5cols', '6cols', '7cols', '8cols', '9cols', '10cols']
}
