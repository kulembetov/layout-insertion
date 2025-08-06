import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine

load_dotenv()

def create_connection() -> Optional["Engine"]:
    """Create connection to DB."""

    DB_NAME = os.getenv("POSTGRES_DB")
    USERNAME = os.getenv("POSTGRES_USER")
    PASSWORD = os.getenv("POSTGRES_PASSWORD")
    HOST = os.getenv("POSTGRES_HOST")
    PORT = os.getenv("POSTGRES_PORT")
    DATABASE_URL = f"postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

    try:
        engine = create_engine(DATABASE_URL, echo=False)
        return engine
    except Exception:
        raise
