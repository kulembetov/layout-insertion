from typing import Optional

from django.core.cache import cache
from config.settings import CACHE_ENABLED


def gen_key(file_id: str, filter_mode: Optional[str] = None, params: Optional[list] = None) -> str:
    ...


def get_cached_request(key: str) -> Optional[dict]:
    if CACHE_ENABLED and cache.get(key):
        return cache.get(key)
    return None


def set_cached_request(key: str, data: dict) -> None:
    if CACHE_ENABLED and not cache.get(key):
        cache.set(key, data)
