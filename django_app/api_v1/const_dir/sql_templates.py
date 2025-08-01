# SQL templates for generating queries
SQL_TEMPLATES: dict[str, str] = {
    "slide_layout": """-- Create SlideLayout
INSERT INTO "SlideLayout" (
    "id", "name", "number", "isActive", "presentationLayoutId",
    "imagesCount", "maxTokensPerBlock", "maxWordsPerSentence", "minWordsPerSentence", "sentences",
    "isLast", "forGeneration"
) VALUES (
    '{slide_layout_id}',
    '{slide_layout_name}',
    {slide_layout_number},
    true,
    '{presentation_layout_id}',
    0,
    300,
    15,
    10,
    1,
    {is_last},
    {for_generation}
)
RETURNING *;""",

    "block_layout": """-- Create BlockLayouts
INSERT INTO "BlockLayout" ("id", "slideLayoutId", "blockLayoutType")
VALUES
{block_layout_values}
RETURNING *;""",

    "block_styles": """-- Create BlockLayoutStyles
INSERT INTO "BlockLayoutStyles" ("blockLayoutId", "textVertical", "textHorizontal", "fontSize", "weight", "zIndex", "color", "opacity", "textTransform", "borderRadius", "colorSettingsId")
VALUES
{styles_values}
RETURNING *;""",

    "block_dimensions": """-- Create BlockLayoutDimensions
INSERT INTO "BlockLayoutDimensions" ("blockLayoutId", "x", "y", "w", "h")
VALUES
{dimension_values}
RETURNING *;""",

    "figure": """-- Create Figures
INSERT INTO "Figure" ("id", "blockLayoutId", "name")
VALUES
{figure_values}
RETURNING *;""",

    "precompiled_image": """-- Create PrecompiledImages
INSERT INTO "PrecompiledImage" ("id", "blockLayoutId", "url", "color")
VALUES
{precompiled_image_values}
RETURNING *;""",

    "slide_layout_additional_info": """-- Create SlideLayoutAdditionalInfo
INSERT INTO "SlideLayoutAdditionalInfo" (
    "slideLayoutId", "percentesCount", "maxSymbolsInBlock", "hasHeaders", "type", "iconUrl", "infographicsType"
) VALUES (
    '{slide_layout_id}',
    {percentesCount},
    {maxSymbolsInBlock},
    {hasHeaders},
    '{type}'::"SlideLayoutType",
    '{icon_url}',
    {infographics_type}
)
RETURNING *;""",

    "slide_layout_dimensions": """-- Create SlideLayoutDimensions
INSERT INTO "SlideLayoutDimensions" (
    "slideLayoutId", "x", "y", "w", "h"
) VALUES (
    '{slide_layout_id}',
    {x},
    {y},
    {w},
    {h}
)
RETURNING *;""",

    "slide_layout_styles": """-- Create SlideLayoutStyles
INSERT INTO "SlideLayoutStyles" (
    "slideLayoutId"
) VALUES (
    '{slide_layout_id}'
)
RETURNING *;""",

    "block_layout_index_config": """-- Create BlockLayoutIndexConfig
INSERT INTO "BlockLayoutIndexConfig" (
    "id", "blockLayoutId", "indexColorId", "indexFontId"
)
VALUES
{block_layout_index_config_values}
RETURNING *;""",

    "slide_layout_index_config": """-- Create SlideLayoutIndexConfig
INSERT INTO "SlideLayoutIndexConfig" (
    "id", "presentationPaletteId", "configNumber", "slideLayoutId", "blockLayoutIndexConfigId", "blockLayoutConfigId"
)
VALUES
{slide_layout_index_config_values}
RETURNING *;""",
    "block_layout_limit": """-- Create BlockLayoutLimit\nINSERT INTO "BlockLayoutLimit" ("minWords", "maxWords", "blockLayoutId")\nVALUES\n{block_layout_limit_values}\nRETURNING *;"""
}
