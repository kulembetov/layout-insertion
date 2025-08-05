import uuid_utils as uuid

from aiogram.types import User
from tg.settings import ADMIN_LIST


def has_access(user_id: int) -> bool:
    if user_id in ADMIN_LIST:
        return True
    return False


def to_str_user(user: User) -> str:
    if user.username:
        return f'@{user.username}'
    return f'ID: {user.id}'


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())
