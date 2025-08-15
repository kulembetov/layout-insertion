from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from log_utils import setup_logger
from tg.settings import DATABASE_URL

logger = setup_logger(__name__)


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

    @staticmethod
    def execute(logic, session):
        """Make try and except."""

        try:
            return logic()

        except (DBAPIError, Exception) as exc:
            logger.error(f"Произошла ошибка в {logic.__name__}: {exc}")
            session.rollback()
            return None

        finally:
            session.close()
