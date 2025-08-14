import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine.row import Row

from db_work.database import BaseManager
from db_work.utils import generate_uuid, get_slide_layout_data_from_cache


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "PresentationLayout"

    def select_layout_by_name(self, name: str) -> Row | None:
        """Find a row in 'PresentationLayout' by name."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():

            query = select(presentation_layout_table).where(presentation_layout_table.c.name == name)
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

    def get_all_presentation_layout_names(self) -> list[str] | None:
        """Get all presentation layout names from the database."""

        presentation_layout_table, session = self.open_session(self.table)

        def logic():
            query = session.query(presentation_layout_table.c.name).all()
            return [row[0] for row in query]

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
            query = select(presentation_layout_table).where(presentation_layout_table.c.id == presentation_layout_id)
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
                "blockLayoutConfigs": [],
                "metadata": {"extracted_at": datetime.now().isoformat(), "presentation_layout_id": presentation_layout_id},
            }

            # Собираем все ColorSettings ID и BlockLayoutConfig ID для избежания дублирования
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
                    block_data = {"id": block_layout_id, "blockLayoutDimensions": None, "blockLayoutStyles": None, "blockLayoutLimit": None, "figures": [], "precompiledImages": [], "blockLayoutIndexConfigs": []}

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

                    # 2.4.6. BlockLayoutIndexConfig (1:N)
                    block_layout_index_config_table, _ = self.open_session("BlockLayoutIndexConfig")
                    block_index_configs_query = select(block_layout_index_config_table.c.id).where(block_layout_index_config_table.c.blockLayoutId == block_layout_id)
                    block_index_configs = session.execute(block_index_configs_query).fetchall()
                    block_data["blockLayoutIndexConfigs"] = [config.id for config in block_index_configs]

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

            # 9. BlockLayoutConfig - получаем все уникальные конфигурации блоков
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


class SlideLayoutManager(BaseManager):
    """Interacts With The SlideLayout Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayout"

    def insert_or_update(self, presentation_layout_id: str | None) -> list[dict[Any, Any]]:
        """Create or update fieds in SliedeLayout table."""

        slide_layout_table, session = self.open_session(self.table)
        added_slides = []
        updated_slides = []

        def logic():
            nonlocal added_slides, updated_slides

            query = select(slide_layout_table).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            result = session.execute(query)
            postgres_data = result.fetchall()

            cached_data = get_slide_layout_data_from_cache(presentation_layout_id)

            for data_item in cached_data:
                slide_dimension = data_item.pop("dimensions")
                slide_blocks = data_item.pop("blocks")
                uuid_data_item = {k: v if k != "id" else generate_uuid() for k, v in data_item.items()}

                matching_row = [row for row in postgres_data if row.name == uuid_data_item["name"] and row.number == uuid_data_item["number"]]

                if len(matching_row) > 0:
                    compared_row = matching_row[0]
                    keys_to_compare = ["number", "imagesCount", "maxTokensPerBlock", "maxWordsPerSentence", "minWordsPerSentence", "sentences", "isLast", "forGeneration", "presentationLayoutIndexColor"]
                    need_update = False

                    for key in keys_to_compare:
                        if getattr(compared_row, key) != uuid_data_item[key]:
                            need_update = True
                            break

                    if need_update:
                        stmt = update(slide_layout_table).where(slide_layout_table.c.id == compared_row.id).values(**uuid_data_item)
                        session.execute(stmt)
                        session.commit()
                        updated_slides.append((compared_row.name, compared_row.id, slide_dimension, slide_blocks))

                else:
                    new_entry = dict(uuid_data_item)
                    new_entry["id"] = generate_uuid()
                    stmt = insert(slide_layout_table).values(**new_entry)
                    session.execute(stmt)
                    session.commit()
                    added_slides.append((new_entry["name"], new_entry["id"], slide_dimension, slide_blocks))

            updated_query = select(slide_layout_table).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            session.execute(updated_query)

            changes = []
            for name, id_, slide_dimension, slide_blocks in added_slides + updated_slides:
                action = "Added" if (name, id_) in added_slides else "Updated"
                # changes.append(f"{action}: {name} {id_}")
                changes.append({"Action": action, "Name": name, "id": id_, "slide_dimension": slide_dimension, "slide_blocks": slide_blocks})
            return changes

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
            values = {"presentationLayoutId": presentation_layout_id, "role": user_role.upper()}
            query = insert(layout_roles_table).values(values)
            session.execute(query)
            session.commit()
            return presentation_layout_id, user_role

        return super().execute(logic, session)


class SlideLayoutStylesManager(BaseManager):
    """Interacts With The SlideLayoutStyles Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutStyles"

    def insert(self, slide_layouts: list[dict]):
        """Insert a field in SlideLayoutStyles Table."""

        # Возможно сюда нужно будет добвать логику на update
        slide_layout_styles_table, session = self.open_session(self.table)

        def logic():
            for item in slide_layouts:
                values = {"slideLayoutId": item.get("id")}

                query = insert(slide_layout_styles_table).values(values)
                session.execute(query)

            session.commit()
            return None

        return super().execute(logic, session)


class SlideLayoutAdditionalInfoManager(BaseManager):
    """Insert a field in SlideLayoutAdditionalInfo Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutAdditionalInfo"

    def insert(self):
        """Insert a field in SlideLayoutAdditionalInfo Table."""

        slide_layout_additional_info, session = self.open_session(self.table)

        def logic():

            # hasHeaders = true, если на слайде есть как минимум 1 blockTitle
            # percentes - считается по количеству блоков с типом percentag

            # type - figma
            # iconUrl - посмотреть в конфиге base path спросить у пользователя
            # infographicsType -

            # maxSymbolsInBlock - default
            # contentType - default

            # values = {
            #     "slideLayoutId": None,
            #     "percentesCount": None,
            #     "hasHeaders": None,
            #     "maxSymbolsInBlock": None,
            #     "type": None,
            #     "iconUrl": None,
            #     "infographicsType": None,
            #     "contentType": None,
            # }
            return ...

        return super().execute(logic, session)


class SlideLayoutDimensionsManager(BaseManager):
    """Insert a field in SlideLayoutDimensions Table."""

    def __init__(self):
        super().__init__()
        self.table = "SlideLayoutDimensions"

    def insert(self, slide_layouts: list[dict]):
        """Insert a field in SlideLayoutDimensions Table."""

        slide_layout_dimensions, session = self.open_session(self.table)

        def logic():
            for item in slide_layouts:
                dimensions = item.get("slide_dimension")
                values = {"slideLayoutId": item.get("id"), "x": 0, "y": 0, "w": dimensions.get("w"), "h": dimensions.get("h")}
                query = insert(slide_layout_dimensions).values(values)
                session.execute(query)

            session.commit()
            return None

        return super().execute(logic, session)


# poetry run python -m db_work.services

# if __name__ == "__main__":
