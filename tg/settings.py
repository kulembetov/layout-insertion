import os

from dotenv import load_dotenv

load_dotenv()

# Database settings
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_LIST_RAW = os.getenv("ADMIN_LIST")
if ADMIN_LIST_RAW:
    ADMIN_LIST = list(map(int, ADMIN_LIST_RAW.split(",")))

# Redis
CACHE_LOCATION = os.getenv("CACHE_LOCATION")
