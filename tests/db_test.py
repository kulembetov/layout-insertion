from unittest.mock import Mock, call, patch

import pytest
from sqlalchemy.engine.row import Row

from db_work.services import ColorSettingsManager, LayoutRolesManager, PresentationLayoutManager, PresentationLayoutStylesManager, PresentationPaletteManager, SlideLayoutManager
from db_work.utils import generate_uuid


class TestPresentationLayoutManager:

    @pytest.fixture
    def manager(self):
        """Фикстура для создания экземпляра менеджера."""
        return PresentationLayoutManager()

    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии."""
        return Mock()

    @pytest.fixture
    def mock_table(self):
        """Фикстура для мока таблицы."""
        mock_table = Mock()
        mock_table.c = Mock()
        mock_table.c.name = Mock()
        return mock_table

    def test_init(self, manager):
        """Тест инициализации менеджера."""
        assert manager.table == "PresentationLayout"

    @patch("db_work.services.logger")
    @patch("db_work.services.select")
    @patch("db_work.services.cast")
    def test_select_layout_by_name_found(self, mock_cast, mock_select, mock_logger, manager, mock_session, mock_table):
        """Тест поиска существующего layout по имени."""

        test_name = "test_layout"
        mock_row = Mock(spec=Row)

        manager.open_session = Mock(return_value=(mock_table, mock_session))
        Mock()
        mock_session.execute.return_value.fetchone.return_value = mock_row

        result = manager.select_layout_by_name(test_name)

        manager.open_session.assert_called_once_with("PresentationLayout")
        mock_session.execute.assert_called_once()
        mock_logger.info.assert_called()
        assert result == mock_row

    @patch("db_work.services.select")
    @patch("db_work.services.cast")
    @patch("db_work.services.logger")
    def test_select_layout_by_uid_found(self, mock_logger, mock_cast, mock_select, manager, mock_session, mock_table):
        """Тест поиска существующего layout по id."""

        test_name = generate_uuid()
        mock_row = Mock(spec=Row)

        manager.open_session = Mock(return_value=(mock_table, mock_session))
        Mock()
        mock_session.execute.return_value.fetchone.return_value = mock_row

        result = manager.select_layout_by_name(test_name)

        manager.open_session.assert_called_once_with("PresentationLayout")
        mock_session.execute.assert_called_once()
        mock_logger.info.assert_called()
        assert result == mock_row

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_layout_success(self, mock_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест успешной вставки нового layout."""

        test_name = "Test Layout"
        test_uid = generate_uuid()

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(test_name)

        manager.open_session.assert_called_once_with("PresentationLayout")

        mock_generate_uuid.assert_called_once()

        mock_sql_insert.assert_called_once_with(mock_table)

        expected_values = {"id": test_uid, "name": test_name}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)

        mock_session.commit.assert_called_once()

        mock_logger.info.assert_called_once_with(f"PresentationLayoutManager: insert new presentation layout - {test_name}.\n")

        assert result == test_uid

    @patch("db_work.services.logger")
    def test_get_presentation_layout_ids_names_success(self, mock_logger, manager, mock_session, mock_table):
        """Тест успешного получения всех layout из базы данных."""

        mock_row1 = Mock()
        mock_row1.id = "uuid1"
        mock_row1.name = "Layout 1"

        mock_row2 = Mock()
        mock_row2.id = "uuid2"
        mock_row2.name = "Layout 2"

        mock_row3 = Mock()
        mock_row3.id = "uuid3"
        mock_row3.name = "Layout 3"

        mock_rows = [mock_row1, mock_row2, mock_row3]

        manager.open_session = Mock(return_value=(mock_table, mock_session))
        mock_session.query.return_value.all.return_value = mock_rows

        result = manager.get_presentation_layout_ids_names()

        manager.open_session.assert_called_once_with("PresentationLayout")
        mock_session.query.assert_called_once_with(mock_table.c)
        mock_session.query.return_value.all.assert_called_once()

        expected_result = [("uuid1", "Layout 1"), ("uuid2", "Layout 2"), ("uuid3", "Layout 3")]
        assert result == expected_result


class TestPresentationPaletteManager:

    @pytest.fixture
    def manager(self):
        """Фикстура для создания экземпляра менеджера."""
        return PresentationPaletteManager()

    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии."""
        return Mock()

    @pytest.fixture
    def mock_table(self):
        """Фикстура для мока таблицы."""
        mock_table = Mock()
        mock_table.c = Mock()
        mock_table.c.name = Mock()
        return mock_table

    def test_init(self, manager):
        """Тест инициализации менеджера."""
        assert manager.table == "PresentationPalette"

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_palette_success(self, mock_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест успешной вставки палитры с данными."""

        slides_layouts = [{"presentationPaletteColors": ["#FF0000", "#00FF00", "#0000FF"]}]
        layout_id = "test-layout-id"

        mock_generate_uuid.side_effect = ["uuid1", "uuid2", "uuid3"]

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result_data, result_palette_ids = manager.insert(slides_layouts, layout_id)

        manager.open_session.assert_called_once_with("PresentationPalette")
        assert mock_generate_uuid.call_count == 3

        assert mock_sql_insert.call_count == 3
        mock_sql_insert.assert_called_with(mock_table)

        expected_calls = [call().values({"id": "uuid1", "presentationLayoutId": layout_id, "color": "#FF0000"}), call().values({"id": "uuid2", "presentationLayoutId": layout_id, "color": "#00FF00"}), call().values({"id": "uuid3", "presentationLayoutId": layout_id, "color": "#0000FF"})]
        mock_insert_query.values.assert_has_calls(expected_calls, any_order=False)

        assert mock_session.execute.call_count == 3
        mock_session.commit.assert_called_once()

        mock_logger.info.assert_called_once_with("PresentationPaletteManager: insert 3 items.\n")

        expected_data = [{"id": "uuid1", "presentationLayoutId": layout_id, "color": "#FF0000"}, {"id": "uuid2", "presentationLayoutId": layout_id, "color": "#00FF00"}, {"id": "uuid3", "presentationLayoutId": layout_id, "color": "#0000FF"}]
        expected_palette_ids = {"#FF0000": "uuid1", "#00FF00": "uuid2", "#0000FF": "uuid3"}
        assert result_data == expected_data
        assert result_palette_ids == expected_palette_ids

    @patch("db_work.services.logger")
    def test_insert_palette_empty_slides_layouts(self, mock_logger, manager, mock_session, mock_table):
        """Тест вставки с пустым slides_layouts."""

        slides_layouts = []
        layout_id = "test-layout-id"

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        result_data, result_palette_ids = manager.insert(slides_layouts, layout_id)

        manager.open_session.assert_called_once_with("PresentationPalette")

        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()
        mock_logger.info.assert_not_called()

        assert result_data == []
        assert result_palette_ids == {}

    @patch("db_work.services.logger")
    def test_insert_palette_empty_colors(self, mock_logger, manager, mock_session, mock_table):
        """Тест вставки с пустыми presentationPaletteColors."""

        slides_layouts = [{"presentationPaletteColors": []}]
        layout_id = "test-layout-id"

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        result_data, result_palette_ids = manager.insert(slides_layouts, layout_id)

        manager.open_session.assert_called_once_with("PresentationPalette")

        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()
        mock_logger.info.assert_not_called()

        assert result_data == []
        assert result_palette_ids == {}

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.database.logger")
    def test_insert_palette_exception_handling(self, mock_db_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест обработки исключения при вставке палитры."""

        # Arrange
        slides_layouts = [{"presentationPaletteColors": ["#FF0000", "#00FF00"]}]
        layout_id = "test-layout-id"

        mock_generate_uuid.side_effect = ["uuid1", "uuid2"]
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_session.execute.side_effect = Exception("Database error")

        result = manager.insert(slides_layouts, layout_id)

        manager.open_session.assert_called_once_with("PresentationPalette")
        mock_session.rollback.assert_called_once()

        assert result is None


class TestColorSettingsManagerManager:

    @pytest.fixture
    def manager(self):
        """Фикстура для создания экземпляра менеджера."""
        return ColorSettingsManager()

    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии."""
        return Mock()

    @pytest.fixture
    def mock_table(self):
        """Фикстура для мока таблицы."""
        mock_table = Mock()
        mock_table.c = Mock()
        mock_table.c.name = Mock()
        return mock_table

    def test_init(self, manager):
        """Тест инициализации менеджера."""
        assert manager.table == "ColorSettings"

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_color_settings_success(self, mock_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест успешной вставки color settings."""

        test_uid = "test-uuid-12345"

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert()

        manager.open_session.assert_called_once_with("ColorSettings")
        mock_generate_uuid.assert_called_once()
        mock_sql_insert.assert_called_once_with(mock_table)

        expected_values = {"id": test_uid, "count": 1, "lightenStep": 0.3, "darkenStep": 0.3, "saturationAdjust": 0.3}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == test_uid

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.database.logger")
    def test_insert_color_settings_exception(self, mock_db_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест обработки исключения при вставке color settings."""

        test_uid = "test-uuid-12345"

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_session.execute.side_effect = Exception("Database error")

        result = manager.insert()

        manager.open_session.assert_called_once_with("ColorSettings")
        mock_session.rollback.assert_called_once()

        assert result is None


class TestPresentationLayoutStylesManager:

    @pytest.fixture
    def manager(self):
        """Фикстура для создания экземпляра менеджера."""
        return PresentationLayoutStylesManager()

    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии."""
        return Mock()

    @pytest.fixture
    def mock_table(self):
        """Фикстура для мока таблицы."""
        mock_table = Mock()
        mock_table.c = Mock()
        mock_table.c.name = Mock()
        return mock_table

    def test_init(self, manager):
        """Тест инициализации менеджера."""
        assert manager.table == "PresentationLayoutStyles"

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_presentation_layout_styles_success(self, mock_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест успешной вставки presentation layout styles."""

        # Arrange
        layout_id = "test-layout-id"
        color_settings_id = "test-color-settings-id"
        test_uid = "test-styles-uuid"

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(layout_id, color_settings_id)

        manager.open_session.assert_called_once_with("PresentationLayoutStyles")
        mock_generate_uuid.assert_called_once()
        mock_sql_insert.assert_called_once_with(mock_table)

        expected_values = {"id": test_uid, "colorSettingsId": color_settings_id, "presentationLayoutId": layout_id}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == test_uid

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_presentation_layout_styles_with_none_ids(self, mock_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест вставки с None значениями для ID."""

        test_uid = "test-styles-uuid"

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(None, None)

        manager.open_session.assert_called_once_with("PresentationLayoutStyles")

        expected_values = {"id": test_uid, "colorSettingsId": None, "presentationLayoutId": None}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == test_uid

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.database.logger")
    def test_insert_presentation_layout_styles_exception(self, mock_db_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест обработки исключения при вставке."""

        layout_id = "test-layout-id"
        color_settings_id = "test-color-settings-id"
        test_uid = "test-styles-uuid"

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_session.execute.side_effect = Exception("Database error")

        result = manager.insert(layout_id, color_settings_id)

        manager.open_session.assert_called_once_with("PresentationLayoutStyles")
        mock_session.rollback.assert_called_once()

        assert result is None

    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_presentation_layout_styles_empty_string_ids(self, mock_logger, mock_sql_insert, mock_generate_uuid, manager, mock_session, mock_table):
        """Тест вставки с пустыми строками для ID."""

        layout_id = ""
        color_settings_id = ""
        test_uid = "test-styles-uuid"

        mock_generate_uuid.return_value = test_uid
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(layout_id, color_settings_id)

        manager.open_session.assert_called_once_with("PresentationLayoutStyles")

        expected_values = {"id": test_uid, "colorSettingsId": "", "presentationLayoutId": ""}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == test_uid


class TestLayoutRolesManager:

    @pytest.fixture
    def manager(self):
        """Фикстура для создания экземпляра менеджера."""
        return LayoutRolesManager()

    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии."""
        return Mock()

    @pytest.fixture
    def mock_table(self):
        """Фикстура для мока таблицы."""
        mock_table = Mock()
        mock_table.c = Mock()
        return mock_table

    def test_init(self, manager):
        """Тест инициализации менеджера."""
        assert manager.table == "LayoutRoles"

    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_layout_role_success(self, mock_logger, mock_sql_insert, manager, mock_session, mock_table):
        """Тест успешной вставки layout role."""

        layout_id = "test-layout-id"
        user_role = "admin"

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(layout_id, user_role)

        manager.open_session.assert_called_once_with("LayoutRoles")
        mock_sql_insert.assert_called_once_with(mock_table)

        expected_values = {"presentationLayoutId": layout_id, "role": "ADMIN"}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == (layout_id, user_role)

    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_layout_role_with_none_layout_id(self, mock_logger, mock_sql_insert, manager, mock_session, mock_table):
        """Тест вставки с None значением для layout ID."""

        user_role = "editor"

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(None, user_role)

        manager.open_session.assert_called_once_with("LayoutRoles")

        expected_values = {"presentationLayoutId": None, "role": "EDITOR"}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == (None, user_role)

    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_layout_role_different_case_roles(self, mock_logger, mock_sql_insert, manager, mock_session, mock_table):
        """Тест вставки ролей в разном регистре."""

        layout_id = "test-layout-id"
        test_cases = [("admin", "ADMIN"), ("ADMIN", "ADMIN"), ("Editor", "EDITOR"), ("viewer", "VIEWER"), ("GUEST", "GUEST")]

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        for input_role, expected_role in test_cases:
            mock_sql_insert.reset_mock()
            mock_session.execute.reset_mock()
            mock_session.commit.reset_mock()

            mock_insert_query = Mock()
            mock_sql_insert.return_value = mock_insert_query

            mock_values_method = Mock()
            mock_insert_query.values = Mock(return_value=mock_values_method)

            result = manager.insert(layout_id, input_role)

            expected_values = {"presentationLayoutId": layout_id, "role": expected_role}
            mock_insert_query.values.assert_called_once_with(expected_values)

            mock_session.execute.assert_called_once_with(mock_values_method)
            mock_session.commit.assert_called_once()

            assert result == (layout_id, input_role)

    @patch("db_work.services.insert")
    @patch("db_work.database.logger")
    def test_insert_layout_role_exception(self, mock_db_logger, mock_sql_insert, manager, mock_session, mock_table):
        """Тест обработки исключения при вставке."""

        layout_id = "test-layout-id"
        user_role = "admin"

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        mock_session.execute.side_effect = Exception("Database error")

        result = manager.insert(layout_id, user_role)

        manager.open_session.assert_called_once_with("LayoutRoles")
        mock_session.rollback.assert_called_once()

        assert result is None

    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_layout_role_empty_strings(self, mock_logger, mock_sql_insert, manager, mock_session, mock_table):
        """Тест вставки с пустыми строками."""

        layout_id = ""
        user_role = ""

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_insert_query = Mock()
        mock_sql_insert.return_value = mock_insert_query

        mock_values_method = Mock()
        mock_insert_query.values = Mock(return_value=mock_values_method)

        result = manager.insert(layout_id, user_role)

        manager.open_session.assert_called_once_with("LayoutRoles")

        expected_values = {"presentationLayoutId": "", "role": ""}
        mock_insert_query.values.assert_called_once_with(expected_values)

        mock_session.execute.assert_called_once_with(mock_values_method)
        mock_session.commit.assert_called_once()

        assert result == ("", "")


class TestSlideLayoutManager:

    @pytest.fixture
    def manager(self):
        """Фикстура для создания экземпляра менеджера."""
        return SlideLayoutManager()

    @pytest.fixture
    def mock_session(self):
        """Фикстура для мока сессии."""
        return Mock()

    @pytest.fixture
    def mock_table(self):
        """Фикстура для мока таблицы."""
        mock_table = Mock()
        mock_table.c = Mock()
        mock_table.c.presentationLayoutId = Mock()
        mock_table.c.id = Mock()
        mock_table.c.name = Mock()
        mock_table.c.number = Mock()
        return mock_table

    def test_init(self, manager):
        """Тест инициализации менеджера."""
        assert manager.table == "SlideLayout"

    @patch("db_work.services.get_slide_layout_data_from_cache")
    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.select")
    @patch("db_work.services.update")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_or_update_all_new_records(self, mock_logger, mock_insert, mock_update, mock_select, mock_generate_uuid, mock_get_cache_data, manager, mock_session, mock_table):
        """Тест вставки всех записей как новых (нет существующих в БД)."""

        layout_id = "test-layout-id"

        cache_data = [
            {
                "name": "Slide 1",
                "number": 1,
                "imagesCount": 2,
                "maxTokensPerBlock": 100,
                "maxWordsPerSentence": 20,
                "minWordsPerSentence": 5,
                "sentences": 3,
                "isLast": False,
                "forGeneration": True,
                "presentationLayoutIndexColor": "#FF0000",
                "dimensions": {},
                "blocks": [],
                "slide_type": "normal",
                "columns": 2,
                "presentationPaletteColors": [],
                "slideConfig": {},
            },
            {
                "name": "Slide 2",
                "number": 2,
                "imagesCount": 1,
                "maxTokensPerBlock": 150,
                "maxWordsPerSentence": 25,
                "minWordsPerSentence": 3,
                "sentences": 4,
                "isLast": True,
                "forGeneration": False,
                "presentationLayoutIndexColor": "#00FF00",
                "dimensions": {},
                "blocks": [],
                "slide_type": "summary",
                "columns": 1,
                "presentationPaletteColors": [],
                "slideConfig": {},
            },
        ]

        mock_get_cache_data.return_value = cache_data

        expected_uuids = ["uuid1", "uuid2"]
        mock_generate_uuid.side_effect = expected_uuids
        mock_postgres_data = []
        mock_session.execute.return_value.fetchall.return_value = mock_postgres_data

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_select_query = Mock()
        mock_select.return_value = mock_select_query

        mock_where_clause = Mock()
        mock_select_query.where.return_value = mock_where_clause

        mock_insert_query = Mock()
        mock_insert.return_value = mock_insert_query

        result = manager.insert_or_update(layout_id)

        manager.open_session.assert_called_once_with("SlideLayout")
        mock_get_cache_data.assert_called_once_with(layout_id)

        assert mock_insert.call_count == 2
        assert mock_update.call_count == 0

        assert mock_generate_uuid.call_count == 2

        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("send 2 slide layouts" in call for call in info_calls)
        assert any("insert 2 items" in call for call in info_calls)
        assert any("update 0 items" in call for call in info_calls)

        assert len(result) == 2
        assert result[0]["id"] == "uuid1"
        assert result[1]["id"] == "uuid2"

    @patch("db_work.services.get_slide_layout_data_from_cache")
    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.select")
    @patch("db_work.services.update")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_or_update_all_existing_records_no_changes(self, mock_logger, mock_insert, mock_update, mock_select, mock_generate_uuid, mock_get_cache_data, manager, mock_session, mock_table):
        """Тест когда все записи существуют и не требуют изменений."""

        layout_id = "test-layout-id"
        cache_data = [{"name": "Slide 1", "number": 1, "imagesCount": 2, "maxTokensPerBlock": 100, "maxWordsPerSentence": 20, "minWordsPerSentence": 5, "sentences": 3, "isLast": False, "forGeneration": True, "presentationLayoutIndexColor": "#FF0000"}]
        mock_get_cache_data.return_value = cache_data

        mock_row = Mock()
        mock_row.id = "existing-uuid"
        mock_row.name = "Slide 1"
        mock_row.number = 1
        mock_row.imagesCount = 2
        mock_row.maxTokensPerBlock = 100
        mock_row.maxWordsPerSentence = 20
        mock_row.minWordsPerSentence = 5
        mock_row.sentences = 3
        mock_row.isLast = False
        mock_row.forGeneration = True
        mock_row.presentationLayoutIndexColor = "#FF0000"

        mock_postgres_data = [mock_row]
        mock_session.execute.return_value.fetchall.return_value = mock_postgres_data

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_select_query = Mock()
        mock_select.return_value = mock_select_query

        mock_where_clause = Mock()
        mock_select_query.where.return_value = mock_where_clause

        result = manager.insert_or_update(layout_id)

        manager.open_session.assert_called_once_with("SlideLayout")
        mock_get_cache_data.assert_called_once_with(layout_id)

        mock_insert.assert_not_called()
        mock_update.assert_not_called()

        info_calls = mock_logger.info.call_args_list
        assert any("send 1 slide layouts" in str(call) for call in info_calls)
        assert any("insert 0 items" in str(call) for call in info_calls)
        assert any("update 0 items" in str(call) for call in info_calls)

        assert len(result) == 1
        assert result[0]["id"] == "existing-uuid"

    @patch("db_work.services.get_slide_layout_data_from_cache")
    @patch("db_work.services.generate_uuid")
    @patch("db_work.services.select")
    @patch("db_work.services.update")
    @patch("db_work.services.insert")
    @patch("db_work.services.logger")
    def test_insert_or_update_with_changes(self, mock_logger, mock_insert, mock_update, mock_select, mock_generate_uuid, mock_get_cache_data, manager, mock_session, mock_table):
        """Тест когда записи существуют но требуют обновления."""

        layout_id = "test-layout-id"
        cache_data = [{"name": "Slide 1", "number": 1, "imagesCount": 3, "maxTokensPerBlock": 100, "maxWordsPerSentence": 20, "minWordsPerSentence": 5, "sentences": 3, "isLast": False, "forGeneration": True, "presentationLayoutIndexColor": "#FF0000"}]

        mock_get_cache_data.return_value = cache_data

        mock_row = Mock()
        mock_row.id = "existing-uuid"
        mock_row.name = "Slide 1"
        mock_row.number = 1
        mock_row.imagesCount = 2
        mock_row.maxTokensPerBlock = 100
        mock_row.maxWordsPerSentence = 20
        mock_row.minWordsPerSentence = 5
        mock_row.sentences = 3
        mock_row.isLast = False
        mock_row.forGeneration = True
        mock_row.presentationLayoutIndexColor = "#FF0000"

        mock_postgres_data = [mock_row]
        mock_session.execute.return_value.fetchall.return_value = mock_postgres_data

        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_select_query = Mock()
        mock_select.return_value = mock_select_query

        mock_where_clause = Mock()
        mock_select_query.where.return_value = mock_where_clause

        mock_update_query = Mock()
        mock_update.return_value = mock_update_query

        mock_where_update = Mock()
        mock_update_query.where.return_value = mock_where_update

        mock_values_method = Mock()
        mock_where_update.values.return_value = mock_values_method

        result = manager.insert_or_update(layout_id)

        manager.open_session.assert_called_once_with("SlideLayout")
        mock_get_cache_data.assert_called_once_with(layout_id)

        mock_update.assert_called_once()
        mock_insert.assert_not_called()

        info_calls = mock_logger.info.call_args_list
        assert any("send 1 slide layouts" in str(call) for call in info_calls)
        assert any("insert 0 items" in str(call) for call in info_calls)
        assert any("update 1 items" in str(call) for call in info_calls)
        assert len(result) == 1
        assert result[0]["id"] == "existing-uuid"

    @patch("db_work.services.get_slide_layout_data_from_cache")
    @patch("db_work.services.select")
    @patch("db_work.database.logger")
    def test_insert_or_update_exception(self, mock_db_logger, mock_select, mock_get_cache_data, manager, mock_session, mock_table):
        """Тест обработки исключения."""

        layout_id = "test-layout-id"

        mock_get_cache_data.return_value = [{"name": "Slide 1", "number": 1}]
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        mock_session.execute.side_effect = Exception("Database error")

        result = manager.insert_or_update(layout_id)

        manager.open_session.assert_called_once_with("SlideLayout")
        mock_session.rollback.assert_called_once()

        assert result is None

    @patch("db_work.services.get_slide_layout_data_from_cache")
    @patch("db_work.services.select")
    @patch("db_work.services.logger")
    def test_insert_or_update_empty_cache(self, mock_logger, mock_select, mock_get_cache_data, manager, mock_session, mock_table):
        """Тест с пустым кэшем."""

        layout_id = "test-layout-id"

        mock_get_cache_data.return_value = []
        manager.open_session = Mock(return_value=(mock_table, mock_session))

        result = manager.insert_or_update(layout_id)

        manager.open_session.assert_called_once_with("SlideLayout")
        mock_get_cache_data.assert_called_once_with(layout_id)

        assert mock_session.execute.call_count == 2

        info_calls = mock_logger.info.call_args_list
        assert any("send 0 slide layouts" in str(call) for call in info_calls)
        assert any("insert 0 items" in str(call) for call in info_calls)
        assert any("update 0 items" in str(call) for call in info_calls)

        assert result == []


# class TestPresentationPaletteManager:

#     @pytest.fixture
#     def manager(self):
#         """Фикстура для создания экземпляра менеджера."""
#         return PresentationPaletteManager()

#     @pytest.fixture
#     def mock_session(self):
#         """Фикстура для мока сессии."""
#         return Mock()

#     @pytest.fixture
#     def mock_table(self):
#         """Фикстура для мока таблицы."""
#         mock_table = Mock()
#         mock_table.c = Mock()
#         mock_table.c.name = Mock()
#         return mock_table

#     def test_init(self, manager):
#         """Тест инициализации менеджера."""
#         assert manager.table == ""
