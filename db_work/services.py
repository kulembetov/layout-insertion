from sqlalchemy import insert, select

from db_work.database import BaseManager
from db_work.utils import generate_uuid


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()

    def select_layout_by_name(self, name: str) -> bool | None:
        """Find a row in 'PresentationLayout' by name."""

        presentation_layout_table, session = self.open_session("PresentationLayout")

        def logic():

            query = select(presentation_layout_table).where(presentation_layout_table.c.name == name)
            result = session.execute(query).fetchone()
            if result:
                return True
            else:
                return False

        return super().execute(logic, session)

    def insert_new_layout(self, name: str) -> str | None:
        """Add new row in 'PresentationLayout'."""

        presentation_layout_table, session = self.open_session("PresentationLayout")

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "name": name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        return super().execute(logic, session)


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()

    def select_color_id(self) -> str | None:
        """Find color id."""

        color_settings_table, session = self.open_session("ColorSettings")

        def logic():
            query = select(color_settings_table.c.id).where(color_settings_table.c.id.is_not(None)).limit(1)
            result = session.execute(query).scalar_one_or_none()
            return result if result else None

        return super().execute(logic, session)


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()

    def insert_new_ids(self, presentation_layout_id: str | None, color_settings_id: str | None) -> str | None:
        """Inserts ColorSettingsID and PresentationLayoutID into PresentationLayoutStyles."""

        presentation_layout_styles_table, session = self.open_session("PresentationLayoutStyles")

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "colorSettingsId": color_settings_id, "presentationLayoutId": presentation_layout_id}
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        return super().execute(logic, session)


# if __name__ == '__main__':
#     print(PresentationLayoutManager().select_layout_by_name('classic'))
#     print(PresentationLayoutManager().insert_new_layout('test_12'))
#     print(ColorSettingsManager().select_color_id())
#     print(PresentationLayoutStylesManager().insert_new_ids(id))
#
#     presentation_layout_id = PresentationLayoutManager().insert_new_layout('test_name')
#     print(presentation_layout_id)
#     color_settings_id = ColorSettingsManager().select_color_id()
#     print(color_settings_id)
#     print(PresentationLayoutStylesManager().insert_new_ids(presentation_layout_id, color_settings_id))
