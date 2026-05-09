import hashlib
import json
import logging
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection

from dollshop.metrics import metric_increment

logger = logging.getLogger(__name__)

SECKILL_SUBMIT_TOKEN_TTL_SECONDS = int(getattr(settings, 'SECKILL_SUBMIT_TOKEN_TTL_SECONDS', 120))
SECKILL_RESERVATION_TTL_SECONDS = int(
    getattr(settings, 'SECKILL_RESERVATION_EXPIRE_MINUTES', 10) * 60
)
SECKILL_PRE_RESERVE_RESULT_TTL_SECONDS = SECKILL_RESERVATION_TTL_SECONDS
SECKILL_CREATE_ORDER_LOCK_TTL_SECONDS = 30


def _safe_token(raw: str) -> str:
    text = (raw or '').strip().lower()
    if not text:
        return 'empty'
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def _redis():
    return get_redis_connection('default')


def submit_token_key(user_id: int, activity_id: int, submit_token: str) -> str:
    return f'iter5.2:seckill:submit-token:{user_id}:{activity_id}:{_safe_token(submit_token)}'


def stock_bucket_key(activity_id: int) -> str:
    return f'iter5.2:seckill:stock:{activity_id}'


def reservation_ticket_key(reservation_token: str) -> str:
    return f'iter5.2:seckill:reservation:{_safe_token(reservation_token)}'


def reservation_result_key(user_id: int, idempotency_key: str) -> str:
    return f'iter5.2:seckill:result:{user_id}:{_safe_token(idempotency_key)}'


def reservation_order_lock_key(reservation_token: str) -> str:
    return f'iter5.2:seckill:create-order:{_safe_token(reservation_token)}'


def reservation_expire_index_key() -> str:
    return 'iter5.2:seckill:reservation-expire-index'


def issue_submit_token(*, user_id: int, activity_id: int) -> str:
    submit_token = secrets.token_urlsafe(18)
    cache.set(
        submit_token_key(user_id, activity_id, submit_token),
        '1',
        timeout=SECKILL_SUBMIT_TOKEN_TTL_SECONDS,
    )
    return submit_token


def submit_token_ttl_seconds() -> int:
    return SECKILL_SUBMIT_TOKEN_TTL_SECONDS


def consume_submit_token(*, user_id: int, activity_id: int, submit_token: str) -> bool:
    key = submit_token_key(user_id, activity_id, submit_token)
    if not cache.get(key):
        metric_increment('seckill_submit_token_invalid')
        return False
    cache.delete(key)
    return True


def sync_activity_stock_bucket(*, activity_id: int, remaining_stock: int) -> int:
    remaining = max(int(remaining_stock), 0)
    _redis().set(stock_bucket_key(activity_id), remaining)
    return remaining


def drop_activity_stock_bucket(activity_id: int) -> None:
    _redis().delete(stock_bucket_key(activity_id))


def get_activity_remaining_stock(activity_id: int, fallback_remaining: int) -> int:
    value = _redis().get(stock_bucket_key(activity_id))
    if value is None:
        return max(int(fallback_remaining), 0)
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return max(int(fallback_remaining), 0)


def ensure_activity_stock_bucket(*, activity_id: int, fallback_remaining: int) -> int:
    key = stock_bucket_key(activity_id)
    current = _redis().get(key)
    if current is None:
        remaining = max(int(fallback_remaining), 0)
        _redis().set(key, remaining)
        return remaining
    try:
        return max(int(current), 0)
    except (TypeError, ValueError):
        remaining = max(int(fallback_remaining), 0)
        _redis().set(key, remaining)
        return remaining


def get_cached_reservation_token(*, user_id: int, idempotency_key: str) -> str:
    if not idempotency_key:
        return ''
    value = _redis().get(reservation_result_key(user_id, idempotency_key))
    if not value:
        return ''
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return str(value)


def _build_reservation_payload(
    *,
    reservation_token: str,
    user_id: int,
    activity_id: int,
    product_id: int,
    quantity: int,
    idempotency_key: str,
    expires_at,
) -> Dict[str, Any]:
    return {
        'reservation_token': reservation_token,
        'user_id': int(user_id),
        'activity_id': int(activity_id),
        'product_id': int(product_id),
        'quantity': int(quantity),
        'idempotency_key': idempotency_key or '',
        'status': 'reserved',
        'expires_at': expires_at.isoformat(),
    }


_HOLD_STOCK_AND_TICKET_SCRIPT = """
local stock_key = KEYS[1]
local ticket_key = KEYS[2]
local expire_index_key = KEYS[3]
local result_key = KEYS[4]
local quantity = tonumber(ARGV[1])
local payload = ARGV[2]
local ttl = tonumber(ARGV[3])
local expire_score = tonumber(ARGV[4])
local reservation_token = ARGV[5]
local result_ttl = tonumber(ARGV[6])

local stock = tonumber(redis.call('GET', stock_key) or '-1')
if stock < 0 then
  return {-2, -1}
end
if stock < quantity then
  return {0, stock}
end

redis.call('DECRBY', stock_key, quantity)
redis.call('SET', ticket_key, payload, 'EX', ttl)
redis.call('ZADD', expire_index_key, expire_score, reservation_token)
if result_key ~= '' then
  redis.call('SET', result_key, reservation_token, 'EX', result_ttl)
end
return {1, stock - quantity}
"""


def hold_stock_and_create_ticket(
    *,
    user_id: int,
    activity_id: int,
    product_id: int,
    quantity: int,
    idempotency_key: str,
) -> Tuple[bool, Dict[str, Any], int]:
    reservation_token = secrets.token_urlsafe(24)
    expires_at = timezone.now() + timedelta(seconds=SECKILL_RESERVATION_TTL_SECONDS)
    payload = _build_reservation_payload(
        reservation_token=reservation_token,
        user_id=user_id,
        activity_id=activity_id,
        product_id=product_id,
        quantity=quantity,
        idempotency_key=idempotency_key,
        expires_at=expires_at,
    )
    payload_json = json.dumps(payload, ensure_ascii=False)
    result_key = reservation_result_key(user_id, idempotency_key) if idempotency_key else ''
    result = _redis().eval(
        _HOLD_STOCK_AND_TICKET_SCRIPT,
        4,
        stock_bucket_key(activity_id),
        reservation_ticket_key(reservation_token),
        reservation_expire_index_key(),
        result_key,
        int(quantity),
        payload_json,
        SECKILL_RESERVATION_TTL_SECONDS,
        int(expires_at.timestamp()),
        reservation_token,
        SECKILL_PRE_RESERVE_RESULT_TTL_SECONDS,
    )
    status_code = int(result[0])
    remaining = int(result[1])
    if status_code == 1:
        metric_increment('seckill_stock_reserved', activity_id=activity_id)
        return True, payload, remaining
    if status_code == 0:
        metric_increment('seckill_stock_bucket_depleted', activity_id=activity_id)
        return False, {}, remaining
    logger.warning('seckill_stock_bucket_missing activity_id=%s', activity_id)
    return False, {}, -1


def load_reservation_ticket(reservation_token: str) -> Optional[Dict[str, Any]]:
    raw = _redis().get(reservation_ticket_key(reservation_token))
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        return json.loads(raw)
    except Exception:
        logger.exception('load_reservation_ticket_failed token=%s', reservation_token)
        return None


def acquire_create_order_lock(reservation_token: str) -> bool:
    created = cache.add(
        reservation_order_lock_key(reservation_token),
        'processing',
        timeout=SECKILL_CREATE_ORDER_LOCK_TTL_SECONDS,
    )
    if not created:
        metric_increment('seckill_create_order_guard_hit')
    return created


def release_create_order_lock(reservation_token: str) -> None:
    cache.delete(reservation_order_lock_key(reservation_token))


def clear_reservation_ticket(reservation_token: str) -> None:
    payload = load_reservation_ticket(reservation_token)
    pipe = _redis().pipeline()
    pipe.delete(reservation_ticket_key(reservation_token))
    pipe.zrem(reservation_expire_index_key(), reservation_token)
    pipe.execute()
    if payload and payload.get('idempotency_key'):
        _redis().setex(
            reservation_result_key(int(payload['user_id']), payload['idempotency_key']),
            SECKILL_PRE_RESERVE_RESULT_TTL_SECONDS,
            reservation_token,
        )


def restore_stock_from_ticket(reservation_token: str, *, reason: str) -> bool:
    client = _redis()
    ticket_key = reservation_ticket_key(reservation_token)
    with client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(ticket_key)
                raw = pipe.get(ticket_key)
                if not raw:
                    pipe.unwatch()
                    return False
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8')
                payload = json.loads(raw)
                quantity = int(payload['quantity'])
                activity_id = int(payload['activity_id'])
                pipe.multi()
                pipe.incrby(stock_bucket_key(activity_id), quantity)
                pipe.delete(ticket_key)
                pipe.zrem(reservation_expire_index_key(), reservation_token)
                pipe.execute()
                metric_increment('seckill_ticket_released', reason=reason)
                logger.info(
                    'seckill_ticket_released token=%s activity_id=%s quantity=%s reason=%s',
                    reservation_token,
                    activity_id,
                    quantity,
                    reason,
                )
                return True
            except Exception:
                pipe.reset()
                logger.exception('restore_stock_from_ticket_retry token=%s reason=%s', reservation_token, reason)
                return False


def restore_stock_from_db(activity_id: int, quantity: int, *, reason: str) -> None:
    _redis().incrby(stock_bucket_key(activity_id), int(quantity))
    metric_increment('seckill_stock_restored', reason=reason)


def pop_expired_reservation_tokens(limit: int = 100) -> list[str]:
    now_score = int(timezone.now().timestamp())
    items = _redis().zrangebyscore(reservation_expire_index_key(), min=0, max=now_score, start=0, num=limit)
    tokens = []
    for item in items:
        if isinstance(item, bytes):
            tokens.append(item.decode('utf-8'))
        else:
            tokens.append(str(item))
    return tokens
