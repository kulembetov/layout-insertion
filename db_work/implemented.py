from db_work.services import BlockLayoutManager, ColorSettingsManager, LayoutRolesManager, PresentationLayoutManager, PresentationLayoutStylesManager, SlideLayoutAdditionalInfoManager, SlideLayoutDimensionsManager, SlideLayoutManager, SlideLayoutStylesManager

# Presentation Layout Managers
presentation_layout_manager = PresentationLayoutManager()
color_settings_manager = ColorSettingsManager()
presentation_layout_styles_manager = PresentationLayoutStylesManager()
layout_roles_manager = LayoutRolesManager()

# Slide Layout Managers
slide_layout_manager = SlideLayoutManager()
slide_layout_styles_manager = SlideLayoutStylesManager()
slide_layout_additional_inf_manager = SlideLayoutAdditionalInfoManager()
slide_layout_dimensions_manager = SlideLayoutDimensionsManager()
slide_layout_additional_info = SlideLayoutAdditionalInfoManager()

# Block Layout Managers
block_layout_manager = BlockLayoutManager()
