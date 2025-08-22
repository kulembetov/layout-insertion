poetry run pytest tests/db_test.py -v

Покрыто тестами:
db_work
    PresentationLayoutManager
        select_layout_by_name
            test_select_layout_by_name_found
        select_layout_by_uid
            test_select_layout_by_uid_found
        insert
            test_insert_layout_success
        get_presentation_layout_ids_names
            test_get_presentation_layout_ids_names_success

    PresentationPaletteManager
        insert
            test_insert_palette_success
            test_insert_palette_empty_slides_layouts
            test_insert_palette_empty_colors
            test_insert_palette_exception_handling

    ColorSettingsManager
        insert
            test_insert_color_settings_success
            test_insert_color_settings_exception

    PresentationLayoutStylesManager
        insert
            test_insert_presentation_layout_styles_success
            test_insert_presentation_layout_styles_with_none_ids
            test_insert_presentation_layout_styles_exception
            test_insert_presentation_layout_styles_empty_string_ids

    LayoutRolesManager
        insert
            test_insert_layout_role_success
            test_insert_layout_role_with_none_layout_id
            test_insert_layout_role_different_case_roles
            test_insert_layout_role_exception
            test_insert_layout_role_empty_strings

    SlideLayoutManager
        insert_or_update
            test_insert_or_update_all_new_records
            test_insert_or_update_all_existing_records_no_changes
            test_insert_or_update_with_changes
            test_insert_or_update_exception
            test_insert_or_update_empty_cache

    SlideLayoutStylesManager
        insert_or_update

    SlideLayoutAdditionalInfoManager
        insert_or_update

    SlideLayoutDimensionsManager
        insert_or_update

    BlockLayoutManager
        insert

    BlockLayoutDimensionsManager
        insert

    PrecompiledImageManager
        insert

    BlockLayoutStylesManager
        insert

    BlockLayoutLimitManager
        insert

    BlockLayoutFigureManager
        insert

    BlockLayoutConfigManager
        insert

    BlockLayoutIndexConfigManager
        insert

    SlideLayoutIndexConfigManager
        insert
