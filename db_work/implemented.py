from db_work.services import (
    BlockLayoutConfigManager,
    BlockLayoutDimensionsManager,
    BlockLayoutFigureManager,
    BlockLayoutIndexConfigManager,
    BlockLayoutLimitManager,
    BlockLayoutManager,
    BlockLayoutStylesManager,
    BlockLayoutToDeleteManager,
    ColorSettingsManager,
    LayoutRolesManager,
    PrecompiledImageManager,
    PresentationLayoutManager,
    PresentationLayoutStylesManager,
    PresentationPaletteManager,
    SlideLayoutAdditionalInfoManager,
    SlideLayoutDimensionsManager,
    SlideLayoutIndexConfigManager,
    SlideLayoutManager,
    SlideLayoutStylesManager,
)

# Presentation Layout Managers
presentation_layout_manager = PresentationLayoutManager()
color_settings_manager = ColorSettingsManager()
presentation_layout_styles_manager = PresentationLayoutStylesManager()
layout_roles_manager = LayoutRolesManager()
presentation_palette_manager = PresentationPaletteManager()

# Slide Layout Managers
slide_layout_manager = SlideLayoutManager()
slide_layout_styles_manager = SlideLayoutStylesManager()
slide_layout_additional_info_manager = SlideLayoutAdditionalInfoManager()
slide_layout_dimensions_manager = SlideLayoutDimensionsManager()
slide_layout_index_config_manager = SlideLayoutIndexConfigManager()

# Block Layout Managers
block_layout_manager = BlockLayoutManager()
block_layout_dimensions_manager = BlockLayoutDimensionsManager()
precompiled_image_manager = PrecompiledImageManager()
block_layout_limit_manager = BlockLayoutLimitManager()
block_layout_styles_manager = BlockLayoutStylesManager()
block_layout_figure_manager = BlockLayoutFigureManager()
block_layout_config_manager = BlockLayoutConfigManager()
block_layout_index_config_manager = BlockLayoutIndexConfigManager()
block_layout_to_delete_manager = BlockLayoutToDeleteManager()
