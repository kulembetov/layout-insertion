from db_work.services import (
    BlockLayoutConfigManager,
    BlockLayoutDimensionsManagers,
    BlockLayoutFigureManagers,
    BlockLayoutIndexConfigManagers,
    BlockLayoutLimitManagers,
    BlockLayoutManager,
    BlockLayoutStylesManagers,
    ColorSettingsManager,
    LayoutRolesManager,
    PrecompiledImageManager,
    PresentationLayoutManager,
    PresentationLayoutStylesManager,
    SlideLayoutAdditionalInfoManager,
    SlideLayoutDimensionsManager,
    SlideLayoutManager,
    SlideLayoutStylesManager,
)

# Presentation Layout Managers
presentation_layout_manager = PresentationLayoutManager()
color_settings_manager = ColorSettingsManager()
presentation_layout_styles_manager = PresentationLayoutStylesManager()
layout_roles_manager = LayoutRolesManager()

# Slide Layout Managers
slide_layout_manager = SlideLayoutManager()
slide_layout_styles_manager = SlideLayoutStylesManager()
slide_layout_additional_info_manager = SlideLayoutAdditionalInfoManager()
slide_layout_dimensions_manager = SlideLayoutDimensionsManager()

# Block Layout Managers
block_layout_manager = BlockLayoutManager()
block_layout_dimensions_manager = BlockLayoutDimensionsManagers()
precompiled_image_manager = PrecompiledImageManager()
block_layout_limit_manager = BlockLayoutLimitManagers()
block_layout_styles_manager = BlockLayoutStylesManagers()
block_layout_figure_manager = BlockLayoutFigureManagers()
block_layout_config_manager = BlockLayoutConfigManager()
block_layout_index_config_manager = BlockLayoutIndexConfigManagers()
