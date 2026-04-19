from django.conf import settings
from django.core.cache import cache
from django.db import transaction


def _feed_namespace() -> str:
    return getattr(settings, 'PRODUCT_FEED_CACHE_NAMESPACE', 'products:feed')


def _feed_version_key() -> str:
    return f'{_feed_namespace()}:version'


def _current_version() -> int:
    version_key = _feed_version_key()
    version = cache.get(version_key)
    if isinstance(version, int) and version > 0:
        return version
    cache.set(version_key, 1, None)
    return 1


def make_feed_cache_key(feed_name: str, limit: int) -> str:
    return f'{_feed_namespace()}:{feed_name}:v{_current_version()}:limit:{limit}'


def get_feed_ttl(feed_name: str) -> int:
    default_ttl = int(getattr(settings, 'PRODUCT_FEED_CACHE_TTL', 300))
    if feed_name == 'top-sales':
        return int(getattr(settings, 'PRODUCT_TOP_SALES_CACHE_TTL', default_ttl))
    if feed_name == 'hot-feed':
        return int(getattr(settings, 'PRODUCT_HOT_FEED_CACHE_TTL', default_ttl))
    return default_ttl


def bump_feed_version() -> int:
    version_key = _feed_version_key()
    try:
        return int(cache.incr(version_key))
    except ValueError:
        # Key not initialized in cache backend.
        if cache.add(version_key, 2, None):
            return 2
    except Exception:
        pass

    version = _current_version() + 1
    cache.set(version_key, version, None)
    return version


def bump_feed_version_on_commit() -> None:
    if transaction.get_connection().in_atomic_block:
        transaction.on_commit(bump_feed_version)
        return
    bump_feed_version()
