import uuid_utils as uuid
from database import create_connection
from sqlalchemy import MetaData, Table, bindparam, insert, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


def select_an_entry_in_presentation_layout(name: str) -> bool:
    """Searches for a field by name in the presentation_layout table."""

    engine = create_connection()
    metadata = MetaData()
    presentation_layout_table = Table("PresentationLayout", metadata, autoload_with=engine)

    query = select(presentation_layout_table).where(presentation_layout_table.c.name == bindparam("name"))

    try:
        with engine.connect() as connection:
            result_proxy = connection.execute(query, {"name": name})
            results = result_proxy.fetchone()

            if results:
                return True
            else:
                return False

    except DBAPIError:
        return False

    except Exception:
        return False


def insert_an_entry_in_presentation_layout(name: str) -> bool:
    """Insert a field in the presentation_layout table."""

    engine = create_connection()
    metadata = MetaData()
    presentation_layout_table = Table("PresentationLayout", metadata, autoload_with=engine)

    values = {"id": generate_uuid(), "name": name}
    query = insert(presentation_layout_table).values(values)

    try:
        with Session(engine) as session:
            session.execute(query)
            session.commit()
            return True

    except DBAPIError:
        return False

    except Exception:
        return False
