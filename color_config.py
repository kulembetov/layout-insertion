# color_config.py

# Example palette and block config IDs (replace with your real ones)
PRESENTATION_PALETTE_IDS = [
    "0197541e-5633-79c4-8974-de7f629c65f9",
    "0197541e-5633-795c-bd9b-ef46cddeb4d5",
    # ... add more as needed
]
BLOCK_LAYOUT_CONFIG_IDS = [
    "01975508-e5bd-7f3e-fa32-d5aab500d2c1",
    "01975508-e5bd-7145-3ab2-2e3f927f1303",
    # ... add more as needed
]

# Indices for each config number (can be any length)
# Used when outline is present on the slide
INDEX_COLOR_IDS_WITH_OUTLINE = [3, 4, 5]
# Used when outline is NOT present on the slide
INDEX_COLOR_IDS_WITHOUT_OUTLINE = [0, 1, 2]
INDEX_FONT_IDS = [0, 0, 0]
CONFIG_NUMBERS = [0, 1, 2]

# Figure name to color index mapping for each config number
FIGURE_INDEXES_BY_CONFIG = {
    0: {
        "outlineRfsOne": 0,
        "logoRfsOne": 3,
        "chartRfsOne": 5,
        "rectangleBigOutlineRfsOne": 0,
        # ... more figure names
    },
    1: {
        "outlineRfsOne": 1,
        "logoRfsOne": 4,
        "chartRfsOne": 5,
        # ... more figure names
    },
    2: {
        "outlineRfsOne": 2,
        "logoRfsOne": 5,
        "chartRfsOne": 4,
        # ... more figure names
    }
} 