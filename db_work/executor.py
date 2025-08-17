from db_work.implemented import block_layout_dimensions_manager, block_layout_manager, color_settings_manager, layout_roles_manager, precompiled_image_manager, presentation_layout_manager, presentation_layout_styles_manager, slide_layout_additional_info, slide_layout_dimensions_manager, slide_layout_manager, slide_layout_styles_manager


class Executor:
    """Execute Insertion Logic."""

    def __init__(self, **tg_params):
        self.tg_params = tg_params

    def insert(self, new_layout_name: str, user_role: str):
        """Insert New Presentation Layout And Fill Related Table."""

        # Presentation Layout ===========================================
        # Create new Presentation Layout
        new_presentation_layout_id = presentation_layout_manager.insert(name=new_layout_name)
        print(f"new_presentation_layout_id {new_presentation_layout_id}")

        # Create user role for new presentation layout
        new_role = layout_roles_manager.insert(presentation_layout_id=new_presentation_layout_id, user_role=user_role)
        print(f"new_role {new_role}")

        # Crate new color id
        new_color_id = color_settings_manager.insert()
        print(f"new_color_id {new_color_id}")

        # Create new presentation layout styles
        new_presentation_layout_styles_id = presentation_layout_styles_manager.insert(presentation_layout_id=new_presentation_layout_id, color_settings_id=new_color_id)
        print(f"new_presentation_layout_styles_id {new_presentation_layout_styles_id}")

        # Slide Layout ===========================================
        # Create new slide layouts or update existing slide layouts.
        new_or_updated_slide_layouts = slide_layout_manager.insert_or_update(presentation_layout_id=new_presentation_layout_id)
        if new_or_updated_slide_layouts:
            print(f"new_or_updated_slide_layouts {len(new_or_updated_slide_layouts)}")

        # Create new slide_layout_styles for every new slide layout
        new_slied_layout_styles = slide_layout_styles_manager.insert_or_upate(slide_layouts=new_or_updated_slide_layouts)
        if new_slied_layout_styles:
            print(f"new_slied_layout_styles {len(new_slied_layout_styles)}")

        # Create new slide layout dimensions for every new slide layout
        new_slide_layout_dimensions = slide_layout_dimensions_manager.insert(slide_layouts=new_or_updated_slide_layouts)
        if new_slide_layout_dimensions:
            print(f"new_slide_layout_dimensions {len(new_slide_layout_dimensions)}")

        # Create new slide layout addition info for every new slide layout
        new_slide_layout_additional_info = slide_layout_additional_info.insert_or_update(slide_layouts=new_or_updated_slide_layouts)
        if new_slide_layout_additional_info:
            print(f"new_slide_layout_additional_info {len(new_slide_layout_additional_info)}")

        # Block Layout ===========================================
        # Create new block layouts
        new_block_layouts = block_layout_manager.insert(new_or_updated_slide_layouts)
        if new_block_layouts:
            print(f"new_block_layout {len(new_block_layouts)}")

        # Create new block layout dimensions
        new_block_layout_dimensions = block_layout_dimensions_manager.insert(new_block_layouts)
        if new_block_layout_dimensions:
            print(f"new_block_layout_dimensions {len(new_block_layout_dimensions)}")

        # Create new precompiled images for every new block layout
        new_precompiled_images = precompiled_image_manager.insert(new_block_layouts, **self.tg_params)
        if new_precompiled_images:
            print(f"new_precompiled_images {len(new_precompiled_images)}")


executor = Executor()

if __name__ == "__main__":
    new_layout_name = "qweryuiyhgf54465h6b"
    user_role = "USER"

    executor.insert(new_layout_name, user_role=user_role)


# # classic
# '019006b0-03af-7b04-a66f-8d31b0a08769'
# # raif
# '0197c55e-1c1b-7760-9525-f51752cf23e2'
