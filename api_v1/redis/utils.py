from typing import Optional

from django.core.cache import cache
from config.settings import CACHE_ENABLED


def gen_key(file_id: str, filter_mode: Optional[str] = None, params: Optional[list] = None) -> str:
    key = f"figma={file_id}"
    if filter_mode and params:
        key += f":filter-mode={filter_mode}"
        param_str = ':'.join(map(str, sorted(params)))
        key += f":params={param_str}"
    return key


def get_cached_request(key: str) -> Optional[dict]:
    # to-do: refactor
    if CACHE_ENABLED and cache.get(key):
        return cache.get(key)
    return None


def set_cached_request(key: str, data: dict) -> None:
    if CACHE_ENABLED:
        cache.set(key, data)
