from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import DBAPIError

import os
from dotenv import load_dotenv
load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


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

    def execute(self, logic, session):
        """Make try and except."""

        try:
            return logic()
        
        except (DBAPIError, Exception) as exc:
            session.rollback()
            return None
    
        finally:
            session.close()