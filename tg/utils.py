from aiogram.types import User
from tg.settings import ADMIN_LIST


def has_access(user_id: int) -> bool:
    if user_id in ADMIN_LIST:
        return True
    return False


def str_user(user: User) -> str:
    if user.username:
        return f'@{user.username}'
    return f'ID: {user.id}'
