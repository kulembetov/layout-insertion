from db_work.implemented import (
    block_layout_config_manager,
    block_layout_dimensions_manager,
    block_layout_figure_manager,
    block_layout_index_config_manager,
    block_layout_limit_manager,
    block_layout_manager,
    block_layout_styles_manager,
    color_settings_manager,
    layout_roles_manager,
    precompiled_image_manager,
    presentation_layout_manager,
    presentation_layout_styles_manager,
    presentation_palette_manager,
    slide_layout_additional_info_manager,
    slide_layout_dimensions_manager,
    slide_layout_manager,
    slide_layout_styles_manager,
)


class Executor:
    """Execute Insertion Logic."""

    def __init__(self, **tg_params):
        self.tg_params = tg_params

    def insert_or_update(self, layout_name: str, user_role: str):
        """Insert New Presentation Layout And Fill Related Table."""

        update = True
        layout_data = presentation_layout_manager.select_layout_by_name(layout_name)
        presentation_layout_id = layout_data[0] if layout_data else None
        if presentation_layout_id is None:
            update = False
        else:
            ...
            # Ром, вызови тут метод, который удалит талицы начиная от block layout

        # Presentation Layout ===========================================

        if update is False:
            # Insert new Presentation Layout
            presentation_layout_id = presentation_layout_manager.insert(name=layout_name)

            # Insert user role for new presentation layout
            layout_roles_manager.insert(presentation_layout_id=presentation_layout_id, user_role=user_role)

            # Insert new color id
            color_id = color_settings_manager.insert()

            # Insert new presentation layout styles
            presentation_layout_styles_manager.insert(presentation_layout_id=presentation_layout_id, color_settings_id=color_id)

        # Slide Layout ===========================================
        # Insert or update existing slide layouts.
        slide_layouts_data = slide_layout_manager.insert_or_update(presentation_layout_id=presentation_layout_id)

        # Insert or update slide layout styles for every  slide layout
        slide_layout_styles_manager.insert_or_upate(slide_layouts=slide_layouts_data)

        # Insert or update slide layout dimensions for every slide layout
        slide_layout_dimensions_manager.insert_or_update(slide_layouts=slide_layouts_data)

        # Insert or update slide layout addition info for every slide layout
        slide_layout_additional_info_manager.insert_or_update(slide_layouts=slide_layouts_data)

        # Insert or update slide layout addition info for every slide layout
        presentation_palette_data = presentation_palette_manager.insert(slide_layouts_data, presentation_layout_id)
        if presentation_palette_data:
            print(f"presentation_palette_data {len(presentation_palette_data)}")

        # Block Layout ===========================================
        # Insert new block layouts
        block_layout_data = block_layout_manager.insert(slide_layouts_data)

        # Insert new block layout dimensions
        block_layout_dimensions_manager.insert(block_layout_data)

        # Insert new precompiled images for every new block layout
        precompiled_image_manager.insert(block_layout_data, **self.tg_params)

        # Insert new styles for every new block layout
        block_layout_styles_manager.insert(block_layout_data)

        # Insert new limits for every block layout
        block_layout_limit_manager.insert(block_layout_data)

        # Insert new figures for every block layout
        block_layout_figure_manager.insert(block_layout_data)

        # Insert new configs for every block layout
        i = block_layout_config_manager.insert(block_layout_data)
        print(i)

        # Insert new index configs for every block layout
        block_layout_index_config_manager.insert(block_layout_data)


executor = Executor()

if __name__ == "__main__":
    layout_name = "nwnwnwnnwnwnwwnwn"
    user_role = "USER"

    miniature_path = "miniature_path"
    miniature_extension = "miniature_extension"

    executor = Executor(
        path=miniature_path,
        extension=miniature_extension,
        layout_name=layout_name,
    )
    executor.insert_or_update(layout_name, user_role="USER")
