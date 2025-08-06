from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from tg.settings import DATABASE_URL


class BaseManager:
    """Base Class For Managers."""

    def __init__(self):
        self.engine = create_engine(DATABASE_URL, echo=False)
        self.metadata = MetaData()

    def open_session(self, table_name: str) -> tuple[Table, Session]:
        """Open session for some table."""

        ps_table = Table(table_name, self.metadata, autoload_with=self.engine)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        session = Session()

        return ps_table, session
