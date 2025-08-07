from django.core.cache import cache

from django_app.config.settings import CACHE_ENABLED


def get_cached_request(key: str) -> list[dict] | None:
    if CACHE_ENABLED:
        cached_data = cache.get(key)
        if cached_data:
            return cached_data
    return None


def set_cached_request(key: str, data: list[dict]) -> None:
    if CACHE_ENABLED:
        cache.set(key, data)
