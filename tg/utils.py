import re
from urllib.parse import urlparse

from aiogram.types import User

from tg.settings import ADMIN_LIST


def has_access(user_id: int) -> bool:
    if user_id in ADMIN_LIST:
        return True
    return False


def to_str_user(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return f"ID: {user.id}"


def is_valid_figma_url(url_raw: str) -> bool:
    try:
        u = urlparse(url_raw)
    except Exception:
        return False

    if u.scheme != "https":
        return False

    if u.netloc not in {"www.figma.com", "figma.com"}:
        return False

    figma_path = re.compile(
        r"""
    ^design/                            # первый сегмент
    (?P<file_id>[A-Za-z0-9]+)/          # file_id — безопасные символы
    (?P<name>[^/?#]+)$                  # name — один сегмент без / ? #
    """,
        re.X,
    )

    # оставляем только первые три сегмента пути
    path = "/".join(u.path.strip("/").split("/")[:3])
    if not figma_path.match(path):
        return False

    # query может быть пустым или любым (param1=...&param2=...)
    # фрагмент (#...) тоже допускается
    return True


def extract_file_id(url: str) -> str | None:
    u = urlparse(url)
    m = re.search(r"/design/([^/]+)(?=/|$)", u.path)
    file_id = m.group(1) if m else None
    return file_id
