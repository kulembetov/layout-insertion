# Automatic blocks configuration
AUTO_BLOCKS = {
    "add_background": True,  # Always add background by default
    "add_watermark": False,  # Default to not adding watermark
    "background": {
        "color": "#ffffff",
        "dimensions": {
            "x": 0,
            "y": 0,
            "w": 1200,
            "h": 675
        },
        "z_index": 0
    },
    "watermark": {
        "dimensions": {
            "x": 1065,
            "y": 636,
            "w": 118,
            "h": 26
        }
    },
    # Special configuration for last slide (slide number -1)
    "last_slide": {
        "watermark1": {
            "dimensions": {
                "x": 785,
                "y": 40,
                "w": 380,
                "h": 114
            }
        }
    }
}

# Default dimensions for different block types
DEFAULT_DIMENSIONS = {
    'background': {
        'x': 0,
        'y': 0,
        'w': 1200,
        'h': 675
    },
    'slideTitle': {
        'x': 37,
        'y': 37,
        'w': 1125,
        'h': 85
    },
    'subTitle': {
        'x': 37,
        'y': 250,
        'w': 875,
        'h': 65
    },
    'blockTitle': {
        'x': 37,
        'y': 37,
        'w': 575,
        'h': 30
    },
    'text': {
        'x': 37,
        'y': 37,
        'w': 575,
        'h': 85
    },
    'number': {
        'x': 77,
        'y': 315,
        'w': 320,
        'h': 50
    },
    'default': {
        'x': 37,
        'y': 230,
        'w': 1125,
        'h': 405
    },
}

# Default styles by block type
DEFAULT_STYLES = {
    'slideTitle': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 50,
        'weight': 700,
        'text_transform': 'none'
    },
    'subTitle': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 25,
        'weight': 400,
        'text_transform': 'none'
    },
    'blockTitle': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 25,
        'weight': 700,
        'text_transform': 'none'
    },
    'text': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 20,
        'weight': 400,
        'text_transform': 'none'
    },
    'number': {
        'text_vertical': 'top',
        'text_horizontal': 'center',
        'font_size': 50,
        'weight': 700,
        'text_transform': 'none'
    },
    'default': {
        'text_vertical': 'top',
        'text_horizontal': 'left',
        'font_size': 20,
        'weight': 400,
        'text_transform': 'none'
    },
}

# Block type groups
BLOCK_TYPES = {
    "null_style_types": ['infographik', 'figure', 'table', 'background', 'image', 'icon'],
    "z_index_types": [
        'text', 'slideTitle', 'blockTitle', 'email', 'date', 'name',
        'percentage', 'image', 'infographik', 'table', 'figure', 'background', 'icon', 'subTitle', 'number', 'chart'
    ],
    # Synced with schema.prisma BlockLayoutType enum
    "block_layout_type_options": [
        'text',
        'slideTitle',
        'blockTitle',
        'email',
        'date',
        'name',
        'percentage',
        'image',
        'infographik',
        'table',
        'figure',
        'icon',
        'background',
        'watermark',
        'subTitle',
        'number',
        'chart'
    ],
}

BLOCK_TYPE_MIN_WORDS = {
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
