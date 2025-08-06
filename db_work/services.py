from sqlalchemy import insert, select
from sqlalchemy.exc import DBAPIError

from db_work.database import BaseManager
from db_work.utils import generate_uuid
from log_utils import setup_logger

logger = setup_logger(__name__)


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()

    def find_layout_by_name(self, name: str) -> bool | None:
        """Find a row in 'PresentationLayout' by name."""

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

    def insert_new_layout(self, name: str) -> str | None:
        """Add new row in 'PresentationLayout'."""

        presentation_layout_table, session = self.open_session("PresentationLayout")
        uid = generate_uuid()

        try:
            values = {"id": uid, "name": name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        except DBAPIError or Exception as exc:
            logger.error(f"Попытка добавить шаблон завершилась ошибкой: {exc}")
            session.rollback()

        finally:
            session.close()


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()

    def insert_new_color_settings(self) -> str | None:
        color_settings_table, session = self.open_session("ColorSettings")
        uid = generate_uuid()

        try:
            values = {"id": uid, "count": 1, "lightenStep": 0.3, "darkenStep": 0.3, "saturationAdjust": 0.3}
            query = insert(color_settings_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        except DBAPIError or Exception as exc:
            logger.error(f"Попытка добавить шаблон завершилась ошибкой: {exc}")
            session.rollback()

        finally:
            session.close()


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()

    def insert_new_ids(self, presentation_layout_id: str, color_settings_id: str) -> str | None:
        """Inserts ColorSettingsID and PresentationLayoutID into PresentationLayoutStyles."""

        presentation_layout_styles_table, session = self.open_session("PresentationLayoutStyles")
        uid = generate_uuid()

        try:
            values = {"id": uid, "colorSettingsId": color_settings_id, "presentationLayoutId": presentation_layout_id}
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return uid

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
