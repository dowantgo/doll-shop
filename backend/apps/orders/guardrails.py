import hashlib
from typing import Tuple

from django.core.cache import cache

from dollshop.metrics import metric_increment

ORDER_SUBMIT_LOCK_TTL_SECONDS = 30
ORDER_SUBMIT_RESULT_TTL_SECONDS = 24 * 60 * 60

PRICE_PREVIEW_USER_LIMIT = 30
PRICE_PREVIEW_IP_LIMIT = 60
PRICE_PREVIEW_RESOURCE_LIMIT = 20
PRICE_PREVIEW_WINDOW_SECONDS = 60

CREATE_ORDER_USER_LIMIT = 8
CREATE_ORDER_IP_LIMIT = 20
CREATE_ORDER_WINDOW_SECONDS = 30


def _safe_token(raw: str) -> str:
    text = (raw or '').strip().lower()
    if not text:
        return 'empty'
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def _counter_key(prefix: str, suffix: str) -> str:
    return f'iter5:{prefix}:{suffix}'


def _increment_window_counter(key: str, window_seconds: int) -> int:
    created = cache.add(key, 1, timeout=window_seconds)
    if created:
        return 1
    try:
        return cache.incr(key)
    except Exception:
        current = int(cache.get(key, 0) or 0) + 1
        cache.set(key, current, timeout=window_seconds)
        return current


def _check_limit(
    prefix: str,
    suffix: str,
    *,
    limit: int,
    window_seconds: int,
    metric_name: str,
    **metric_labels,
) -> Tuple[bool, int]:
    key = _counter_key(prefix, suffix)
    count = _increment_window_counter(key, window_seconds)
    allowed = count <= limit
    if not allowed:
        metric_increment(metric_name, **metric_labels)
    return allowed, count


def check_price_preview_limits(user_id: int, ip: str, resource_token: str) -> Tuple[bool, str]:
    allowed, _ = _check_limit(
        'price-preview:user',
        str(user_id),
        limit=PRICE_PREVIEW_USER_LIMIT,
        window_seconds=PRICE_PREVIEW_WINDOW_SECONDS,
        metric_name='price_preview_rate_limited',
        dimension='user',
    )
    if not allowed:
        return False, 'Too many price preview requests from the current user.'

    allowed, _ = _check_limit(
        'price-preview:ip',
        _safe_token(ip),
        limit=PRICE_PREVIEW_IP_LIMIT,
        window_seconds=PRICE_PREVIEW_WINDOW_SECONDS,
        metric_name='price_preview_rate_limited',
        dimension='ip',
    )
    if not allowed:
        return False, 'Too many price preview requests from the current IP.'

    allowed, _ = _check_limit(
        'price-preview:resource',
        f'{user_id}:{_safe_token(resource_token)}',
        limit=PRICE_PREVIEW_RESOURCE_LIMIT,
        window_seconds=PRICE_PREVIEW_WINDOW_SECONDS,
        metric_name='price_preview_rate_limited',
        dimension='resource',
    )
    if not allowed:
        return False, 'This item is being previewed too frequently. Please try again later.'

    return True, ''


def check_create_order_limits(user_id: int, ip: str) -> Tuple[bool, str]:
    allowed, _ = _check_limit(
        'create-order:user',
        str(user_id),
        limit=CREATE_ORDER_USER_LIMIT,
        window_seconds=CREATE_ORDER_WINDOW_SECONDS,
        metric_name='create_order_rate_limited',
        dimension='user',
    )
    if not allowed:
        return False, 'Order submission is too frequent for the current user.'

    allowed, _ = _check_limit(
        'create-order:ip',
        _safe_token(ip),
        limit=CREATE_ORDER_IP_LIMIT,
        window_seconds=CREATE_ORDER_WINDOW_SECONDS,
        metric_name='create_order_rate_limited',
        dimension='ip',
    )
    if not allowed:
        return False, 'Order submission is too frequent for the current IP.'

    return True, ''


def _idempotency_lock_key(user_id: int, idempotency_key: str) -> str:
    return _counter_key('order-submit:lock', f'{user_id}:{_safe_token(idempotency_key)}')


def _idempotency_result_key(user_id: int, idempotency_key: str) -> str:
    return _counter_key('order-submit:result', f'{user_id}:{_safe_token(idempotency_key)}')


def acquire_order_submit_guard(user_id: int, idempotency_key: str) -> bool:
    created = cache.add(
        _idempotency_lock_key(user_id, idempotency_key),
        'processing',
        timeout=ORDER_SUBMIT_LOCK_TTL_SECONDS,
    )
    if not created:
        metric_increment('order_idempotency_guard_hit')
    return created


def release_order_submit_guard(user_id: int, idempotency_key: str) -> None:
    cache.delete(_idempotency_lock_key(user_id, idempotency_key))


def store_order_submit_result(user_id: int, idempotency_key: str, order_id: str) -> None:
    cache.set(
        _idempotency_result_key(user_id, idempotency_key),
        order_id,
        timeout=ORDER_SUBMIT_RESULT_TTL_SECONDS,
    )


def get_order_submit_result(user_id: int, idempotency_key: str) -> str:
    return cache.get(_idempotency_result_key(user_id, idempotency_key)) or ''
