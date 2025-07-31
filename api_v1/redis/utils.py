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
    if CACHE_ENABLED:
        cached_data = cache.get(key)
        if cached_data:
            return cached_data


def set_cached_request(key: str, data: dict) -> None:
    if CACHE_ENABLED:
        cache.set(key, data)
