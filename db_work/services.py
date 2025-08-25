import re
import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import delete, func, insert, null, select, update
from sqlalchemy.engine.row import Row
from sqlalchemy.sql.elements import ColumnElement

from db_work import constants
from db_work.database import BaseManager
from db_work.utils import BlockLayoutUtils, ColorUtils, SlideLayoutUtils, generate_uuid, get_slide_layout_data_from_cache
from log_utils import logs, setup_logger

logger = setup_logger(__name__)


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "PresentationLayout"

    def select_layout_by_name(self, name: str) -> Row | None:
        """Find an entry in 'PresentationLayout' by name."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            query = select(presentation_layout_table).where(cast(ColumnElement[bool], presentation_layout_table.c.name == name))
            result = session.execute(query).fetchone()

            if result:
                logger.info(f"PresentationLayoutManager: {name} is found in database. Start updating.\n")
                logger.info("Skip working PresentationLayoutManager.")
                logger.info("Skip working ColorSettingsManager.")
                logger.info("Skip working PresentationLayoutStylesManager.")
                logger.info("Skip working LayoutRolesManager.")
                logger.info("Skip working PresentationPaletteManager.\n")

            else:
                logger.info(f"PresentationLayoutManager: {name} isn't found in database. Start inserting.\n")

            return result

        return super().execute(logic, session)

    def select_layout_by_uid(self, str_uid: str) -> Row | None:
        """Find an entry in 'PresentationLayout' by uid."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            uid = uuid.UUID(str_uid)
            query = select(presentation_layout_table).where(cast(ColumnElement[bool], presentation_layout_table.c.id == uid))
            result = session.execute(query).fetchone()
            return result

        return super().execute(logic, session)

    def insert(self, name: str) -> str | None:
        """Inserts an entry in PresentationLayout table."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "name": name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        logger.info(f"PresentationLayoutManager: insert new presentation layout - {name}.\n")

        return super().execute(logic, session)

    def get_presentation_layout_ids_names(self) -> list[tuple[str, str]] | None:
        """Get all presentation layout names from the database."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            query = session.query(presentation_layout_table.c).all()
            return [(f"{row.id}", row.name) for row in query]

        return super().execute(logic, session)

    def get_presentation_layout_structure(self, presentation_layout_id: str) -> dict | None:
        """Получить полную структуру связей PresentationLayout со всеми связанными таблицами.

        Возвращает ID записей для понимания полной архитектуры базы данных,
        включая все 1:1, 1:N и N:N связи согласно PRESENTATION_LAYOUT_STRUCTURE.md.
        ColorSettings собираются из всех источников (PresentationLayoutStyles + BlockLayoutStyles).

        Args:
            presentation_layout_id: ID презентационного макета

        Returns:
            dict: Полная структура связей с ID или None в случае ошибки
        """
        presentation_layout_table, session = self.open_session("PresentationLayout")

        def logic():
            # 1. Проверяем существование PresentationLayout
            query = select(presentation_layout_table).where(cast(ColumnElement[bool], presentation_layout_table.c.id == presentation_layout_id))
            presentation_layout = session.execute(query).fetchone()

            if not presentation_layout:
                return None

            result = {
                "presentationLayout": presentation_layout.id,
                "slideLayouts": [],
                "layoutRoles": [],
                "fontStyleConfigurations": [],
                "presentationLayoutColors": [],
                "presentationLayoutStyles": None,
                "colorSettings": [],
                "presentationPalettes": [],
                "slideLayoutIndexConfigs": [],
                "blockLayoutIndexConfigs": [],
                "blockLayoutConfigs": [],
                "metadata": {"extracted_at": datetime.now().isoformat(), "presentation_layout_id": presentation_layout_id},
            }

            # Собираем все ID для избежания дублирования
            color_settings_ids = set()
            block_layout_config_ids = set()

            # 2. Получаем SlideLayout с полными связями
            slide_layout_table, _ = self.open_session("SlideLayout")
            slide_layouts_query = select(slide_layout_table.c.id).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            slide_layouts = session.execute(slide_layouts_query).fetchall()

            for slide_layout in slide_layouts:
                slide_layout_id = slide_layout.id
                slide_data = {"id": slide_layout_id, "slideLayoutStyles": None, "slideLayoutDimensions": None, "slideLayoutAdditionalInfo": None, "blockLayouts": []}

                # 2.1. SlideLayoutStyles (1:1)
                slide_layout_styles_table, _ = self.open_session("SlideLayoutStyles")
                styles_query = select(slide_layout_styles_table.c.slideLayoutId).where(slide_layout_styles_table.c.slideLayoutId == slide_layout_id)
                styles_result = session.execute(styles_query).fetchone()
                if styles_result:
                    slide_data["slideLayoutStyles"] = styles_result.slideLayoutId

                # 2.2. SlideLayoutDimensions (1:1)
                slide_layout_dimensions_table, _ = self.open_session("SlideLayoutDimensions")
                dimensions_query = select(slide_layout_dimensions_table.c.slideLayoutId).where(slide_layout_dimensions_table.c.slideLayoutId == slide_layout_id)
                dimensions_result = session.execute(dimensions_query).fetchone()
                if dimensions_result:
                    slide_data["slideLayoutDimensions"] = dimensions_result.slideLayoutId

                # 2.3. SlideLayoutAdditionalInfo (1:1)
                slide_layout_additional_info_table, _ = self.open_session("SlideLayoutAdditionalInfo")
                additional_info_query = select(slide_layout_additional_info_table.c.slideLayoutId).where(slide_layout_additional_info_table.c.slideLayoutId == slide_layout_id)
                additional_info_result = session.execute(additional_info_query).fetchone()
                if additional_info_result:
                    slide_data["slideLayoutAdditionalInfo"] = additional_info_result.slideLayoutId

                # 2.4. BlockLayout и его полные связи (1:N)
                block_layout_table, _ = self.open_session("BlockLayout")
                block_layouts_query = select(block_layout_table.c.id).where(block_layout_table.c.slideLayoutId == slide_layout_id)
                block_layouts = session.execute(block_layouts_query).fetchall()

                for block_layout in block_layouts:
                    block_layout_id = block_layout.id
                    block_data = {"id": block_layout_id, "blockLayoutDimensions": None, "blockLayoutStyles": None, "blockLayoutLimit": None, "figures": [], "precompiledImages": []}

                    # 2.4.1. BlockLayoutDimensions (1:1)
                    block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                    block_dimensions_query = select(block_layout_dimensions_table.c.blockLayoutId).where(block_layout_dimensions_table.c.blockLayoutId == block_layout_id)
                    block_dimensions_result = session.execute(block_dimensions_query).fetchone()
                    if block_dimensions_result:
                        block_data["blockLayoutDimensions"] = block_dimensions_result.blockLayoutId

                    # 2.4.2. BlockLayoutStyles (1:1) + ColorSettings
                    block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                    block_styles_query = select(block_layout_styles_table.c.blockLayoutId, block_layout_styles_table.c.colorSettingsId).where(block_layout_styles_table.c.blockLayoutId == block_layout_id)
                    block_styles_result = session.execute(block_styles_query).fetchone()
                    if block_styles_result:
                        block_data["blockLayoutStyles"] = block_styles_result.blockLayoutId
                        # Собираем ColorSettings ID из BlockLayoutStyles
                        if block_styles_result.colorSettingsId:
                            color_settings_ids.add(block_styles_result.colorSettingsId)

                    # 2.4.3. BlockLayoutLimit (1:1)
                    block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                    block_limit_query = select(block_layout_limit_table.c.blockLayoutId).where(block_layout_limit_table.c.blockLayoutId == block_layout_id)
                    block_limit_result = session.execute(block_limit_query).fetchone()
                    if block_limit_result:
                        block_data["blockLayoutLimit"] = block_limit_result.blockLayoutId

                    # 2.4.4. Figure (1:N)
                    figure_table, _ = self.open_session("Figure")
                    figures_query = select(figure_table.c.id).where(figure_table.c.blockLayoutId == block_layout_id)
                    figures = session.execute(figures_query).fetchall()
                    block_data["figures"] = [figure.id for figure in figures]

                    # 2.4.5. PrecompiledImage (1:N)
                    precompiled_image_table, _ = self.open_session("PrecompiledImage")
                    precompiled_images_query = select(precompiled_image_table.c.id).where(precompiled_image_table.c.blockLayoutId == block_layout_id)
                    precompiled_images = session.execute(precompiled_images_query).fetchall()
                    block_data["precompiledImages"] = [image.id for image in precompiled_images]

                    slide_data["blockLayouts"].append(block_data)

                result["slideLayouts"].append(slide_data)

            # 3. LayoutRoles (1:N) - количество ролей
            layout_roles_table, _ = self.open_session("LayoutRoles")
            layout_roles_query = select(layout_roles_table.c.presentationLayoutId).where(layout_roles_table.c.presentationLayoutId == presentation_layout_id)
            layout_roles = session.execute(layout_roles_query).fetchall()
            result["layoutRoles"] = len(layout_roles)

            # 4. FontStyleConfiguration (1:N)
            font_style_configuration_table, _ = self.open_session("FontStyleConfiguration")
            font_configs_query = select(font_style_configuration_table.c.id).where(font_style_configuration_table.c.presentationLayoutId == presentation_layout_id)
            font_configs = session.execute(font_configs_query).fetchall()
            result["fontStyleConfigurations"] = [config.id for config in font_configs]

            # 5. PresentationLayoutColor (1:N)
            presentation_layout_color_table, _ = self.open_session("PresentationLayoutColor")
            layout_colors_query = select(presentation_layout_color_table.c.id).where(presentation_layout_color_table.c.presentationLayoutId == presentation_layout_id)
            layout_colors = session.execute(layout_colors_query).fetchall()
            result["presentationLayoutColors"] = [color.id for color in layout_colors]

            # 6. PresentationLayoutStyles (1:1) + ColorSettings
            presentation_layout_styles_table, _ = self.open_session("PresentationLayoutStyles")
            layout_styles_query = select(presentation_layout_styles_table.c.id, presentation_layout_styles_table.c.colorSettingsId).where(presentation_layout_styles_table.c.presentationLayoutId == presentation_layout_id)
            layout_styles = session.execute(layout_styles_query).fetchone()

            if layout_styles:
                result["presentationLayoutStyles"] = layout_styles.id
                # Добавляем ColorSettings ID из PresentationLayoutStyles
                if layout_styles.colorSettingsId:
                    color_settings_ids.add(layout_styles.colorSettingsId)

            # 7. PresentationPalette и связанные таблицы (1:N)
            presentation_palette_table, _ = self.open_session("PresentationPalette")
            palettes_query = select(presentation_palette_table.c.id).where(presentation_palette_table.c.presentationLayoutId == presentation_layout_id)
            palettes = session.execute(palettes_query).fetchall()

            for palette in palettes:
                palette_id = palette.id
                palette_data = {"id": palette_id, "slideConfigSequences": []}

                # 7.1. SlideConfigSequence (1:N)
                slide_config_sequence_table, _ = self.open_session("SlideConfigSequence")
                sequences_query = select(slide_config_sequence_table.c.id).where(slide_config_sequence_table.c.presentationPaletteId == palette_id)
                sequences = session.execute(sequences_query).fetchall()
                palette_data["slideConfigSequences"] = [seq.id for seq in sequences]

                result["presentationPalettes"].append(palette_data)

            # 8. SlideLayoutIndexConfig - получаем все связующие записи (N:N)
            slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")

            # Получаем все SlideLayoutIndexConfig для данного PresentationLayout через связанные SlideLayout
            all_slide_layout_ids = [slide.id for slide in slide_layouts]
            if all_slide_layout_ids:
                slide_layout_index_configs_query = select(slide_layout_index_config_table.c.id, slide_layout_index_config_table.c.slideLayoutId, slide_layout_index_config_table.c.presentationPaletteId, slide_layout_index_config_table.c.blockLayoutIndexConfigId, slide_layout_index_config_table.c.blockLayoutConfigId).where(
                    slide_layout_index_config_table.c.slideLayoutId.in_(all_slide_layout_ids)
                )

                slide_layout_index_configs = session.execute(slide_layout_index_configs_query).fetchall()

                for config in slide_layout_index_configs:
                    result["slideLayoutIndexConfigs"].append({"id": config.id, "slideLayoutId": config.slideLayoutId, "presentationPaletteId": config.presentationPaletteId, "blockLayoutIndexConfigId": config.blockLayoutIndexConfigId, "blockLayoutConfigId": config.blockLayoutConfigId})
                    # Собираем BlockLayoutConfig ID
                    if config.blockLayoutConfigId:
                        block_layout_config_ids.add(config.blockLayoutConfigId)

            # 9. BlockLayoutIndexConfig - получаем все индексные конфигурации блоков
            # Собираем все BlockLayout ID для получения их BlockLayoutIndexConfig
            all_block_layout_ids = []
            for slide in result["slideLayouts"]:
                for block in slide["blockLayouts"]:
                    all_block_layout_ids.append(block["id"])

            if all_block_layout_ids:
                block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                block_index_configs_query = select(block_layout_index_config_table.c.id, block_layout_index_config_table.c.blockLayoutId, block_layout_index_config_table.c.indexColorId, block_layout_index_config_table.c.indexFontId).where(block_layout_index_config_table.c.blockLayoutId.in_(all_block_layout_ids))

                block_index_configs = session.execute(block_index_configs_query).fetchall()

                for config in block_index_configs:
                    result["blockLayoutIndexConfigs"].append({"id": config.id, "blockLayoutId": config.blockLayoutId, "indexColorId": config.indexColorId, "indexFontId": config.indexFontId})

            # 10. BlockLayoutConfig - получаем все уникальные конфигурации блоков
            if block_layout_config_ids:
                block_layout_config_table, _ = self.open_session("BlockLayoutConfig")
                block_configs_query = select(block_layout_config_table.c.id).where(block_layout_config_table.c.id.in_(list(block_layout_config_ids)))
                block_configs = session.execute(block_configs_query).fetchall()
                result["blockLayoutConfigs"] = [config.id for config in block_configs]

            # Финализируем массив ColorSettings (убираем дублирование)
            result["colorSettings"] = list(color_settings_ids)

            logger.info("Получил все связи по PresentationLayout. Начался процесс удаления.")

            return result

        return super().execute(logic, session)

    def delete_presentation_layout_structure(self, presentation_layout_id: str) -> bool:
        """Удалить полную структуру PresentationLayout со всеми связанными данными.

        Сначала получает структуру связей через get_presentation_layout_structure,
        затем удаляет все записи в строго определённом порядке, исключающем ошибки внешних ключей:

        Порядок удаления:
        0. Обнуление parentLayoutId в UserBlockLayout (сохранение пользовательских данных)
        1. SlideConfigSequence
        2. SlideLayoutIndexConfig
        3. BlockLayoutIndexConfig
        4. Figure
        5. PrecompiledImage
        6. BlockLayoutLimit
        7. BlockLayoutDimensions
        8. BlockLayoutStyles
        9. BlockLayout
        10. SlideLayoutDimensions
        11. SlideLayoutStyles
        12. SlideLayoutAdditionalInfo
        13. SlideLayout
        14. PresentationPalette
        15. BlockLayoutConfig
        16. FontStyleConfiguration
        17. PresentationLayoutColor
        18. LayoutRoles
        19. PresentationLayoutStyles
        20. ColorSettings
        21. PresentationLayout

        Args:
            presentation_layout_id: ID презентационного макета для удаления

        Returns:
            bool: True если удаление прошло успешно, False в случае ошибки
        """
        # Получаем структуру данных для удаления
        structure = self.get_presentation_layout_structure(presentation_layout_id)

        if not structure:
            print(f"PresentationLayout с ID {presentation_layout_id} не найден")
            return False

        presentation_layout_table, session = self.open_session("PresentationLayout")

        def logic():
            try:

                slide_layout_ids = [slide["id"] for slide in structure["slideLayouts"]]

                if slide_layout_ids:

                    user_slide_layout_table, _ = self.open_session("UserSlideLayout")
                    user_slide_layouts_query = select(user_slide_layout_table.c.id).where(user_slide_layout_table.c.parentLayoutId.in_(slide_layout_ids))
                    user_slide_layouts = session.execute(user_slide_layouts_query).fetchall()
                    user_slide_layout_ids = [usl.id for usl in user_slide_layouts]
                    if user_slide_layout_ids:
                        user_block_layout_table, _ = self.open_session("UserBlockLayout")
                        update_query = update(user_block_layout_table).where(user_block_layout_table.c.userSlideLayoutId.in_(user_slide_layout_ids)).values(parentLayoutId=None)

                        session.execute(update_query)
                        session.commit()
                        logger.info("Проставил NULL в UserBlockLayout в parentLayoutId")

                # 1. SlideConfigSequence (связаны с PresentationPalette)
                for palette in structure["presentationPalettes"]:
                    if palette["slideConfigSequences"]:
                        slide_config_sequence_table, _ = self.open_session("SlideConfigSequence")
                        for sequence_id in palette["slideConfigSequences"]:
                            delete_query = delete(slide_config_sequence_table).where(slide_config_sequence_table.c.id == sequence_id)
                            session.execute(delete_query)
                logger.info("Удалил SlideConfigSequence")

                # 2. SlideLayoutIndexConfig (связующая N:N таблица)
                if structure["slideLayoutIndexConfigs"]:
                    slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
                    for config in structure["slideLayoutIndexConfigs"]:
                        delete_query = delete(slide_layout_index_config_table).where(slide_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)
                logger.info("Удалил SlideLayoutIndexConfig")

                # 3. BlockLayoutIndexConfig
                if structure["blockLayoutIndexConfigs"]:
                    block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                    for config in structure["blockLayoutIndexConfigs"]:
                        delete_query = delete(block_layout_index_config_table).where(block_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)
                logger.info("Удалил BlockLayoutIndexConfig")

                # 4. Figure (связаны с BlockLayout)
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["figures"]:
                            figure_table, _ = self.open_session("Figure")
                            for figure_id in block["figures"]:
                                delete_query = delete(figure_table).where(figure_table.c.id == figure_id)
                                session.execute(delete_query)
                logger.info("Удалил Figure")

                # 5. PrecompiledImage (связаны с BlockLayout)
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["precompiledImages"]:
                            precompiled_image_table, _ = self.open_session("PrecompiledImage")
                            for image_id in block["precompiledImages"]:
                                delete_query = delete(precompiled_image_table).where(precompiled_image_table.c.id == image_id)
                                session.execute(delete_query)
                logger.info("Удалил PrecompiledImage")

                # 6. BlockLayoutLimit
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutLimit"]:
                            block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                            delete_query = delete(block_layout_limit_table).where(block_layout_limit_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)
                logger.info("Удалил BlockLayoutLimit")

                # 7. BlockLayoutDimensions
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutDimensions"]:
                            block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                            delete_query = delete(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)
                logger.info("Удалил BlockLayoutDimensions")

                # 8. BlockLayoutStyles
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutStyles"]:
                            block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                            delete_query = delete(block_layout_styles_table).where(block_layout_styles_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)
                logger.info("Удалил BlockLayoutStyles")

                # 9. BlockLayout
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        block_layout_table, _ = self.open_session("BlockLayout")
                        delete_query = delete(block_layout_table).where(block_layout_table.c.id == block["id"])
                        session.execute(delete_query)
                logger.info("Удалил BlockLayout")

                # 11. SlideLayoutDimensions
                for slide in structure["slideLayouts"]:
                    if slide["slideLayoutDimensions"]:
                        slide_layout_dimensions_table, _ = self.open_session("SlideLayoutDimensions")
                        delete_query = delete(slide_layout_dimensions_table).where(slide_layout_dimensions_table.c.slideLayoutId == slide["id"])
                        session.execute(delete_query)
                logger.info("Удалил SlideLayoutDimensions")

                # 12. SlideLayoutStyles
                for slide in structure["slideLayouts"]:
                    if slide["slideLayoutStyles"]:
                        slide_layout_styles_table, _ = self.open_session("SlideLayoutStyles")
                        delete_query = delete(slide_layout_styles_table).where(slide_layout_styles_table.c.slideLayoutId == slide["id"])
                        session.execute(delete_query)
                logger.info("Удалил SlideLayoutStyles")

                # 13. SlideLayoutAdditionalInfo
                for slide in structure["slideLayouts"]:
                    if slide["slideLayoutAdditionalInfo"]:
                        slide_layout_additional_info_table, _ = self.open_session("SlideLayoutAdditionalInfo")
                        delete_query = delete(slide_layout_additional_info_table).where(slide_layout_additional_info_table.c.slideLayoutId == slide["id"])
                        session.execute(delete_query)
                logger.info("Удалил SlideLayoutAdditionalInfo")

                # 14. SlideLayout
                for slide in structure["slideLayouts"]:
                    slide_layout_table, _ = self.open_session("SlideLayout")
                    delete_query = delete(slide_layout_table).where(slide_layout_table.c.id == slide["id"])
                    session.execute(delete_query)
                logger.info("Удалил SlideLayout")

                # 15. PresentationPalette
                for palette in structure["presentationPalettes"]:
                    presentation_palette_table, _ = self.open_session("PresentationPalette")
                    delete_query = delete(presentation_palette_table).where(presentation_palette_table.c.id == palette["id"])
                    session.execute(delete_query)
                logger.info("Удалил PresentationPalette")

                # 16. BlockLayoutConfig
                if structure["blockLayoutConfigs"]:
                    block_layout_config_table, _ = self.open_session("BlockLayoutConfig")
                    for config_id in structure["blockLayoutConfigs"]:
                        delete_query = delete(block_layout_config_table).where(block_layout_config_table.c.id == config_id)
                        session.execute(delete_query)
                logger.info("Удалил BlockLayoutConfig")

                # 17. FontStyleConfiguration
                if structure["fontStyleConfigurations"]:
                    font_style_configuration_table, _ = self.open_session("FontStyleConfiguration")
                    for config_id in structure["fontStyleConfigurations"]:
                        delete_query = delete(font_style_configuration_table).where(font_style_configuration_table.c.id == config_id)
                        session.execute(delete_query)
                logger.info("Удалил FontStyleConfiguration")

                # 18. PresentationLayoutColor
                if structure["presentationLayoutColors"]:
                    presentation_layout_color_table, _ = self.open_session("PresentationLayoutColor")
                    for color_id in structure["presentationLayoutColors"]:
                        delete_query = delete(presentation_layout_color_table).where(presentation_layout_color_table.c.id == color_id)
                        session.execute(delete_query)
                logger.info("Удалил PresentationLayoutColor")

                # 19. LayoutRoles
                if structure["layoutRoles"] > 0:
                    layout_roles_table, _ = self.open_session("LayoutRoles")
                    delete_query = delete(layout_roles_table).where(layout_roles_table.c.presentationLayoutId == presentation_layout_id)
                    session.execute(delete_query)
                logger.info("Удалил LayoutRoles")

                # 20. PresentationLayoutStyles
                if structure["presentationLayoutStyles"]:
                    presentation_layout_styles_table, _ = self.open_session("PresentationLayoutStyles")
                    delete_query = delete(presentation_layout_styles_table).where(presentation_layout_styles_table.c.id == structure["presentationLayoutStyles"])
                    session.execute(delete_query)
                logger.info("Удалил PresentationLayoutStyles")

                # 21. ColorSettings (только те, которые не используются в других местах)
                if structure["colorSettings"]:
                    color_settings_table, _ = self.open_session("ColorSettings")
                    for color_settings_id in structure["colorSettings"]:
                        # Проверяем, используется ли ColorSettings в других местах
                        # Проверяем PresentationLayoutStyles
                        pls_table, _ = self.open_session("PresentationLayoutStyles")
                        pls_check = select(pls_table.c.id).where(pls_table.c.colorSettingsId == color_settings_id)
                        pls_result = session.execute(pls_check).fetchone()

                        # Проверяем BlockLayoutStyles
                        bls_table, _ = self.open_session("BlockLayoutStyles")
                        bls_check = select(bls_table.c.blockLayoutId).where(bls_table.c.colorSettingsId == color_settings_id)
                        bls_result = session.execute(bls_check).fetchone()

                        # Удаляем только если не используется в других местах
                        if not pls_result and not bls_result:
                            delete_query = delete(color_settings_table).where(color_settings_table.c.id == color_settings_id)
                            session.execute(delete_query)
                logger.info("Удалил ColorSettings")

                # 22. Наконец, удаляем сам PresentationLayout
                delete_query = delete(presentation_layout_table).where(presentation_layout_table.c.id == presentation_layout_id)
                session.execute(delete_query)
                logger.info("Удалил PresentationLayout")

                # Коммитим все изменения
                session.commit()
                return True

            except Exception as e:
                session.rollback()
                print(f"Ошибка при удалении PresentationLayout структуры: {e}")
                return False

        return super().execute(logic, session)

    def get_deletion_summary(self, presentation_layout_id: str) -> dict | None:
        """Получить сводку о том, что будет удалено при удалении PresentationLayout.

        Полезно для подтверждения перед удалением.

        Args:
            presentation_layout_id: ID презентационного макета

        Returns:
            dict: Сводка с количеством записей для удаления или None в случае ошибки
        """
        structure = self.get_presentation_layout_structure(presentation_layout_id)

        if not structure:
            return None

        # Подсчитываем количество записей для удаления
        summary = {
            "presentation_layout_id": presentation_layout_id,
            "slide_layouts_count": len(structure["slideLayouts"]),
            "block_layouts_count": sum(len(slide["blockLayouts"]) for slide in structure["slideLayouts"]),
            "figures_count": sum(len(block["figures"]) for slide in structure["slideLayouts"] for block in slide["blockLayouts"]),
            "precompiled_images_count": sum(len(block["precompiledImages"]) for slide in structure["slideLayouts"] for block in slide["blockLayouts"]),
            "presentation_palettes_count": len(structure["presentationPalettes"]),
            "slide_config_sequences_count": sum(len(palette["slideConfigSequences"]) for palette in structure["presentationPalettes"]),
            "slide_layout_index_configs_count": len(structure["slideLayoutIndexConfigs"]),
            "block_layout_index_configs_count": len(structure["blockLayoutIndexConfigs"]),
            "block_layout_configs_count": len(structure["blockLayoutConfigs"]),
            "presentation_layout_colors_count": len(structure["presentationLayoutColors"]),
            "font_style_configurations_count": len(structure["fontStyleConfigurations"]),
            "layout_roles_count": structure["layoutRoles"],
            "color_settings_count": len(structure["colorSettings"]),
            "has_presentation_layout_styles": structure["presentationLayoutStyles"] is not None,
        }

        # Подсчитываем связанные стили и размеры
        slide_styles_count = sum(1 for slide in structure["slideLayouts"] if slide["slideLayoutStyles"])
        slide_dimensions_count = sum(1 for slide in structure["slideLayouts"] if slide["slideLayoutDimensions"])
        slide_additional_info_count = sum(1 for slide in structure["slideLayouts"] if slide["slideLayoutAdditionalInfo"])

        block_styles_count = sum(1 for slide in structure["slideLayouts"] for block in slide["blockLayouts"] if block["blockLayoutStyles"])
        block_dimensions_count = sum(1 for slide in structure["slideLayouts"] for block in slide["blockLayouts"] if block["blockLayoutDimensions"])
        block_limits_count = sum(1 for slide in structure["slideLayouts"] for block in slide["blockLayouts"] if block["blockLayoutLimit"])

        summary.update(
            {
                "slide_layout_styles_count": slide_styles_count,
                "slide_layout_dimensions_count": slide_dimensions_count,
                "slide_layout_additional_info_count": slide_additional_info_count,
                "block_layout_styles_count": block_styles_count,
                "block_layout_dimensions_count": block_dimensions_count,
                "block_layout_limits_count": block_limits_count,
            }
        )

        # Общее количество записей для удаления
        total_records = (
            1
            + summary["slide_layouts_count"]  # сам PresentationLayout
            + summary["block_layouts_count"]
            + summary["figures_count"]
            + summary["precompiled_images_count"]
            + summary["presentation_palettes_count"]
            + summary["slide_config_sequences_count"]
            + summary["slide_layout_index_configs_count"]
            + summary["block_layout_index_configs_count"]
            + summary["block_layout_configs_count"]
            + summary["presentation_layout_colors_count"]
            + summary["font_style_configurations_count"]
            + summary["layout_roles_count"]
            + summary["color_settings_count"]
            + (1 if summary["has_presentation_layout_styles"] else 0)
            + summary["slide_layout_styles_count"]
            + summary["slide_layout_dimensions_count"]
            + summary["slide_layout_additional_info_count"]
            + summary["block_layout_styles_count"]
            + summary["block_layout_dimensions_count"]
            + summary["block_layout_limits_count"]
        )

        summary["total_records_to_delete"] = total_records

        return summary


class PresentationPaletteManager(BaseManager):
    """Interacts With The PresentationPalette Table."""

    def __init__(self):
        super().__init__()
        self.table = "PresentationPalette"

    def insert(self, slides_layouts: list[dict], layout_id: str) -> tuple[list[dict], dict[str, str]]:
        """Inserts an entry in PresentationPalette table."""

        presentation_palette_table, session = self.open_session(self.table)

        def logic():
            data: list[dict] = []
            palette_ids: dict[str, str] = {}

            if not slides_layouts:
                return data, palette_ids

            presentation_palette_colors: list[str] = slides_layouts[0].get("presentationPaletteColors", [])

            if not presentation_palette_colors:
                return data, palette_ids

            for color in presentation_palette_colors:
                values = {
                    "id": generate_uuid(),
                    "presentationLayoutId": layout_id,
                    "color": color,
                }
                palette_ids[color] = values["id"]
                data.append(values)

                query = insert(presentation_palette_table).values(values)
                session.execute(query)

            session.commit()
            logger.info(f"PresentationPaletteManager: insert {len(data)} items.\n")
            # logger.info(f"PresentationPaletteManager: update {updated_data} items.\n")
            return data, palette_ids

        return super().execute(logic, session)


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()
        self.table = "ColorSettings"

    def insert(self) -> str | None:
        """Inserts an entry in ColorSettings table."""

        color_settings_table, session = self.open_session(self.table)

        def logic():
            new_color_id = generate_uuid()
            values = {"id": new_color_id, "count": 1, "lightenStep": 0.3, "darkenStep": 0.3, "saturationAdjust": 0.3}
            query = insert(color_settings_table).values(values)
            session.execute(query)
            session.commit()

            return new_color_id if new_color_id else None

        logger.info("ColorSettingsManager: insert new color settings.\n")

        return super().execute(logic, session)


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()
        self.table = "PresentationLayoutStyles"

    def insert(self, presentation_layout_id: str | None, color_settings_id: str | None) -> str | None:
        """Inserts an entry in PresentationLayoutStyles table."""

        presentation_layout_styles_table, session = self.open_session(self.table)

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "colorSettingsId": color_settings_id, "presentationLayoutId": presentation_layout_id}
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        logger.info("PresentationLayoutStylesManager: insert new presentation layout styles.\n")

        return super().execute(logic, session)


class LayoutRolesManager(BaseManager):
    """Interacts With The LayoutRoles Table."""

    def __init__(self):
        super().__init__()
        self.table = "LayoutRoles"

    def insert(self, presentation_layout_id: str | None, user_role: str) -> tuple[str] | None:
        """Insert an entry in LayoutRoles Table."""

        layout_roles_table, session = self.open_session(self.table)

        def logic():
            values = {"presentationLayoutId": presentation_layout_id, "role": user_role.upper()}
            query = insert(layout_roles_table).values(values)
            session.execute(query)
            session.commit()
            return presentation_layout_id, user_role

        logger.info("LayoutRolesManager: insert new layout role.\n")

        return super().execute(logic, session)


@logs(logger, on=True)
class SlideLayoutManager(BaseManager):
    """Interacts With The SlideLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayout"

    @logs(logger, on=True)
    def insert_or_update(self, presentation_layout_id: str | None) -> list[dict[Any, Any]]:
        """Insert or update an entry in SlideLayout table."""

        slide_layout_table, session = self.open_session(self.table)

        def logic():
            data = []
            updated_slide_layouts = 0
            added_slide_layouts = 0

            query = select(slide_layout_table).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            postgres_data = session.execute(query).fetchall()
            values = get_slide_layout_data_from_cache(presentation_layout_id)

            for value in values:
                keys_to_remove = ("dimensions", "blocks", "slide_type", "columns", "presentationPaletteColors", "slideConfig")
                value_for_slide_layout = {k: v for k, v in value.items() if k not in keys_to_remove}

                uuid_data_item = {k: v if k != "id" else generate_uuid() for k, v in value_for_slide_layout.items()}
                matching_row = [row for row in postgres_data if row.name == value_for_slide_layout["name"] and row.number == value_for_slide_layout["number"]]

                if len(matching_row) > 0:
                    compared_row = matching_row[0]
                    keys_to_compare = ["number", "imagesCount", "maxTokensPerBlock", "maxWordsPerSentence", "minWordsPerSentence", "sentences", "isLast", "forGeneration", "presentationLayoutIndexColor"]
                    need_update = False

                    for key in keys_to_compare:
                        if getattr(compared_row, key) != uuid_data_item[key]:
                            need_update = True
                            break

                    if need_update:
                        query = update(slide_layout_table).where(slide_layout_table.c.id == compared_row.id).values(**uuid_data_item)
                        session.execute(query)
                        session.commit()

                        updated_slide_layouts += 1
                        value_id = compared_row.id
                    else:
                        value_id = compared_row.id

                else:

                    new_entry = dict(uuid_data_item)
                    new_entry["id"] = generate_uuid()
                    query = insert(slide_layout_table).values(**new_entry)
                    session.execute(query)
                    session.commit()
                    value_id = new_entry["id"]
                    added_slide_layouts += 1

                value["id"] = value_id
                data.append(value)

            updated_query = select(slide_layout_table).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            session.execute(updated_query)

            logger.info(f"SlideLayoutManager: send {len(data)} slide layouts to other managers.")
            logger.info(f"SlideLayoutManager: insert {added_slide_layouts} items.")
            logger.info(f"SlideLayoutManager: update {updated_slide_layouts} items.\n")
            return data

        return super().execute(logic, session)

    def get_slides_by_presentation_layout_id(self, presentation_layout_id: str) -> list[dict] | None:
        """Get all slides for a specific presentation layout."""

        slide_layout_table, session = self.open_session(self.table)

        def logic():
            query = (
                session.query(
                    slide_layout_table.c.id,
                    slide_layout_table.c.name,
                    slide_layout_table.c.presentationLayoutId,
                )
                .filter(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
                .order_by(slide_layout_table.c.number)
            )

            result = query.all()

            return [{"id": row.id, "name": row.name, "presentationLayoutId": row.presentationLayoutId} for row in result]

        return super().execute(logic, session)

    def get_slide_layout_structure(self, slide_layout_ids: list[str]) -> dict | None:
        """Получить полную структуру связей SlideLayout со всеми связанными таблицами.

        Возвращает ID записей для понимания полной архитектуры слайдов,
        включая все 1:1, 1:N связи и связанные BlockLayout с их зависимостями.

        Args:
            slide_layout_ids: Список ID слайдов

        Returns:
            dict: Полная структура связей с ID или None в случае ошибки
        """
        if not slide_layout_ids:
            return None

        slide_layout_table, session = self.open_session("SlideLayout")

        def logic():
            # 1. Проверяем существование SlideLayout
            query = select(slide_layout_table).where(slide_layout_table.c.id.in_(slide_layout_ids))
            slide_layouts = session.execute(query).fetchall()

            if not slide_layouts:
                return None

            # Создаем результирующую структуру
            result = {
                "slideLayouts": [],
                "slideLayoutIndexConfigs": [],
                "blockLayoutIndexConfigs": [],
                "colorSettings": [],
                "metadata": {"extracted_at": datetime.now().isoformat(), "slide_layout_ids": slide_layout_ids, "total_slides": len(slide_layouts)},
            }

            # Собираем все ID для избежания дублирования
            color_settings_ids = set()

            # Обрабатываем каждый слайд
            for slide_layout in slide_layouts:
                slide_layout_id = slide_layout.id
                slide_data = {
                    "slideLayout": slide_layout_id,
                    "slideLayoutStyles": None,
                    "slideLayoutDimensions": None,
                    "slideLayoutAdditionalInfo": None,
                    "blockLayouts": [],
                }

                # 2. SlideLayoutStyles (1:1)
                slide_layout_styles_table, _ = self.open_session("SlideLayoutStyles")
                styles_query = select(slide_layout_styles_table.c.slideLayoutId).where(slide_layout_styles_table.c.slideLayoutId == slide_layout_id)
                styles_result = session.execute(styles_query).fetchone()
                if styles_result:
                    slide_data["slideLayoutStyles"] = styles_result.slideLayoutId

                # 3. SlideLayoutDimensions (1:1)
                slide_layout_dimensions_table, _ = self.open_session("SlideLayoutDimensions")
                dimensions_query = select(slide_layout_dimensions_table.c.slideLayoutId).where(slide_layout_dimensions_table.c.slideLayoutId == slide_layout_id)
                dimensions_result = session.execute(dimensions_query).fetchone()
                if dimensions_result:
                    slide_data["slideLayoutDimensions"] = dimensions_result.slideLayoutId

                # 4. SlideLayoutAdditionalInfo (1:1)
                slide_layout_additional_info_table, _ = self.open_session("SlideLayoutAdditionalInfo")
                additional_info_query = select(slide_layout_additional_info_table.c.slideLayoutId).where(slide_layout_additional_info_table.c.slideLayoutId == slide_layout_id)
                additional_info_result = session.execute(additional_info_query).fetchone()
                if additional_info_result:
                    slide_data["slideLayoutAdditionalInfo"] = additional_info_result.slideLayoutId

                # 5. BlockLayout и его полные связи (1:N)
                block_layout_table, _ = self.open_session("BlockLayout")
                block_layouts_query = select(block_layout_table.c.id).where(block_layout_table.c.slideLayoutId == slide_layout_id)
                block_layouts = session.execute(block_layouts_query).fetchall()

                for block_layout in block_layouts:
                    block_layout_id = block_layout.id
                    block_data = {"id": block_layout_id, "blockLayoutDimensions": None, "blockLayoutStyles": None, "blockLayoutLimit": None, "figures": [], "precompiledImages": []}

                    # 5.1. BlockLayoutDimensions (1:1)
                    block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                    block_dimensions_query = select(block_layout_dimensions_table.c.blockLayoutId).where(block_layout_dimensions_table.c.blockLayoutId == block_layout_id)
                    block_dimensions_result = session.execute(block_dimensions_query).fetchone()
                    if block_dimensions_result:
                        block_data["blockLayoutDimensions"] = block_dimensions_result.blockLayoutId

                    # 5.2. BlockLayoutStyles (1:1) + ColorSettings
                    block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                    block_styles_query = select(block_layout_styles_table.c.blockLayoutId, block_layout_styles_table.c.colorSettingsId).where(block_layout_styles_table.c.blockLayoutId == block_layout_id)
                    block_styles_result = session.execute(block_styles_query).fetchone()
                    if block_styles_result:
                        block_data["blockLayoutStyles"] = block_styles_result.blockLayoutId
                        # Собираем ColorSettings ID из BlockLayoutStyles
                        if block_styles_result.colorSettingsId:
                            color_settings_ids.add(block_styles_result.colorSettingsId)

                    # 5.3. BlockLayoutLimit (1:1)
                    block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                    block_limit_query = select(block_layout_limit_table.c.blockLayoutId).where(block_layout_limit_table.c.blockLayoutId == block_layout_id)
                    block_limit_result = session.execute(block_limit_query).fetchone()
                    if block_limit_result:
                        block_data["blockLayoutLimit"] = block_limit_result.blockLayoutId

                    # 5.4. Figure (1:N)
                    figure_table, _ = self.open_session("Figure")
                    figures_query = select(figure_table.c.id).where(figure_table.c.blockLayoutId == block_layout_id)
                    figures = session.execute(figures_query).fetchall()
                    block_data["figures"] = [figure.id for figure in figures]

                    # 5.5. PrecompiledImage (1:N)
                    precompiled_image_table, _ = self.open_session("PrecompiledImage")
                    precompiled_images_query = select(precompiled_image_table.c.id).where(precompiled_image_table.c.blockLayoutId == block_layout_id)
                    precompiled_images = session.execute(precompiled_images_query).fetchall()
                    block_data["precompiledImages"] = [image.id for image in precompiled_images]

                    slide_data["blockLayouts"].append(block_data)

                result["slideLayouts"].append(slide_data)

            # 6. SlideLayoutIndexConfig - получаем все связующие записи для всех SlideLayout
            slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
            slide_layout_index_configs_query = select(slide_layout_index_config_table.c.id, slide_layout_index_config_table.c.slideLayoutId, slide_layout_index_config_table.c.presentationPaletteId, slide_layout_index_config_table.c.blockLayoutIndexConfigId, slide_layout_index_config_table.c.blockLayoutConfigId).where(
                slide_layout_index_config_table.c.slideLayoutId.in_(slide_layout_ids)
            )
            slide_layout_index_configs = session.execute(slide_layout_index_configs_query).fetchall()

            for config in slide_layout_index_configs:
                result["slideLayoutIndexConfigs"].append({"id": config.id, "slideLayoutId": config.slideLayoutId, "presentationPaletteId": config.presentationPaletteId, "blockLayoutIndexConfigId": config.blockLayoutIndexConfigId, "blockLayoutConfigId": config.blockLayoutConfigId})

            # 7. BlockLayoutIndexConfig - получаем все индексные конфигурации блоков
            # Собираем все BlockLayout ID для получения их BlockLayoutIndexConfig
            all_block_layout_ids = []
            for slide in result["slideLayouts"]:
                for block in slide["blockLayouts"]:
                    all_block_layout_ids.append(block["id"])

            if all_block_layout_ids:
                block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                block_index_configs_query = select(block_layout_index_config_table.c.id, block_layout_index_config_table.c.blockLayoutId, block_layout_index_config_table.c.indexColorId, block_layout_index_config_table.c.indexFontId).where(block_layout_index_config_table.c.blockLayoutId.in_(all_block_layout_ids))

                block_index_configs = session.execute(block_index_configs_query).fetchall()

                for config in block_index_configs:
                    result["blockLayoutIndexConfigs"].append({"id": config.id, "blockLayoutId": config.blockLayoutId, "indexColorId": config.indexColorId, "indexFontId": config.indexFontId})

            # Финализируем массив ColorSettings (убираем дублирование)
            result["colorSettings"] = list(color_settings_ids)

            logger.info("Получил все связи по SlideLayouts. Начался процесс удаления.")

            return result

        return super().execute(logic, session)

    def delete_slide_layout_structure(self, slide_layout_ids: list[str]) -> dict:
        """Удалить полную структуру SlideLayout со всеми связанными данными.

        Сначала получает структуру связей через get_slide_layout_structure,
        затем удаляет все записи в строго определённом порядке, исключающем ошибки внешних ключей:

        Порядок удаления:
        0. Обнуление parentLayoutId в UserBlockLayout (сохранение пользовательских данных)
        1. SlideLayoutIndexConfig
        2. BlockLayoutIndexConfig
        3. Figure
        4. PrecompiledImage
        5. BlockLayoutLimit
        6. BlockLayoutDimensions
        7. BlockLayoutStyles
        8. BlockLayout
        9. SlideLayoutDimensions
        10. SlideLayoutStyles
        11. SlideLayoutAdditionalInfo
        12. SlideLayout
        13. ColorSettings (только неиспользуемые)

        Args:
            slide_layout_ids: Список ID слайдов для удаления

        Returns:
            dict: Результат удаления с информацией об успешных и неудачных операциях
        """
        if not slide_layout_ids:
            return {"success": False, "message": "Список ID слайдов пуст", "deleted_slides": [], "failed_slides": []}

        # Получаем структуру данных для удаления
        structure = self.get_slide_layout_structure(slide_layout_ids)

        if not structure:
            return {"success": False, "message": "Слайды не найдены", "deleted_slides": [], "failed_slides": slide_layout_ids}

        slide_layout_table, session = self.open_session("SlideLayout")

        def logic():
            try:
                deleted_slides = []

                # Получаем все SlideLayout ID для удаления
                slide_layout_ids = [slide["slideLayout"] for slide in structure["slideLayouts"]]

                if slide_layout_ids:

                    user_slide_layout_table, _ = self.open_session("UserSlideLayout")
                    user_slide_layouts_query = select(user_slide_layout_table.c.id).where(user_slide_layout_table.c.parentLayoutId.in_(slide_layout_ids))
                    user_slide_layouts = session.execute(user_slide_layouts_query).fetchall()

                    user_slide_layout_ids = [usl.id for usl in user_slide_layouts]

                    if user_slide_layout_ids:
                        # Обнуляем parentLayoutId в UserBlockLayout для пользовательских блоков
                        user_block_layout_table, _ = self.open_session("UserBlockLayout")
                        update_query = update(user_block_layout_table).where(user_block_layout_table.c.userSlideLayoutId.in_(user_slide_layout_ids)).values(parentLayoutId=None)

                        result = session.execute(update_query)
                        updated_count = result.rowcount
                        print(f"Обнулено parentLayoutId в {updated_count} записях UserBlockLayout")

                logger.info("Обнулено parentLayoutId в NULL записи в UserBlockLayout")

                # Удаляем в правильном порядке согласно зависимостям внешних ключей

                # 1. SlideLayoutIndexConfig (связующая таблица)
                if structure["slideLayoutIndexConfigs"]:
                    slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
                    for config in structure["slideLayoutIndexConfigs"]:
                        delete_query = delete(slide_layout_index_config_table).where(slide_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)
                logger.info("Удалил таблицу SlideLayoutIndexConfig")

                # 2. BlockLayoutIndexConfig
                if structure["blockLayoutIndexConfigs"]:
                    block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                    for config in structure["blockLayoutIndexConfigs"]:
                        delete_query = delete(block_layout_index_config_table).where(block_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)
                logger.info("Удалил таблицу BlockLayoutIndexConfig")

                # Обрабатываем каждый слайд
                for slide in structure["slideLayouts"]:
                    slide_layout_id = slide["slideLayout"]

                    # 3. Figure (связаны с BlockLayout)
                    for block in slide["blockLayouts"]:
                        if block["figures"]:
                            figure_table, _ = self.open_session("Figure")
                            for figure_id in block["figures"]:
                                delete_query = delete(figure_table).where(figure_table.c.id == figure_id)
                                session.execute(delete_query)

                    logger.info("Удалил таблицу Figure")

                    # 4. PrecompiledImage (связаны с BlockLayout)
                    for block in slide["blockLayouts"]:
                        if block["precompiledImages"]:
                            precompiled_image_table, _ = self.open_session("PrecompiledImage")
                            for image_id in block["precompiledImages"]:
                                delete_query = delete(precompiled_image_table).where(precompiled_image_table.c.id == image_id)
                                session.execute(delete_query)
                    logger.info("Удалил таблицу PrecompiledImage")

                    # 5. BlockLayoutLimit
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutLimit"]:
                            block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                            delete_query = delete(block_layout_limit_table).where(block_layout_limit_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)
                    logger.info("Удалил таблицу BlockLayoutLimit")

                    # 6. BlockLayoutDimensions
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutDimensions"]:
                            block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                            delete_query = delete(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)
                    logger.info("Удалил таблицу BlockLayoutDimensions")

                    # 7. BlockLayoutStyles
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutStyles"]:
                            block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                            delete_query = delete(block_layout_styles_table).where(block_layout_styles_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)
                    logger.info("Удалил таблицу BlockLayoutStyles")

                    # 8. BlockLayout
                    for block in slide["blockLayouts"]:
                        block_layout_table, _ = self.open_session("BlockLayout")
                        delete_query = delete(block_layout_table).where(block_layout_table.c.id == block["id"])
                        session.execute(delete_query)
                    logger.info("Удалил таблицу BlockLayout")

                    # 9. SlideLayoutDimensions
                    if slide["slideLayoutDimensions"]:
                        slide_layout_dimensions_table, _ = self.open_session("SlideLayoutDimensions")
                        delete_query = delete(slide_layout_dimensions_table).where(slide_layout_dimensions_table.c.slideLayoutId == slide_layout_id)
                        session.execute(delete_query)
                    logger.info("Удалил таблицу SlideLayoutDimensions")

                    # 10. SlideLayoutStyles
                    if slide["slideLayoutStyles"]:
                        slide_layout_styles_table, _ = self.open_session("SlideLayoutStyles")
                        delete_query = delete(slide_layout_styles_table).where(slide_layout_styles_table.c.slideLayoutId == slide_layout_id)
                        session.execute(delete_query)
                    logger.info("Удалил таблицу SlideLayoutStyles")

                    # 11. SlideLayoutAdditionalInfo
                    if slide["slideLayoutAdditionalInfo"]:
                        slide_layout_additional_info_table, _ = self.open_session("SlideLayoutAdditionalInfo")
                        delete_query = delete(slide_layout_additional_info_table).where(slide_layout_additional_info_table.c.slideLayoutId == slide_layout_id)
                        session.execute(delete_query)
                    logger.info("Удалил таблицу SlideLayoutAdditionalInfo")

                    # 12. Удаляем сам SlideLayout
                    delete_query = delete(slide_layout_table).where(slide_layout_table.c.id == slide_layout_id)
                    session.execute(delete_query)
                    logger.info("Удалил таблицу SlideLayout")

                    deleted_slides.append(slide_layout_id)

                # 13. ColorSettings (только те, которые не используются в других местах)
                if structure["colorSettings"]:
                    color_settings_table, _ = self.open_session("ColorSettings")
                    for color_settings_id in structure["colorSettings"]:
                        # Проверяем, используется ли ColorSettings в других местах
                        # Проверяем PresentationLayoutStyles
                        pls_table, _ = self.open_session("PresentationLayoutStyles")
                        pls_check = select(pls_table.c.id).where(pls_table.c.colorSettingsId == color_settings_id)
                        pls_result = session.execute(pls_check).fetchone()

                        # Проверяем BlockLayoutStyles
                        bls_table, _ = self.open_session("BlockLayoutStyles")
                        bls_check = select(bls_table.c.blockLayoutId).where(bls_table.c.colorSettingsId == color_settings_id)
                        bls_result = session.execute(bls_check).fetchone()

                        # Удаляем только если не используется в других местах
                        if not pls_result and not bls_result:
                            delete_query = delete(color_settings_table).where(color_settings_table.c.id == color_settings_id)
                            session.execute(delete_query)
                logger.info("Удалил таблицу ColorSettings")

                # Коммитим все изменения
                session.commit()

                return {"success": True, "message": f"Успешно удалено {len(deleted_slides)} слайдов", "deleted_slides": deleted_slides, "failed_slides": [], "total_requested": len(slide_layout_ids), "total_deleted": len(deleted_slides)}

            except Exception as e:
                session.rollback()
                error_msg = f"Ошибка при удалении SlideLayout структуры: {e}"
                print(error_msg)
                return {"success": False, "message": error_msg, "deleted_slides": [], "failed_slides": slide_layout_ids, "total_requested": len(slide_layout_ids), "total_deleted": 0}

        return super().execute(logic, session)


class SlideLayoutStylesManager(BaseManager):
    """Interacts With The SlideLayoutStyles Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutStyles"

    def insert_or_upate(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert or update data in SlideLayoutStyles Table."""

        slide_layout_styles_table, session = self.open_session(self.table)

        def logic():
            data = []

            for item in slide_layouts:
                existing_query = select(slide_layout_styles_table.c.slideLayoutId).where(slide_layout_styles_table.c.slideLayoutId == item.get("id"))
                result = session.execute(existing_query).scalar_one_or_none()

                if not result:
                    values = {"slideLayoutId": item.get("id")}
                    data.append(values)

                    query = insert(slide_layout_styles_table).values(values)
                    session.execute(query)

            session.commit()
            logger.info(f"SlideLayoutStylesManager: insert {len(data)} items. \n")
            return data

        return super().execute(logic, session)


class SlideLayoutAdditionalInfoManager(BaseManager):
    """Interacts With The SlideLayoutAdditionalInfo Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutAdditionalInfo"

    def insert_or_update(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert or update an entry in SlideLayoutAdditionalInfo Table."""

        slide_layout_additional_info, session = self.open_session(self.table)

        def logic():
            data = []
            updated_items = 0
            added_items = 0

            if slide_layouts:
                for slide_layout in slide_layouts:
                    slide_layout_id = slide_layout.get("id")
                    slide_layout_type = slide_layout.get("slide_type")
                    slide_layout_name = slide_layout.get("name")
                    slide_layout_colunms = slide_layout.get("columns")

                    has_headers = False
                    percentes = 0
                    slide_layout_blocks = slide_layout.get("blocks")
                    for slide_layout_block in slide_layout_blocks:
                        if slide_layout_block.get("figma_type"):
                            has_headers = True
                        if slide_layout_block.get("percentage"):
                            percentes += 1

                    slide_infographics_type = None
                    for pattern, config_data in constants.SLIDE_LAYOUT_TO_INFOGRAPHICS_TYPE.items():
                        if pattern in slide_layout_name:
                            slide_infographics_type = config_data["infographicsType"]
                            break

                    slide_layout_icon_url = SlideLayoutUtils().build_slide_icon_url(slide_type=slide_layout_type, slide_name=slide_layout_name, columns=slide_layout_colunms)

                    values = {
                        "slideLayoutId": slide_layout_id,
                        "percentesCount": percentes,
                        "hasHeaders": has_headers,
                        "maxSymbolsInBlock": constants.MAX_SYMBOLS_IN_BLOCK,
                        "type": slide_layout_type,
                        "iconUrl": slide_layout_icon_url,
                        "infographicsType": slide_infographics_type,
                        "contentType": constants.CONTENT_TYPE,
                    }

                    existing_query = select(slide_layout_additional_info).where(slide_layout_additional_info.c.slideLayoutId == slide_layout_id)
                    result = session.execute(existing_query).one_or_none()

                    if result is None:
                        query = insert(slide_layout_additional_info).values(values)
                        session.execute(query)
                        data.append(values)
                        added_items += 1

                    else:
                        existing_values = dict(result._mapping)
                        should_update = any(existing_values[key] != value for key, value in values.items())

                        if should_update:
                            update_query = update(slide_layout_additional_info).where(slide_layout_additional_info.c.slideLayoutId == slide_layout_id).values(**values)
                            session.execute(update_query)
                            data.append(values)
                            updated_items += 1

                session.commit()

            logger.info(f"SlideLayoutAdditionalInfoManager: insert {added_items} items.")
            logger.info(f"SlideLayoutAdditionalInfoManager: update {updated_items} items.\n")

            return data

        return super().execute(logic, session)


class SlideLayoutDimensionsManager(BaseManager):
    """Interacts With The SlideLayoutDimensions Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutDimensions"

    def insert_or_update(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert or update an entry in SlideLayoutDimensions Table."""

        slide_layout_dimensions, session = self.open_session(self.table)

        def logic():
            data = []
            updated_items = 0
            added_items = 0

            for item in slide_layouts:

                dimensions = item.get("dimensions")
                slide_layout_id = item.get("id")

                values = {"slideLayoutId": item.get("id"), "x": 0, "y": 0, "w": dimensions.get("w"), "h": dimensions.get("h")}

                existing_query = select(slide_layout_dimensions).where(slide_layout_dimensions.c.slideLayoutId == slide_layout_id)
                result = session.execute(existing_query).one_or_none()

                if result is None:
                    data.append(values)
                    query = insert(slide_layout_dimensions).values(values)
                    session.execute(query)
                    added_items += 1

                else:
                    existing_values = dict(result._mapping)
                    should_update = any(existing_values[key] != value for key, value in values.items())

                    if should_update:
                        update_query = update(slide_layout_dimensions).where(slide_layout_dimensions.c.slideLayoutId == slide_layout_id).values(**values)
                        session.execute(update_query)
                        data.append(values)
                        updated_items += 1

            session.commit()

            logger.info(f"SlideLayoutDimensionsManager: insert {added_items} items.")
            logger.info(f"SlideLayoutDimensionsManager: update {updated_items} items.\n")

            return data

        return super().execute(logic, session)


class BlockLayoutManager(BaseManager):
    """Interacts With The BlockLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayout"

    def insert(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayout Table."""

        block_layout_table, session = self.open_session(self.table)

        def logic():
            data = []
            added_items = 0

            for slide_layout in slide_layouts:
                slide_layout_id = slide_layout.get("id")
                slide_layout_blocks = slide_layout.get("blocks")
                slide_layout_presentation_palette = slide_layout.get("presentationPaletteColors")

                for slide_layout_block in slide_layout_blocks:
                    block_layout_type = slide_layout_block.get("sql_type")
                    id = generate_uuid()

                    values = {"id": id, "blockLayoutType": block_layout_type, "slideLayoutId": slide_layout_id}
                    values_for_block_layout_table = values

                    query = insert(block_layout_table).values(values_for_block_layout_table)
                    session.execute(query)
                    added_items += 1

                    # Add block parametrs for other block layout managers
                    values["dimensions"] = slide_layout_block.get("dimensions")
                    values["name"] = slide_layout_block.get("name")
                    values["sql_type"] = slide_layout_block.get("sql_type")
                    values["precompiled_image_info"] = slide_layout_block.get("precompiled_image_info")
                    values["words"] = slide_layout_block.get("words")
                    values["presentation_palette"] = slide_layout_presentation_palette
                    values["styles"] = slide_layout_block.get("styles")
                    values["color"] = slide_layout_block.get("color")
                    values["slideConfig"] = slide_layout.get("slideConfig")
                    values["needs_null_styles"] = slide_layout_block.get("needs_null_styles")
                    values["slide_layout_id"] = slide_layout_id
                    data.append(values)

            session.commit()

            logger.info(f"BlockLayoutManager: insert {added_items} items.\n")
            return data

        return super().execute(logic, session)


class BlockLayoutDimensionsManager(BaseManager):
    """Interacts With The BlockLayoutDimensions Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutDimensions"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayoutDimensions Table."""

        block_layout_dimensions_table, session = self.open_session(self.table)

        data = []
        added_items = 0
        updated_items = 0

        def logic():
            nonlocal data
            nonlocal added_items
            nonlocal updated_items

            for block_layout in block_layouts:
                block_layout_dimensions = block_layout.get("dimensions")
                block_layout_id = block_layout.get("id")

                values = {
                    "blockLayoutId": block_layout_id,
                    "x": block_layout_dimensions.get("x"),
                    "y": block_layout_dimensions.get("y"),
                    "w": block_layout_dimensions.get("w"),
                    "h": block_layout_dimensions.get("h"),
                    "rotation": block_layout_dimensions.get("r", 0),
                }

                query = insert(block_layout_dimensions_table).values(values)
                session.execute(query)
                added_items += 1

            logger.info(f"BlockLayoutDimensionsManagers: insert {added_items} items.\n")

            data.append(values)
            session.commit()
            return data

        return super().execute(logic, session)


class PrecompiledImageManager(BaseManager):
    """Interacts With The PrecompiledImageManager Table."""

    def __init__(self):
        super().__init__()
        self.table = "PrecompiledImage"

    def insert(self, block_layouts: list[dict], **tg_params: dict[str, str]) -> list[dict]:
        """Insert an entry in PrecompiledImage Table."""

        precompiled_image_table, session = self.open_session(self.table)

        def logic():
            data = []

            for block_layout in block_layouts:
                precompiled_image_info = block_layout.get("precompiled_image_info")
                presentation_palette = block_layout.get("presentation_palette")

                if precompiled_image_info and presentation_palette:
                    for color in presentation_palette:
                        url = self._extract_precompiled_image_url(precompiled_image_info.get("name"), color, **tg_params)
                        values = {
                            "id": generate_uuid(),
                            "blockLayoutId": block_layout.get("id"),
                            "url": url,
                            "color": color,
                        }

                        data.append(values)
                        query = insert(precompiled_image_table).values(values)
                        session.execute(query)

            session.commit()
            logger.info(f"PrecompiledImageManager: insert {len(data)} items.\n")
            return data

        return super().execute(logic, session)

    @staticmethod
    def _extract_precompiled_image_url(name: str, color: str, **tg_params: dict[str, str]) -> str | None:
        if name is None:
            return None

        match = re.match(r"image precompiled ([^ ]+)(?: z-index \d+)?(?: (#[0-9a-fA-F]{3,6}))?", name)
        if not match:
            return None

        base_url = "https://storage.yandexcloud.net/"  # откуда его надо брать?
        path = tg_params["path"]
        layout_name = tg_params["layout_name"]
        block_name = match.group(1)
        ext = tg_params["extension"]

        match path:
            case "dev":
                path = "presentsimple-dev-s3"
            case "stage":
                path = "presentsimple-stage-s3"
            case "prod":
                path = "presentsimple-prod-s3"
            case _:
                raise ValueError(f"Unexpected path value: {path}")

        return f"{base_url}{path}/layouts/business/miniatures/{layout_name}/{block_name}_{color[1:]}.{ext}"


class BlockLayoutStylesManager(BaseManager):
    """Interacts With The BlockLayoutStyles Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutStyles"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayoutStyles Table."""

        block_layout_styles_table, session = self.open_session(self.table)

        def logic():
            data = []

            default_color = constants.DEFAULT_COLOR
            color_settings_id = constants.DEFAULT_COLOR_SETTINGS_ID

            for block_layout in block_layouts:
                block_layout_styles = block_layout.get("styles")
                border_radius = block_layout_styles.get("borderRadius")
                needs_null_styles = block_layout.get("needs_null_styles")
                # sql_type = block_layout.get("sql_type")

                weight = block_layout_styles.get("weight")
                weight = float(weight) if isinstance(weight, str) and weight.isdigit() else None
                weight = null() if weight is None else weight

                color_value = block_layout.get("color")
                color_value = ColorUtils.normalize_color(color_value) if color_value else None
                if not color_value or not color_value.startswith("#") or len(color_value) not in (4, 7):
                    color_value = default_color

                if needs_null_styles:
                    # if sql_type == 'background' or sql_type == 'figure':
                    layout_values = {
                        "blockLayoutId": block_layout.get("id"),
                        "textVertical": null(),
                        "textHorizontal": null(),
                        "fontSize": null(),
                        "weight": null(),
                        "zIndex": block_layout_styles.get("zIndex", 1),
                        "opacity": block_layout_styles.get("opacity"),
                        "textTransform": null(),
                        "borderRadius": border_radius,
                        "colorSettingsId": color_settings_id,
                        "color": color_value,
                    }
                else:
                    layout_values = {
                        "blockLayoutId": block_layout.get("id"),
                        "textVertical": block_layout_styles.get("textVertical"),
                        "textHorizontal": block_layout_styles.get("textHorizontal"),
                        "fontSize": block_layout_styles.get("fontSize"),
                        "weight": weight,
                        "zIndex": block_layout_styles.get("zIndex", 1),
                        "opacity": block_layout_styles.get("opacity"),
                        "textTransform": block_layout_styles.get("textTransform"),
                        "borderRadius": border_radius,
                        "colorSettingsId": color_settings_id,
                        "color": color_value,
                    }

                defoltes = {
                    # Defoltes
                    "pathName": null(),
                    "italic": False,
                    "underline": False,
                    "listType": null(),
                    "autoResize": False,
                    "background": null(),
                    "fontFamily": "roboto",
                    "gradientType": None,
                    "contentEditable": True,
                    "movable": True,
                    "removable": True,
                    "selectable": True,
                    "styleEditable": True,
                    "visible": True,
                    "cropOffsetX": 0,
                    "cropOffsetY": 0,
                    "cropScale": 1,
                }
                values = layout_values | defoltes

                data.append(values)
                query = insert(block_layout_styles_table).values(values)
                session.execute(query)

            session.commit()
            logger.info(f"BlockLayoutStylesManager: insert {len(data)} items.\n")
            return data

        return super().execute(logic, session)


class BlockLayoutLimitManager(BaseManager):
    """Interacts With The BlockLayoutLimit Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutLimit"
        self.block_layout_min_words = constants.BLOCK_TYPE_MIN_WORDS

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayoutLimit Table."""

        block_layout_limit_table, session = self.open_session(self.table)

        def logic():
            data = []

            min_words_config = self.block_layout_min_words

            for block_layout in block_layouts:
                block_layout_type = block_layout.get("sql_type")
                block_layout_id = block_layout.get("id")
                block_layout_words = block_layout.get("words", [])

                min_words = min_words_config.get(block_layout_type, 1)
                max_words = len(block_layout_words) if isinstance(block_layout_words, list) else 1

                values = {
                    "blockLayoutId": block_layout_id,
                    "maxWords": max_words,
                    "minWords": min_words,
                }

                query = insert(block_layout_limit_table).values(values)
                session.execute(query)
                data.append(values)

            session.commit()
            logger.info(f"BlockLayoutLimitManager: insert {len(data)} items.\n")
            return data

        return super().execute(logic, session)


class BlockLayoutFigureManager(BaseManager):
    """Interacts With The Figure Table."""

    def __init__(self):
        super().__init__()
        self.table = "Figure"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayoutDimensions Table."""

        figure_table, session = self.open_session(self.table)

        data = []

        def logic():
            nonlocal data

            for block_layout in block_layouts:
                block_layout_id = block_layout.get("id")
                block_layout_name = block_layout.get("name")
                block_layout_type = block_layout.get("sql_type")

                clean_block_name = BlockLayoutUtils().normalize_name(name=block_layout_name)

                if block_layout_type == "figure":
                    match = re.search(r"\(([^)]+)\)", clean_block_name)
                    if match:
                        figure_name = match.group(1)
                        figure_name = re.sub(r"_\d+", "", figure_name)
                    else:
                        figure_name = clean_block_name

                    values = {
                        "id": generate_uuid(),
                        "name": figure_name,
                        "createdAt": func.now(),
                        "blockLayoutId": block_layout_id,
                    }

                    query = insert(figure_table).values(values)
                    session.execute(query)

                    data.append(values)

            session.commit()
            logger.info(f"BlockLayoutFigureManager: insert {len(data)} items.\n")
            return data

        return super().execute(logic, session)


class BlockLayoutConfigManager(BaseManager):
    """Interacts With The BlockLayoutConfig Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutConfig"

    def insert(self, block_layouts: list[dict], palette_ids: dict[str, str]) -> tuple[list[dict], dict[str, dict[str, str]]]:
        """Insert an entry in BlockLayoutConfig Table."""

        block_layout_config_table, session = self.open_session(self.table)

        def logic():
            def safe_get(d: dict, key: str):
                return d.get(key, None) if d else None

            data = []
            palette_block_ids: dict[str, dict[str, str]] = {}

            if not block_layouts:
                return data, palette_block_ids

            slide_config: dict[str, dict[str, list[dict[str, str]]]] = block_layouts[0].get("slideConfig", {})
            presentation_palette = block_layouts[0].get("presentation_palette", [])
            if not slide_config or not presentation_palette:
                return data, palette_block_ids

            for color in presentation_palette:
                palette_block_ids[color] = {}
                values = {
                    "id": generate_uuid(),
                    "text": self._collect(safe_get(slide_config.get("text"), color)),
                    "slideTitle": self._collect(safe_get(slide_config.get("slideTitle"), color)),
                    "blockTitle": self._collect(safe_get(slide_config.get("blockTitle"), color)),
                    "email": self._collect(safe_get(slide_config.get("email"), color)),
                    "date": self._collect(safe_get(slide_config.get("date"), color)),
                    "name": self._collect(safe_get(slide_config.get("name"), color)),
                    "percentage": self._collect(safe_get(slide_config.get("percentage"), color)),
                    "figure": self._collect(safe_get(slide_config.get("figure"), color)),
                    "icon": self._collect(safe_get(slide_config.get("icon"), color)),
                    "background": self._collect(safe_get(slide_config.get("background"), color)),
                    "subTitle": self._collect(safe_get(slide_config.get("subTitle"), color)),
                    "number": self._collect(safe_get(slide_config.get("number"), color)),
                    "logo": self._collect(safe_get(slide_config.get("logo"), color)),
                    "font": self._collect(safe_get(slide_config.get("font"), color), is_font=True),
                }
                palette_block_ids[color]["presentation_palette"] = palette_ids[color]
                palette_block_ids[color]["block_layout_config_id"] = values["id"]

                data.append(values)
                query = insert(block_layout_config_table).values(values)
                session.execute(query)

            session.commit()
            logger.info(f"BlockLayoutConfigManager: insert {len(data)} items.\n")
            return data, palette_block_ids

        return super().execute(logic, session)

    @staticmethod
    def _collect(list_info: list[dict[str, str]] | None, is_font=False) -> list[str] | None:
        if not list_info:
            return None
        fonts = set()
        colors = []
        for dict_info in list_info:
            if dict_info.get("fontFamily"):
                fonts.add(dict_info["fontFamily"])
            if dict_info.get("color"):
                colors.append(dict_info["color"])

        return sorted(list(fonts)) if is_font else colors


class BlockLayoutIndexConfigManager(BaseManager):
    """Interacts With The BlockLayoutIndexConfig Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutIndexConfig"

    def insert(self, block_layouts: list[dict]) -> tuple[list[dict], dict[str, str]]:
        """Insert an entry in BlockLayoutIndexConfig Table."""

        block_layout_index_config_table, session = self.open_session(self.table)

        def logic():
            data = []
            block_index_ids: dict[str, str] = {}

            for block_layout in block_layouts:
                block_layout_id = block_layout.get("id")
                block_layout_name = block_layout.get("name")
                block_layout_type = block_layout.get("sql_type")
                match = re.search(r"z-index\s*(\d+)", block_layout_name)
                if match:
                    block_layout_index = int(match.group(1))
                else:
                    block_layout_index = None

                index_font_id = 0

                if block_layout_type in ["table", "infographik", "image"]:
                    continue

                if block_layout_index is not None:
                    block_id_to_index_config_id: dict[str, list[str]] = {}
                    block_id_to_index_config_id[block_layout_id] = []

                    index_color_id = block_layout_index

                    values = {
                        "id": generate_uuid(),
                        "blockLayoutId": block_layout_id,
                        "indexColorId": index_color_id,
                        "indexFontId": index_font_id,
                    }
                    block_index_ids[block_layout_id] = values["id"]
                    data.append(values)

                    query = insert(block_layout_index_config_table).values(values)
                    session.execute(query)

            session.commit()
            logger.info(f"BlockLayoutIndexConfigManager: insert {len(data)} items.\n")
            return data, block_index_ids

        return super().execute(logic, session)


class SlideLayoutIndexConfigManager(BaseManager):
    """Interacts with the SlideLayoutIndexConfig Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutIndexConfig"

    def insert(self, block_layouts: list[dict], block_index_ids: dict[str, str], palette_block_ids: dict[str, dict[str, str]]) -> list[dict]:
        """Insert an entry in SlideLayoutIndexConfig Table."""

        slide_layout_index_config_table, session = self.open_session(self.table)

        def logic():
            data = []
            if not block_layouts:
                return data

            for id_info in palette_block_ids.values():

                presentation_palette_id = id_info["presentation_palette"]
                block_layout_config_id = id_info["block_layout_config_id"]

                for block_layout in block_layouts:
                    slide_layout_id = block_layout.get("slide_layout_id")
                    block_layout_id = block_layout.get("id")

                    block_layout_index_config_id = block_index_ids.get(block_layout_id)

                    if not block_layout_index_config_id:
                        continue

                    values = {
                        "id": generate_uuid(),
                        "presentationPaletteId": presentation_palette_id,
                        "configNumber": 0,
                        "slideLayoutId": slide_layout_id,
                        "blockLayoutIndexConfigId": block_layout_index_config_id,
                        "blockLayoutConfigId": block_layout_config_id,
                    }

                    data.append(values)
                    query = insert(slide_layout_index_config_table).values(values)
                    session.execute(query)

            session.commit()
            logger.info(f"SlideLayoutIndexConfigManager: insert {len(data)} items.\n")
            return data

        return super().execute(logic, session)


class BlockLayoutToDeleteManager(BaseManager):
    """Insert an entry in BlockLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayout"

    def get_block_layout_structure(self, block_layout_ids: list[str]) -> dict | None:
        """Получить полную структуру связей BlockLayout со всеми зависимыми таблицами.

        Args:
            block_layout_ids: Список ID блоков

        Returns:
            dict | None: Полная структура связей с ID или None, если не найдено
        """
        if not block_layout_ids:
            return None

        block_layout_table, session = self.open_session("BlockLayout")

        def logic():
            # 1. Проверяем существование BlockLayout
            query = select(block_layout_table).where(block_layout_table.c.id.in_(block_layout_ids))
            block_layouts = session.execute(query).fetchall()

            if not block_layouts:
                return None

            result = {
                "blockLayouts": [],
                "blockLayoutIndexConfigs": [],
                "slideLayoutIndexConfigs": [],
                "metadata": {
                    "extracted_at": datetime.now().isoformat(),
                    "block_layout_ids": block_layout_ids,
                    "total_blocks": len(block_layouts),
                },
            }

            # Сначала собираем данные по каждому блоку
            collected_block_index_config_ids: list[str] = []

            for bl in block_layouts:
                block_id = bl.id
                block_data = {
                    "blockLayout": block_id,
                    "blockLayoutDimensions": None,
                    "blockLayoutStyles": None,
                    "blockLayoutLimit": None,
                    "figures": [],
                    "precompiledImages": [],
                }

                # BlockLayoutDimensions (1:1)
                block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                dim_q = select(block_layout_dimensions_table.c.blockLayoutId).where(block_layout_dimensions_table.c.blockLayoutId == block_id)
                dim_r = session.execute(dim_q).fetchone()
                if dim_r:
                    block_data["blockLayoutDimensions"] = dim_r.blockLayoutId

                # BlockLayoutStyles (1:1)
                block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                style_q = select(block_layout_styles_table.c.blockLayoutId).where(block_layout_styles_table.c.blockLayoutId == block_id)
                style_r = session.execute(style_q).fetchone()
                if style_r:
                    block_data["blockLayoutStyles"] = style_r.blockLayoutId

                # BlockLayoutLimit (1:1)
                block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                limit_q = select(block_layout_limit_table.c.blockLayoutId).where(block_layout_limit_table.c.blockLayoutId == block_id)
                limit_r = session.execute(limit_q).fetchone()
                if limit_r:
                    block_data["blockLayoutLimit"] = limit_r.blockLayoutId

                # Figure (1:N)
                figure_table, _ = self.open_session("Figure")
                figs_q = select(figure_table.c.id).where(figure_table.c.blockLayoutId == block_id)
                figs = session.execute(figs_q).fetchall()
                block_data["figures"] = [r.id for r in figs]

                # PrecompiledImage (1:N)
                precompiled_image_table, _ = self.open_session("PrecompiledImage")
                imgs_q = select(precompiled_image_table.c.id).where(precompiled_image_table.c.blockLayoutId == block_id)
                imgs = session.execute(imgs_q).fetchall()
                block_data["precompiledImages"] = [r.id for r in imgs]

                # BlockLayoutIndexConfig (N:1 относительно BlockLayout)
                block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                blic_q = select(
                    block_layout_index_config_table.c.id,
                    block_layout_index_config_table.c.blockLayoutId,
                    block_layout_index_config_table.c.indexColorId,
                    block_layout_index_config_table.c.indexFontId,
                ).where(block_layout_index_config_table.c.blockLayoutId == block_id)
                blic_rows = session.execute(blic_q).fetchall()
                for row in blic_rows:
                    result["blockLayoutIndexConfigs"].append(
                        {
                            "id": row.id,
                            "blockLayoutId": row.blockLayoutId,
                            "indexColorId": row.indexColorId,
                            "indexFontId": row.indexFontId,
                        }
                    )
                    collected_block_index_config_ids.append(row.id)

                result["blockLayouts"].append(block_data)

            # SlideLayoutIndexConfig, связанные через blockLayoutIndexConfigId
            if collected_block_index_config_ids:
                slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
                slic_q = select(
                    slide_layout_index_config_table.c.id,
                    slide_layout_index_config_table.c.slideLayoutId,
                    slide_layout_index_config_table.c.presentationPaletteId,
                    slide_layout_index_config_table.c.blockLayoutIndexConfigId,
                    slide_layout_index_config_table.c.blockLayoutConfigId,
                ).where(slide_layout_index_config_table.c.blockLayoutIndexConfigId.in_(collected_block_index_config_ids))
                slic_rows = session.execute(slic_q).fetchall()
                for row in slic_rows:
                    result["slideLayoutIndexConfigs"].append(
                        {
                            "id": row.id,
                            "slideLayoutId": row.slideLayoutId,
                            "presentationPaletteId": row.presentationPaletteId,
                            "blockLayoutIndexConfigId": row.blockLayoutIndexConfigId,
                            "blockLayoutConfigId": row.blockLayoutConfigId,
                        }
                    )
            logger.info("Получил все связи по BlockLayout. Начался процесс удаления.")

            return result

        return super().execute(logic, session)

    def delete_block_layout_structure(self, block_layout_ids: list[str]) -> dict:
        """Удалить полную структуру BlockLayout со всеми связанными данными в правильном порядке.

        Порядок удаления:
        0. Обнуление parentLayoutId в UserBlockLayout (сохранение пользовательских данных)
        1. SlideLayoutIndexConfig (по blockLayoutIndexConfigId)
        2. BlockLayoutIndexConfig
        3. Figure
        4. PrecompiledImage
        5. BlockLayoutLimit
        6. BlockLayoutDimensions
        7. BlockLayoutStyles
        8. BlockLayout

        Args:
            block_layout_ids: Список ID блоков для удаления

        Returns:
            dict: Результат удаления
        """
        if not block_layout_ids:
            return {
                "success": False,
                "message": "Список ID блоков пуст",
                "deleted_blocks": [],
                "failed_blocks": [],
            }

        # Получаем структуру
        structure = self.get_block_layout_structure(block_layout_ids)
        if not structure:
            return {
                "success": False,
                "message": "Блоки не найдены",
                "deleted_blocks": [],
                "failed_blocks": block_layout_ids,
            }

        block_layout_table, session = self.open_session("BlockLayout")

        def logic():
            try:
                deleted_blocks: list[str] = []

                # 0. Обнуляем ссылки в пользовательских блоках (если такие есть)
                user_block_layout_table, _ = self.open_session("UserBlockLayout")
                try:
                    update_query = update(user_block_layout_table).where(user_block_layout_table.c.parentLayoutId.in_(block_layout_ids)).values(parentLayoutId=None)
                    session.execute(update_query)
                    logger.info("Обнулил parentLayoutId")
                except Exception:
                    # Таблицы может не существовать в некоторых окружениях — пропускаем молча
                    pass

                # 1. SlideLayoutIndexConfig
                if structure.get("slideLayoutIndexConfigs"):
                    slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
                    for config in structure["slideLayoutIndexConfigs"]:
                        del_q = delete(slide_layout_index_config_table).where(slide_layout_index_config_table.c.id == config["id"])
                        session.execute(del_q)
                logger.info("Удалил таблицу SlideLayoutIndexConfig")

                # 2. BlockLayoutIndexConfig
                if structure.get("blockLayoutIndexConfigs"):
                    block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                    for config in structure["blockLayoutIndexConfigs"]:
                        del_q = delete(block_layout_index_config_table).where(block_layout_index_config_table.c.id == config["id"])
                        session.execute(del_q)
                logger.info("Удалил таблицу BlockLayoutIndexConfig")

                # 3-8. По каждому блоку
                for block in structure["blockLayouts"]:
                    block_id = block["blockLayout"]

                    # 3. Figure
                    if block["figures"]:
                        figure_table, _ = self.open_session("Figure")
                        for figure_id in block["figures"]:
                            del_q = delete(figure_table).where(figure_table.c.id == figure_id)
                            session.execute(del_q)
                    logger.info("Удалил таблицу Figure")

                    # 4. PrecompiledImage
                    if block["precompiledImages"]:
                        precompiled_image_table, _ = self.open_session("PrecompiledImage")
                        for image_id in block["precompiledImages"]:
                            del_q = delete(precompiled_image_table).where(precompiled_image_table.c.id == image_id)
                            session.execute(del_q)
                    logger.info("Удалил таблицу PrecompiledImage")

                    # 5. BlockLayoutLimit
                    if block["blockLayoutLimit"]:
                        block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                        del_q = delete(block_layout_limit_table).where(block_layout_limit_table.c.blockLayoutId == block_id)
                        session.execute(del_q)
                    logger.info("Удалил таблицу BlockLayoutLimit")

                    # 6. BlockLayoutDimensions
                    if block["blockLayoutDimensions"]:
                        block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                        del_q = delete(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block_id)
                        session.execute(del_q)
                    logger.info("Удалил таблицу BlockLayoutDimensions")

                    # 7. BlockLayoutStyles
                    if block["blockLayoutStyles"]:
                        block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                        del_q = delete(block_layout_styles_table).where(block_layout_styles_table.c.blockLayoutId == block_id)
                        session.execute(del_q)
                    logger.info("Удалил таблицу BlockLayoutStyles")

                    # 8. Сам BlockLayout
                    del_q = delete(block_layout_table).where(block_layout_table.c.id == block_id)
                    session.execute(del_q)
                    deleted_blocks.append(block_id)
                    logger.info("Удалил таблицу BlockLayout")

                session.commit()

                return {
                    "success": True,
                    "message": f"Успешно удалено {len(deleted_blocks)} блоков",
                    "deleted_blocks": deleted_blocks,
                    "failed_blocks": [],
                    "total_requested": len(block_layout_ids),
                    "total_deleted": len(deleted_blocks),
                }

            except Exception as e:
                session.rollback()
                error_msg = f"Ошибка при удалении BlockLayout структуры: {e}"
                print(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "deleted_blocks": [],
                    "failed_blocks": block_layout_ids,
                    "total_requested": len(block_layout_ids),
                    "total_deleted": 0,
                }

        return super().execute(logic, session)

    def find_existing_block_layouts(self, presentation_layout_id: str) -> list[str]:

        # Find slide layout ids
        slide_layout_table, session = self.open_session("SlideLayout")
        query = select(slide_layout_table.c.id).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
        result = session.execute(query).fetchall()
        slide_layout_ids = [str(row[0]) for row in result]

        block_layout_ids = []

        # Find block layouts ids
        block_layout_table, session = self.open_session("BlockLayout")
        for slide_layout_id in slide_layout_ids:
            query = select(block_layout_table.c.id).where(block_layout_table.c.slideLayoutId == slide_layout_id)
            result = session.execute(query).fetchall()
            block_layout_ids.extend([str(row[0]) for row in result])

        return block_layout_ids
