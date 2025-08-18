from db_work.implemented import block_layout_dimensions_manager, block_layout_manager, color_settings_manager, layout_roles_manager, precompiled_image_manager, presentation_layout_manager, presentation_layout_styles_manager, slide_layout_additional_info_manager, slide_layout_dimensions_manager, slide_layout_manager, slide_layout_styles_manager


class Executor:
    """Execute Insertion Logic."""

    def __init__(self, **tg_params):
        self.tg_params = tg_params

    def insert_or_update(self, layout_name: str, user_role: str):
        """Insert New Presentation Layout And Fill Related Table."""

        # Presentation Layout ===========================================
        # Времено
        update = True
        find_name = presentation_layout_manager.select_layout_by_name(layout_name)
        if find_name is not True:
            update = False
        print(f"Update: {update}")

        if update is True:
            layout_data = presentation_layout_manager.select_layout_by_name(layout_name)
            new_presentation_layout_id = layout_data[0] if layout_data else None

        # Create new Presentation Layout
        if update is False:
            new_presentation_layout_id = presentation_layout_manager.insert(name=layout_name)
            print(f"new_presentation_layout_id {new_presentation_layout_id}")

        # Create user role for new presentation layout
        if update is False:
            new_role = layout_roles_manager.insert(presentation_layout_id=new_presentation_layout_id, user_role=user_role)
            print(f"new_role {new_role}")

        # Crate new color id
        if update is False:
            new_color_id = color_settings_manager.insert()
            print(f"new_color_id {new_color_id}")

        # Create new presentation layout styles
        if update is False:
            new_presentation_layout_styles_id = presentation_layout_styles_manager.insert(presentation_layout_id=new_presentation_layout_id, color_settings_id=new_color_id)
            print(f"new_presentation_layout_styles_id {new_presentation_layout_styles_id}")

        # Slide Layout ===========================================
        # Create new slide layouts or update existing slide layouts.
        slide_layouts_data = slide_layout_manager.insert_or_update(presentation_layout_id=new_presentation_layout_id)

        # Create new slide_layout_styles for every new slide layout
        slide_layout_styles_manager.insert_or_upate(slide_layouts=slide_layouts_data)

        # Create new slide layout dimensions for every new slide layout
        slide_layout_dimensions_manager.insert_or_update(slide_layouts=slide_layouts_data)

        # Create new slide layout addition info for every new slide layout
        slide_layout_additional_info_manager.insert_or_update(slide_layouts=slide_layouts_data)

        # Block Layout ===========================================
        # Create new block layouts
        block_layout_data = block_layout_manager.insert(slide_layouts_data)

        # Create new block layout dimensions
        block_layout_dimensions_manager.insert_or_update(block_layout_data)

        # Create new precompiled images for every new block layout
        new_precompiled_images = precompiled_image_manager.insert(block_layout_data, **self.tg_params)
        if new_precompiled_images:
            print(f"new_precompiled_images {len(new_precompiled_images)}")


executor = Executor()

if __name__ == "__main__":
    layout_name = "qweryuiyhgf544ss65hsss6b"
    user_role = "USER"

    # executor.insert_or_update(layout_name, user_role=user_role)

    miniature_path = "miniature_path"
    miniature_extension = "miniature_extension"
    layout_name = "layout_namea"

    executor = Executor(
        path=miniature_path,
        extension=miniature_extension,
        layout_name=layout_name,
    )
    executor.insert_or_update(layout_name, user_role="USER")


# # classic
# '019006b0-03af-7b04-a66f-8d31b0a08769'
# # raif
# '0197c55e-1c1b-7760-9525-f51752cf23e2'
