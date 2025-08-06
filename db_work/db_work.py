from sqlalchemy import MetaData, Table, insert, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy import insert, select
from sqlalchemy.orm import sessionmaker, Session

from database import create_connection

from db_utils import generate_uuid

class BaseManager():
    """Base Class For Managers."""

    def __init__(self):
        self.engine = create_connection()
        self.metadata = MetaData()

    def _open_session(self, table_name: str) -> tuple[Table, Session]:
        """Open Session For PresentationLayout Table."""

        presentation_layout_table = Table(table_name, self.metadata, autoload_with=self.engine)
        Session = sessionmaker(bind=self.engine)
        session = Session()

        return presentation_layout_table, session


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()

    def select_an_entry_from_presentation_layout(self, name: str) -> bool:
        """Find A Field In PresentationLayout By Name."""

        presentation_layout_table, session = self._open_session('PresentationLayout')

        try:
            query = select(presentation_layout_table).where(presentation_layout_table.c.name == name)
            result = session.execute(query).fetchone()
            if result:
                return True
            else:
                return False
            
        except DBAPIError:
            session.rollback()
            return False

        except Exception:
            session.rollback()
            return False
        
        finally:
            session.close()

    def insert_an_entry_in_presentation_layout(self, name: str) -> bool:
        """Add New Field In PresentationLayout."""

        presentation_layout_table, session = self._open_session('PresentationLayout')
        id = generate_uuid()
        
        try:
            values = {'id': id, 'name': name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return id
        
        except DBAPIError:
            session.rollback()
            return False

        except Exception:
            session.rollback()
            return False
        
        finally:
            session.close()


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()
    
    def select_id_from_color_settings(self) -> str:
        """Find A Id In ColorSettings Table"""

        color_settings_table, session = self._open_session('ColorSettings')

        try:
            query = select(color_settings_table.c.id).where(color_settings_table.c.id != None).limit(1)
            result = session.execute(query).scalar_one_or_none()
            if result:
                return result
            else:
                return False

        except DBAPIError:
            session.rollback()
            return False
        
        except Exception:
            session.rollback()
            return False

        finally:
            session.close()


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()

    def insert_an_entry_in_presentation_layout_styles(self, presentation_layout_id: str) -> str:
        """Inserts ColorSettingsID and PresentationLayoutID into PresentationLayoutStyles."""

        presentation_layout_styles_table, session = self._open_session('PresentationLayoutStyles')

        id = generate_uuid()
        color_settings_id = ColorSettingsManager().select_id_from_color_settings()

        try:
            values = {
                'id': id,
                'colorSettingsId': color_settings_id,
                'presentationLayoutId': presentation_layout_id
            }
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return id
        
        except DBAPIError:
            session.rollback()
            return False

        except Exception:
            session.rollback()
            return False
        
        finally:
            session.close()





# print(PresentationLayoutManager().select_an_entry_from_presentation_layout('classic'))
# print(PresentationLayoutManager().insert_an_entry_in_presentation_layout('test_name'))
# print(ColorSettingsManager().select_id_from_color_settings())
# print(PresentationLayoutStylesManager().insert_an_entry_in_presentation_layout_styles(id))

# id = PresentationLayoutManager().insert_an_entry_in_presentation_layout('test_name')
# print(id)
# print(PresentationLayoutStylesManager().insert_an_entry_in_presentation_layout_styles(id))



