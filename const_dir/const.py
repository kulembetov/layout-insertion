# Base path for slide layout miniatures
MINIATURES_BASE_PATH = "/assets/miniatures/raiffeisen"

# Default ColorSettings ID to use for all blocks
DEFAULT_COLOR_SETTINGS_ID = "019565bd-99ce-792c-86fd-0188712beb9b"

# Default color
DEFAULT_COLOR = "#ffffff"

# Precompiled Images configuration
PRECOMPILED_IMAGES = {
    "base_url": "https://storage.yandexcloud.net/presentsimple-dev-s3/layouts/raiffeisen",
    "default_colors": [
        "#bae4e4",  # мятно-бирюзовый
        "#c6d6f2",  # холодно-синий
        "#dfe8f5",  # небесно-голубой
        "#e3dcf8",  # сиреневый
        "#f0f0f0",  # светло-серый
        "#f5e7e7",  # розово-бежевый
        "#fad2be"   # персиково-оранжевый
    ],
    "prefix": [
        "Green",
        "Blue",
        "Sky",
        "Purple",
        "Gray",
        "Pink",
        "Orange"
    ]
}

# Default Z-index mappings
Z_INDEX_DEFAULTS = {
    'background': 0,
    'watermark': 10,
    'figure': 1,
    'image': 2,
    'icon': 2,
    'infographik': 2,
    'table': 2,
    'text': 3,
    'slideTitle': 3,
    'subTitle': 3,
    'blockTitle': 3,
    'number': 3,
    'email': 3,
    'date': 3,
    'name': 3,
    'percentage': 3,
    'default': 1,
}

MINIATURE_EXTENSION = ".png"

# Output configuration
OUTPUT_CONFIG = {
    "output_dir": "my_sql_output",
    "filename_template": "{slide_layout_name}_{timestamp}.sql",
    "timestamp_format": "%b%d_%H-%M",  # e.g., Mar10_14-23
}

WATERMARK_SLIDES = []

FIGMA_TO_SQL_BLOCK_MAPPING = {
    'text': 'text',
    'slideTitle': 'slideTitle',
    'slidetitle': 'slideTitle',
    'slide_title': 'slideTitle',
    'blockTitle': 'blockTitle',
    'blocktitle': 'blockTitle',
    'block_title': 'blockTitle',
    'subTitle': 'subTitle',
    'subtitle': 'subTitle',
    'sub_title': 'subTitle',
    'image': 'image',
    'img': 'image',
    'picture': 'image',
    'background': 'background',
    'bg': 'background',
    'figure': 'figure',
    'fig': 'figure',
    'table': 'table',
    'infographik': 'infographik',
    'infographic': 'infographik',
    'chart': 'chart',
    'watermark': 'watermark',
    'icon': 'icon',
    'number': 'number',
    'num': 'number',
    'email': 'email',
    'date': 'date',
    'name': 'name',
    'percentage': 'percentage',
    'percent': 'percentage',
    '%': 'percentage',
    'title': 'slideTitle',
    'heading': 'slideTitle',
    'header': 'blockTitle',
    'paragraph': 'text',
    'body': 'text',
    'content': 'text',
    'caption': 'text',
    'label': 'text',
}

FIGMA_CONFIG = {
    'TARGET_WIDTH': 1200,
    'TARGET_HEIGHT': 675,
    'OUTPUT_DIR': 'figma_extract',
    'OUTPUT_FILE': 'extracted_data'
}

# Valid font weights - ONLY these are allowed
VALID_FONT_WEIGHTS = [300, 400, 700]
