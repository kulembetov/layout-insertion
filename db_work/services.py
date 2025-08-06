from database import BaseManager
from sqlalchemy import insert, select
from sqlalchemy.exc import DBAPIError
from utils import generate_uuid

from log_utils import setup_logger

logger = setup_logger(__name__)


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()

    def select_an_entry_from_presentation_layout(self, name: str) -> bool | None:
        """Find A Field In PresentationLayout By Name."""

        presentation_layout_table, session = self.open_session("PresentationLayout")

        try:
            query = select(presentation_layout_table).where(presentation_layout_table.c.name == name)
            result = session.execute(query).fetchone()
            if result:
                return True
            else:
                return False

        except DBAPIError or Exception as exc:
            logger.error(f"Попытка добавить шаблон завершилась ошибкой: {exc}")
            session.rollback()

        finally:
            session.close()

    def insert_an_entry_in_presentation_layout(self, name: str) -> str | None:
        """Add New Field In PresentationLayout."""

        presentation_layout_table, session = self.open_session("PresentationLayout")
        id = generate_uuid()

        try:
            values = {"id": id, "name": name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return id

        except DBAPIError or Exception as exc:
            logger.error(f"Попытка добавить шаблон завершилась ошибкой: {exc}")
            session.rollback()

        finally:
            session.close()


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()

    def select_id_from_color_settings(self) -> str | None:
        """Find A Id In ColorSettings Table"""

        color_settings_table, session = self.open_session("ColorSettings")

        try:
            query = select(color_settings_table.c.id).where(color_settings_table.c.id is not None).limit(1)
            result = session.execute(query).scalar_one_or_none()
            if result:
                return result

        except DBAPIError or Exception as exc:
            logger.error(f"Попытка добавить шаблон завершилась ошибкой: {exc}")
            session.rollback()

        finally:
            session.close()


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()

    def insert_an_entry_in_presentation_layout_styles(self, presentation_layout_id: str) -> str | None:
        """Inserts ColorSettingsID and PresentationLayoutID into PresentationLayoutStyles."""

        presentation_layout_styles_table, session = self.open_session("PresentationLayoutStyles")

        id = generate_uuid()
        color_settings_id = ColorSettingsManager().select_id_from_color_settings()

        try:
            values = {"id": id, "colorSettingsId": color_settings_id, "presentationLayoutId": presentation_layout_id}
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return id

        except DBAPIError or Exception as exc:
            logger.error(f"Попытка добавить шаблон завершилась ошибкой: {exc}")
            session.rollback()

        finally:
            session.close()


# if __name__ == '__main__':
#     print(PresentationLayoutManager().select_an_entry_from_presentation_layout('classic'))
#     print(PresentationLayoutManager().insert_an_entry_in_presentation_layout('test_name'))
#     print(ColorSettingsManager().select_id_from_color_settings())
#     print(PresentationLayoutStylesManager().insert_an_entry_in_presentation_layout_styles(id))
#
#     id = PresentationLayoutManager().insert_an_entry_in_presentation_layout('test_name')
#     print(id)
#     print(PresentationLayoutStylesManager().insert_an_entry_in_presentation_layout_styles(id))
