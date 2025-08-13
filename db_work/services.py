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
                        updated_slides.append((compared_row.name, compared_row.id))

                else:
                    new_entry = dict(uuid_data_item)
                    new_entry["id"] = generate_uuid()
                    stmt = insert(slide_layout_table).values(**new_entry)
                    session.execute(stmt)
                    session.commit()
                    added_slides.append((new_entry["name"], new_entry["id"]))

            updated_query = select(slide_layout_table).where(slide_layout_table.c.presentationLayoutId == presentation_layout_id)
            session.execute(updated_query)

            changes = []
            for name, id_ in added_slides + updated_slides:
                action = "Added" if (name, id_) in added_slides else "Updated"
                # changes.append(f"{action}: {name} {id_}")
                changes.append({"Action": action, "Name": name, "id": id_})
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
        self.table = "SlideLayoutStyles"

    def insert(self, slide_layouts: list[dict]):
        """Insert a field in SlideLayoutStyles Table."""

        # Возможно сюда нужно будет добвать логику на uodate
        slide_layout_styles_table, session = self.open_session(self.table)

        def logic():
            for item in slide_layouts:
                values = {"slideLayoutId": item.get("id")}

                query = insert(slide_layout_styles_table).values(values)
                session.execute(query)

            session.commit()
            return None

        return super().execute(logic, session)


# poetry run python -m db_work.services

# if __name__ == "__main__":
