from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Автоматически мокаем все зависимости для всех тестов."""
    with patch("db_work.services.select"), patch("db_work.services.cast"), patch("db_work.services.ColumnElement"), patch("db_work.services.logger"):
        yield
