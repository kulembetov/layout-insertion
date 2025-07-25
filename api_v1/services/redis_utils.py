from typing import Optional

from django.core.cache import cache
from config.settings import CACHE_ENABLED

def get_cached_request(file_id: str) -> Optional[dict]:
    if CACHE_ENABLED and cache.get(file_id):
        return cache.get(file_id)
    return None

def set_cached_request(file_id: str, data: dict) -> None:
    if CACHE_ENABLED and not cache.get(file_id):
        cache.set(file_id, data)
