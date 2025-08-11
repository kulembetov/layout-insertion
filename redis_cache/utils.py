from django.core.cache import cache

from django_app.config.settings import CACHE_ENABLED


def get_cached_request(key: str) -> list[dict] | None:
    if not CACHE_ENABLED:
        return None
    return cache.get(key)


def set_cached_request(key: str, data: list[dict]) -> None:
    if CACHE_ENABLED:
        cache.set(key, data)
