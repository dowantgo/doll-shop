import hashlib
from typing import Tuple

from django.core.cache import cache

from dollshop.metrics import metric_increment

SECKILL_PRE_RESERVE_USER_LIMIT = 6
SECKILL_PRE_RESERVE_IP_LIMIT = 20
SECKILL_PRE_RESERVE_ACTIVITY_LIMIT = 12
SECKILL_PRE_RESERVE_WINDOW_SECONDS = 30


def _safe_token(raw: str) -> str:
    text = (raw or '').strip().lower()
    if not text:
        return 'empty'
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def _counter_key(prefix: str, suffix: str) -> str:
    return f'iter5.2:seckill:{prefix}:{suffix}'


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


def check_pre_reserve_limits(*, user_id: int, ip: str, activity_id: int) -> Tuple[bool, str]:
    allowed, _ = _check_limit(
        'reserve:user',
        str(user_id),
        limit=SECKILL_PRE_RESERVE_USER_LIMIT,
        window_seconds=SECKILL_PRE_RESERVE_WINDOW_SECONDS,
        metric_name='seckill_pre_reserve_rate_limited',
        dimension='user',
    )
    if not allowed:
        return False, '当前账号秒杀请求过于频繁，请稍后再试。'

    allowed, _ = _check_limit(
        'reserve:ip',
        _safe_token(ip),
        limit=SECKILL_PRE_RESERVE_IP_LIMIT,
        window_seconds=SECKILL_PRE_RESERVE_WINDOW_SECONDS,
        metric_name='seckill_pre_reserve_rate_limited',
        dimension='ip',
    )
    if not allowed:
        return False, '当前 IP 秒杀请求过于频繁，请稍后再试。'

    allowed, _ = _check_limit(
        'reserve:activity',
        f'{user_id}:{activity_id}',
        limit=SECKILL_PRE_RESERVE_ACTIVITY_LIMIT,
        window_seconds=SECKILL_PRE_RESERVE_WINDOW_SECONDS,
        metric_name='seckill_pre_reserve_rate_limited',
        dimension='activity',
    )
    if not allowed:
        return False, '该秒杀商品当前请求过于集中，请稍后再试。'

    return True, ''
