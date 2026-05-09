import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)


def _normalize_label(value: Any) -> str:
    return str(value).replace(' ', '_').replace(':', '_').replace('/', '_')


def metric_key(name: str, **labels) -> str:
    if not labels:
        return f'metrics:{name}'
    parts = [f'{key}={_normalize_label(val)}' for key, val in sorted(labels.items())]
    return f'metrics:{name}:' + '|'.join(parts)


def metric_increment(name: str, *, ttl: int = 86400, amount: int = 1, **labels) -> int:
    key = metric_key(name, **labels)
    created = cache.add(key, amount, timeout=ttl)
    if created:
        return amount
    try:
        return cache.incr(key, amount)
    except Exception:
        current = int(cache.get(key, 0) or 0) + amount
        cache.set(key, current, timeout=ttl)
        logger.debug('metric_increment_fallback key=%s value=%s', key, current)
        return current
