import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import delete, func, insert, null, select, update
from sqlalchemy.engine.row import Row
from sqlalchemy.sql.elements import ColumnElement

from db_work import constants
from db_work.database import BaseManager
from db_work.utils import BlockLayoutUtils, SlideLayoutUtils, generate_uuid, get_slide_layout_data_from_cache
from log_utils import logs, setup_logger

logger = setup_logger(__name__)


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "PresentationLayout"

    def select_layout_by_name(self, name: str) -> Row | None:
        """Find a row in 'PresentationLayout' by name."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            query = select(presentation_layout_table).where(cast(ColumnElement[bool], presentation_layout_table.c.name == name))
            result = session.execute(query).fetchone()
            return result

        return super().execute(logic, session)

    def select_layout_by_uid(self, str_uid: str) -> Row | None:
        """Find a row in 'PresentationLayout' by uid."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            uid = uuid.UUID(str_uid)
            query = select(presentation_layout_table).where(cast(ColumnElement[bool], presentation_layout_table.c.id == uid))
            result = session.execute(query).fetchone()
            return result

        return super().execute(logic, session)

    def insert(self, name: str) -> str | None:
        """Insert New Layout."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "name": name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return uid

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

            return result

        return super().execute(logic, session)

    def save_presentation_layout_structure_to_file(self, presentation_layout_id: str, output_dir: str = "my_output") -> str | None:
        """Получить и сохранить структуру связей PresentationLayout в JSON файл.

        Args:
            presentation_layout_id: ID презентационного макета
            output_dir: Директория для сохранения файла

        Returns:
            str: Путь к созданному файлу или None в случае ошибки
        """
        data = self.get_presentation_layout_structure(presentation_layout_id)

        if not data:
            return None

        # Создаем директорию если её нет
        os.makedirs(output_dir, exist_ok=True)

        # Формируем имя файла
        filename = f"presentation_layout_structure_{presentation_layout_id[:8]}.json"
        filepath = os.path.join(output_dir, filename)

        # Сохраняем в файл
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return filepath
        except Exception as e:
            print(f"Ошибка при сохранении файла структуры: {e}")
            return None

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

                # 1. SlideConfigSequence (связаны с PresentationPalette)
                for palette in structure["presentationPalettes"]:
                    if palette["slideConfigSequences"]:
                        slide_config_sequence_table, _ = self.open_session("SlideConfigSequence")
                        for sequence_id in palette["slideConfigSequences"]:
                            delete_query = delete(slide_config_sequence_table).where(slide_config_sequence_table.c.id == sequence_id)
                            session.execute(delete_query)

                # 2. SlideLayoutIndexConfig (связующая N:N таблица)
                if structure["slideLayoutIndexConfigs"]:
                    slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
                    for config in structure["slideLayoutIndexConfigs"]:
                        delete_query = delete(slide_layout_index_config_table).where(slide_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)

                # 3. BlockLayoutIndexConfig
                if structure["blockLayoutIndexConfigs"]:
                    block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                    for config in structure["blockLayoutIndexConfigs"]:
                        delete_query = delete(block_layout_index_config_table).where(block_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)

                # 4. Figure (связаны с BlockLayout)
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["figures"]:
                            figure_table, _ = self.open_session("Figure")
                            for figure_id in block["figures"]:
                                delete_query = delete(figure_table).where(figure_table.c.id == figure_id)
                                session.execute(delete_query)

                # 5. PrecompiledImage (связаны с BlockLayout)
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["precompiledImages"]:
                            precompiled_image_table, _ = self.open_session("PrecompiledImage")
                            for image_id in block["precompiledImages"]:
                                delete_query = delete(precompiled_image_table).where(precompiled_image_table.c.id == image_id)
                                session.execute(delete_query)

                # 6. BlockLayoutLimit
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutLimit"]:
                            block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                            delete_query = delete(block_layout_limit_table).where(block_layout_limit_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)

                # 7. BlockLayoutDimensions
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutDimensions"]:
                            block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                            delete_query = delete(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)

                # 8. BlockLayoutStyles
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutStyles"]:
                            block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                            delete_query = delete(block_layout_styles_table).where(block_layout_styles_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)

                # 9. BlockLayout
                for slide in structure["slideLayouts"]:
                    for block in slide["blockLayouts"]:
                        block_layout_table, _ = self.open_session("BlockLayout")
                        delete_query = delete(block_layout_table).where(block_layout_table.c.id == block["id"])
                        session.execute(delete_query)

                # 11. SlideLayoutDimensions
                for slide in structure["slideLayouts"]:
                    if slide["slideLayoutDimensions"]:
                        slide_layout_dimensions_table, _ = self.open_session("SlideLayoutDimensions")
                        delete_query = delete(slide_layout_dimensions_table).where(slide_layout_dimensions_table.c.slideLayoutId == slide["id"])
                        session.execute(delete_query)

                # 12. SlideLayoutStyles
                for slide in structure["slideLayouts"]:
                    if slide["slideLayoutStyles"]:
                        slide_layout_styles_table, _ = self.open_session("SlideLayoutStyles")
                        delete_query = delete(slide_layout_styles_table).where(slide_layout_styles_table.c.slideLayoutId == slide["id"])
                        session.execute(delete_query)

                # 13. SlideLayoutAdditionalInfo
                for slide in structure["slideLayouts"]:
                    if slide["slideLayoutAdditionalInfo"]:
                        slide_layout_additional_info_table, _ = self.open_session("SlideLayoutAdditionalInfo")
                        delete_query = delete(slide_layout_additional_info_table).where(slide_layout_additional_info_table.c.slideLayoutId == slide["id"])
                        session.execute(delete_query)

                # 14. SlideLayout
                for slide in structure["slideLayouts"]:
                    slide_layout_table, _ = self.open_session("SlideLayout")
                    delete_query = delete(slide_layout_table).where(slide_layout_table.c.id == slide["id"])
                    session.execute(delete_query)

                # 15. PresentationPalette
                for palette in structure["presentationPalettes"]:
                    presentation_palette_table, _ = self.open_session("PresentationPalette")
                    delete_query = delete(presentation_palette_table).where(presentation_palette_table.c.id == palette["id"])
                    session.execute(delete_query)

                # 16. BlockLayoutConfig
                if structure["blockLayoutConfigs"]:
                    block_layout_config_table, _ = self.open_session("BlockLayoutConfig")
                    for config_id in structure["blockLayoutConfigs"]:
                        delete_query = delete(block_layout_config_table).where(block_layout_config_table.c.id == config_id)
                        session.execute(delete_query)

                # 17. FontStyleConfiguration
                if structure["fontStyleConfigurations"]:
                    font_style_configuration_table, _ = self.open_session("FontStyleConfiguration")
                    for config_id in structure["fontStyleConfigurations"]:
                        delete_query = delete(font_style_configuration_table).where(font_style_configuration_table.c.id == config_id)
                        session.execute(delete_query)

                # 18. PresentationLayoutColor
                if structure["presentationLayoutColors"]:
                    presentation_layout_color_table, _ = self.open_session("PresentationLayoutColor")
                    for color_id in structure["presentationLayoutColors"]:
                        delete_query = delete(presentation_layout_color_table).where(presentation_layout_color_table.c.id == color_id)
                        session.execute(delete_query)

                # 19. LayoutRoles
                if structure["layoutRoles"] > 0:
                    layout_roles_table, _ = self.open_session("LayoutRoles")
                    delete_query = delete(layout_roles_table).where(layout_roles_table.c.presentationLayoutId == presentation_layout_id)
                    session.execute(delete_query)

                # 20. PresentationLayoutStyles
                if structure["presentationLayoutStyles"]:
                    presentation_layout_styles_table, _ = self.open_session("PresentationLayoutStyles")
                    delete_query = delete(presentation_layout_styles_table).where(presentation_layout_styles_table.c.id == structure["presentationLayoutStyles"])
                    session.execute(delete_query)

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

                # 22. Наконец, удаляем сам PresentationLayout
                delete_query = delete(presentation_layout_table).where(presentation_layout_table.c.id == presentation_layout_id)
                session.execute(delete_query)

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
    def __init__(self):
        super().__init__()
        self.table = "PresentationPalette"

    def insert(self):
        presentation_palette_table, session = self.open_session(self.table)

        def logic():
            return None

        return super().execute(logic, session)


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()
        self.table = "ColorSettings"

    def insert(self) -> str | None:
        """Insert new color id."""

        color_settings_table, session = self.open_session(self.table)

        def logic():
            new_color_id = generate_uuid()
            values = {"id": new_color_id, "count": 1, "lightenStep": 0.3, "darkenStep": 0.3, "saturationAdjust": 0.3}
            query = insert(color_settings_table).values(values)
            session.execute(query)
            session.commit()

            return new_color_id if new_color_id else None

        return super().execute(logic, session)


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()
        self.table = "PresentationLayoutStyles"

    def insert(self, presentation_layout_id: str | None, color_settings_id: str | None) -> str | None:
        """Inserts ColorSettingsID and PresentationLayoutID into PresentationLayoutStyles."""

        presentation_layout_styles_table, session = self.open_session(self.table)

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "colorSettingsId": color_settings_id, "presentationLayoutId": presentation_layout_id}
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        return super().execute(logic, session)


class LayoutRolesManager(BaseManager):
    """Interacts With The LayoutRoles Table."""

    def __init__(self):
        super().__init__()
        self.table = "LayoutRoles"

    def insert(self, presentation_layout_id: str | None, user_role: str) -> tuple[str] | None:
        """Insert a field in LayoutRoles Table."""

        layout_roles_table, session = self.open_session(self.table)

        def logic():
            values = {"presentationLayoutId": presentation_layout_id, "role": user_role.upper()}
            query = insert(layout_roles_table).values(values)
            session.execute(query)
            session.commit()
            return presentation_layout_id, user_role

        return super().execute(logic, session)


@logs(logger, on=True)
class SlideLayoutManager(BaseManager):
    """Interacts With The SlideLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayout"

    @logs(logger, on=True)
    def insert_or_update(self, presentation_layout_id: str | None) -> list[dict[Any, Any]]:
        """Create or update fields in SlideLayout table."""

        slide_layout_table, session = self.open_session(self.table)
        data = []
        value_id = None
        updated_slide_layouts = 0
        added_slide_layouts = 0

        def logic():
            nonlocal data
            nonlocal value_id
            nonlocal updated_slide_layouts
            nonlocal added_slide_layouts

            query = select(slide_layout_table).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            postgres_data = session.execute(query).fetchall()
            values = get_slide_layout_data_from_cache(presentation_layout_id)

            for value in values:
                value_for_slide_layout = value
                keys_to_remove = ("dimensions", "blocks", "slide_type", "columns", "presentationPaletteColors")
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

                # Удаляем в правильном порядке согласно зависимостям внешних ключей

                # 1. SlideLayoutIndexConfig (связующая таблица)
                if structure["slideLayoutIndexConfigs"]:
                    slide_layout_index_config_table, _ = self.open_session("SlideLayoutIndexConfig")
                    for config in structure["slideLayoutIndexConfigs"]:
                        delete_query = delete(slide_layout_index_config_table).where(slide_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)

                # 2. BlockLayoutIndexConfig
                if structure["blockLayoutIndexConfigs"]:
                    block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                    for config in structure["blockLayoutIndexConfigs"]:
                        delete_query = delete(block_layout_index_config_table).where(block_layout_index_config_table.c.id == config["id"])
                        session.execute(delete_query)

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

                    # 4. PrecompiledImage (связаны с BlockLayout)
                    for block in slide["blockLayouts"]:
                        if block["precompiledImages"]:
                            precompiled_image_table, _ = self.open_session("PrecompiledImage")
                            for image_id in block["precompiledImages"]:
                                delete_query = delete(precompiled_image_table).where(precompiled_image_table.c.id == image_id)
                                session.execute(delete_query)

                    # 5. BlockLayoutLimit
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutLimit"]:
                            block_layout_limit_table, _ = self.open_session("BlockLayoutLimit")
                            delete_query = delete(block_layout_limit_table).where(block_layout_limit_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)

                    # 6. BlockLayoutDimensions
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutDimensions"]:
                            block_layout_dimensions_table, _ = self.open_session("BlockLayoutDimensions")
                            delete_query = delete(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)

                    # 7. BlockLayoutStyles
                    for block in slide["blockLayouts"]:
                        if block["blockLayoutStyles"]:
                            block_layout_styles_table, _ = self.open_session("BlockLayoutStyles")
                            delete_query = delete(block_layout_styles_table).where(block_layout_styles_table.c.blockLayoutId == block["id"])
                            session.execute(delete_query)

                    # 8. BlockLayout
                    for block in slide["blockLayouts"]:
                        block_layout_table, _ = self.open_session("BlockLayout")
                        delete_query = delete(block_layout_table).where(block_layout_table.c.id == block["id"])
                        session.execute(delete_query)

                    # 9. SlideLayoutDimensions
                    if slide["slideLayoutDimensions"]:
                        slide_layout_dimensions_table, _ = self.open_session("SlideLayoutDimensions")
                        delete_query = delete(slide_layout_dimensions_table).where(slide_layout_dimensions_table.c.slideLayoutId == slide_layout_id)
                        session.execute(delete_query)

                    # 10. SlideLayoutStyles
                    if slide["slideLayoutStyles"]:
                        slide_layout_styles_table, _ = self.open_session("SlideLayoutStyles")
                        delete_query = delete(slide_layout_styles_table).where(slide_layout_styles_table.c.slideLayoutId == slide_layout_id)
                        session.execute(delete_query)

                    # 11. SlideLayoutAdditionalInfo
                    if slide["slideLayoutAdditionalInfo"]:
                        slide_layout_additional_info_table, _ = self.open_session("SlideLayoutAdditionalInfo")
                        delete_query = delete(slide_layout_additional_info_table).where(slide_layout_additional_info_table.c.slideLayoutId == slide_layout_id)
                        session.execute(delete_query)

                    # 12. Удаляем сам SlideLayout
                    delete_query = delete(slide_layout_table).where(slide_layout_table.c.id == slide_layout_id)
                    session.execute(delete_query)

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

        added_data = []

        def logic():
            nonlocal added_data

            for item in slide_layouts:
                existing_query = select(slide_layout_styles_table.c.slideLayoutId).where(slide_layout_styles_table.c.slideLayoutId == item.get("id"))
                result = session.execute(existing_query).scalar_one_or_none()

                if not result:
                    values = {"slideLayoutId": item.get("id")}
                    added_data.append(values)

                    query = insert(slide_layout_styles_table).values(values)
                    session.execute(query)

            session.commit()
            logger.info(f"SlideLayoutStylesManager: insert {len(added_data)} items. \n")
            return added_data

        return super().execute(logic, session)


class SlideLayoutAdditionalInfoManager(BaseManager):
    """Insert or update data in SlideLayoutAdditionalInfo Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutAdditionalInfo"

    def insert_or_update(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert a field in SlideLayoutAdditionalInfo Table."""

        slide_layout_additional_info, session = self.open_session(self.table)

        added_data = []
        updated_items = 0
        added_items = 0

        def logic():
            nonlocal added_data
            nonlocal updated_items
            nonlocal added_items

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
                        added_data.append(values)
                        added_items += 1

                    else:
                        existing_values = dict(result._mapping)
                        should_update = any(existing_values[key] != value for key, value in values.items())

                        if should_update:
                            update_query = update(slide_layout_additional_info).where(slide_layout_additional_info.c.slideLayoutId == slide_layout_id).values(**values)
                            session.execute(update_query)
                            added_data.append(values)
                            updated_items += 1

                session.commit()

            logger.info(f"SlideLayoutAdditionalInfoManager: insert {added_items} items.")
            logger.info(f"SlideLayoutAdditionalInfoManager: update {updated_items} items.\n")

            return added_data

        return super().execute(logic, session)


class SlideLayoutDimensionsManager(BaseManager):
    """Insert a field in SlideLayoutDimensions Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutDimensions"

    def insert_or_update(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert a field in SlideLayoutDimensions Table."""

        slide_layout_dimensions, session = self.open_session(self.table)

        added_data = []
        updated_items = 0
        added_items = 0

        def logic():
            nonlocal added_data
            nonlocal updated_items
            nonlocal added_items

            for item in slide_layouts:

                dimensions = item.get("dimensions")
                slide_layout_id = item.get("id")

                values = {"slideLayoutId": item.get("id"), "x": 0, "y": 0, "w": dimensions.get("w"), "h": dimensions.get("h")}

                existing_query = select(slide_layout_dimensions).where(slide_layout_dimensions.c.slideLayoutId == slide_layout_id)
                result = session.execute(existing_query).one_or_none()

                if result is None:
                    added_data.append(values)
                    query = insert(slide_layout_dimensions).values(values)
                    session.execute(query)
                    added_items += 1

                else:
                    existing_values = dict(result._mapping)
                    should_update = any(existing_values[key] != value for key, value in values.items())

                    if should_update:
                        update_query = update(slide_layout_dimensions).where(slide_layout_dimensions.c.slideLayoutId == slide_layout_id).values(**values)
                        session.execute(update_query)
                        added_data.append(values)
                        updated_items += 1

            session.commit()

            logger.info(f"SlideLayoutDimensionsManager: insert {added_items} items.")
            logger.info(f"SlideLayoutDimensionsManager: update {updated_items} items.\n")

            return added_data

        return super().execute(logic, session)


class BlockLayoutManager(BaseManager):
    """Insert a entry in BlockLayoutManager Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayout"

    def insert(self, slide_layouts: list[dict]) -> list[dict]:
        """Insert a field in BlockLayout Table."""

        block_layout_table, session = self.open_session(self.table)

        data = []
        added_items = 0
        updated_items = 0
        values = {}

        def logic():
            nonlocal data
            nonlocal added_items
            nonlocal updated_items
            nonlocal values

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
                    data.append(values)

            session.commit()

            logger.info(f"BlockLayoutManager: insert {added_items} items.")
            logger.info(f"BlockLayoutManager: update {updated_items} items.\n")

            return data

        return super().execute(logic, session)


class BlockLayoutDimensionsManagers(BaseManager):
    """Insert a field in BlockLayoutDimensionsManagers Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutDimensions"

    def insert_or_update(self, block_layouts: list[dict]) -> list[dict]:
        """Insert or update an entry in BlockLayoutDimensions Table."""

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

                existing_query = select(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block_layout_id)
                result = session.execute(existing_query).one_or_none()

                if result is None:
                    query = insert(block_layout_dimensions_table).values(values)
                    session.execute(query)
                    added_items += 1

                else:
                    existing_values = dict(result._mapping)
                    should_update = any(existing_values[key] != value for key, value in values.items())

                    if should_update:
                        update_query = update(block_layout_dimensions_table).where(block_layout_dimensions_table.c.blockLayoutId == block_layout_id).values(**values)
                        session.execute(update_query)
                        updated_items += 1

            logger.info(f"BlockLayoutDimensionsManagers: insert {added_items} items.")
            logger.info(f"BlockLayoutDimensionsManagers: update {updated_items} items.\n")

            data.append(values)
            session.commit()
            return data

        return super().execute(logic, session)


class PrecompiledImageManager(BaseManager):
    """Insert a row in PrecompiledImage Table."""

    # Возможно сюда нужно будет добавить логику на update

    def __init__(self):
        super().__init__()
        self.table = "PrecompiledImage"

    def insert(self, block_layouts: list[dict], **tg_params: dict[str, str]) -> list[dict]:
        """Insert a row in PrecompiledImage Table."""

        precompiled_image_table, session = self.open_session(self.table)

        def logic():
            added_data = []

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

                        added_data.append(values)
                        query = insert(precompiled_image_table).values(values)
                        session.execute(query)

            session.commit()
            return added_data

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

        return f"{base_url}{path}/layouts/{layout_name}/{block_name}_{color[1:]}.{ext}"


class BlockLayoutStylesManagers(BaseManager):
    """Insert a field in BlockLayoutStyles Table."""

    # Возможно сюда нужно будет добвать логику на update

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutStyles"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert a field in BlockLayoutStyles Table."""

        block_layout_styles_table, session = self.open_session(self.table)

        added_data = []
        values = {}

        def logic():
            nonlocal added_data
            nonlocal values

            default_color = constants.DEFAULT_COLOR
            color_settings_id = constants.DEFAULT_COLOR_SETTINGS_ID

            for block_layout in block_layouts:
                block_layout_styles = block_layout.get("styles")
                border_radius = block_layout_styles.get("borderRadius")

                weight = block_layout_styles.get("weight")
                weight = block_layout_styles.get("weight")
                weight = float(weight) if isinstance(weight, str) and weight.isdigit() else None
                weight = null() if weight is None else weight

                # color_value = block.styles.get("color")
                # color_value = ColorUtils.normalize_color(color_value) if color_value else None
                # if not color_value or not color_value.startswith("#") or len(color_value) not in (4, 7):
                color_value = default_color

                # if block.needs_null_styles:

                values = {
                    "blockLayoutId": block_layout.get("id"),
                    "textVertical": block_layout_styles.get("textVertical"),
                    "textHorizontal": block_layout_styles.get("textHorizontal"),
                    "fontSize": block_layout_styles.get("fontSize"),
                    "weight": weight,
                    "zIndex": block_layout_styles.get("zIndex"),
                    "opacity": block_layout_styles.get("opacity"),
                    "textTransform": block_layout_styles.get("textTransform"),
                    "borderRadius": border_radius,
                    "colorSettingsId": color_settings_id,
                    "color": color_value,
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

                added_data.append(values)
                query = insert(block_layout_styles_table).values(values)
                session.execute(query)

            session.commit()
            return added_data

        return super().execute(logic, session)


class BlockLayoutLimitManagers(BaseManager):
    """Insert an entry in BlockLayoutLimit Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutLimit"
        self.block_layout_min_words = constants.BLOCK_TYPE_MIN_WORDS

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayoutLimit Table."""

        block_layout_limit_table, session = self.open_session(self.table)

        added_data = []

        def logic():
            nonlocal added_data

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
                added_data.append(values)

            session.commit()
            return added_data

        return super().execute(logic, session)


class BlockLayoutFigureManagers(BaseManager):
    """Insert an entry in Figure Table."""

    def __init__(self):
        super().__init__()
        self.table = "Figure"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert a field in BlockLayoutDimensions Table."""

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
            return data

        return super().execute(logic, session)


class BlockLayoutConfigManager(BaseManager):
    """Insert a row in BlockLayoutConfig Table."""

    # Возможно сюда нужно будет добавить логику на update

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutConfig"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert a row in BlockLayoutConfig Table."""

        block_layout_config_table, session = self.open_session(self.table)

        def logic():
            def safe_get(d: dict, key: str):
                return d.get(key, None) if d else None

            added_data = []
            if not block_layouts:
                return added_data

            slide_config: dict[str, dict[str, list[dict[str, str]]]] = block_layouts[0].get("slide_config", {})
            presentation_palette = block_layouts[0].get("presentation_palette", [])
            if not slide_config or not presentation_palette:
                return added_data

            for color in presentation_palette:
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

                added_data.append(values)
                query = insert(block_layout_config_table).values(values)
                session.execute(query)

            session.commit()
            return added_data

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


class BlockLayoutIndexConfigManagers(BaseManager):
    """Insert an entry in BlockLayoutIndexConfig Table."""

    def __init__(self):
        super().__init__()
        self.table = "BlockLayoutIndexConfig"

    def insert(self, block_layouts: list[dict]) -> list[dict]:
        """Insert an entry in BlockLayoutIndexConfig Table."""

        block_layout_index_config_table, session = self.open_session(self.table)

        data = []

        def logic():
            nonlocal data

            for block_layout in block_layouts:
                block_layout_id = block_layout.get("id")
                block_layout_name = block_layout.get("name")
                block_layout_type = block_layout.get("sql_type")
                # print(block_layout_name)
                # block_layout_index = BlockLayoutUtils().extract_index(name=block_layout_name, block_type=block_layout_type) # 1302
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
                query = insert(block_layout_index_config_table).values(values)
                session.execute(query)

                data.append(values)

            session.commit()
            return data

        return super().execute(logic, session)


# poetry run python -m db_work.services

# if __name__ == "__main__":


# pattern
# class BlockLayoutDimensionsManagers(BaseManager):
#     """Insert a field in BlockLayoutDimensionsManagers Table."""

#     # Возможно сюда нужно будет добавить логику на update

#     def __init__(self):
#         super().__init__()
#         self.table = "BlockLayoutDimensions"

#     def insert(self, slide_layouts: list[dict]) -> list[dict]:
#         """Insert a field in BlockLayoutDimensions Table."""

#         block_layout_dimensions_table, session = self.open_session(self.table)

#         added_data = []

#         def logic():
#             nonlocal added_data

#             return added_data

#         return super().execute(logic, session)
