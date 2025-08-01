from typing import Optional

from django.core.cache import cache
from django_app.config.settings import CACHE_ENABLED


# def gen_key(file_id: str, filter_type: Optional[str] = None, filter_names: Optional[list] = None) -> str:
#     key = f"figma={file_id}"
#     if filter_type and filter_names:
#         key += f":filter-type={filter_type}"
#         names_str = ':'.join(map(str, sorted(filter_names)))
#         key += f":filter-names={names_str}"
#     return key


def get_cached_request(key: str) -> Optional[dict]:
    if CACHE_ENABLED:
        cached_data = cache.get(key)
        if cached_data:
            return cached_data
    return None


def set_cached_request(key: str, data: dict) -> None:
    if CACHE_ENABLED:
        cache.set(key, data)

