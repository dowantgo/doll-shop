import hashlib
import logging
from typing import Tuple

from django.core.cache import cache
from django.utils import timezone

from dollshop.metrics import metric_increment

logger = logging.getLogger(__name__)

LOGIN_FAIL_WINDOW_SECONDS = 10 * 60
LOGIN_LOCK_SECONDS = 15 * 60
LOGIN_FAIL_THRESHOLD = 5
CAPTCHA_LIMIT_WINDOW_SECONDS = 60
CAPTCHA_LIMIT_COUNT = 20
EMAIL_COOLDOWN_SECONDS = 60
EMAIL_LIMIT_WINDOW_SECONDS = 30 * 60
EMAIL_LIMIT_COUNT = 5
EMAIL_IP_LIMIT_WINDOW_SECONDS = 10 * 60
EMAIL_IP_LIMIT_COUNT = 10


def get_client_ip(request) -> str:
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _safe_token(raw: str) -> str:
    text = (raw or '').strip().lower()
    if not text:
        return 'empty'
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def _window_counter_key(prefix: str, suffix: str) -> str:
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


def _window_rate_limit(prefix: str, suffix: str, *, limit: int, window_seconds: int, metric_name: str):
    key = _window_counter_key(prefix, suffix)
    count = _increment_window_counter(key, window_seconds)
    allowed = count <= limit
    if not allowed:
        metric_increment(metric_name)
    return allowed, count


def get_login_lock_status(identifier: str, ip: str) -> Tuple[bool, int]:
    lock_key = _window_counter_key('login-lock', f'{_safe_token(identifier)}:{_safe_token(ip)}')
    expires_at = cache.get(lock_key)
    if not expires_at:
        return False, 0
    remaining = max(int(expires_at - timezone.now().timestamp()), 0)
    if remaining <= 0:
        cache.delete(lock_key)
        return False, 0
    metric_increment('login_lock_hit')
    return True, remaining


def record_login_failure(identifier: str, ip: str) -> Tuple[bool, int]:
    fail_key = _window_counter_key('login-fail', f'{_safe_token(identifier)}:{_safe_token(ip)}')
    count = _increment_window_counter(fail_key, LOGIN_FAIL_WINDOW_SECONDS)
    metric_increment('login_fail')
    if count >= LOGIN_FAIL_THRESHOLD:
        lock_key = _window_counter_key('login-lock', f'{_safe_token(identifier)}:{_safe_token(ip)}')
        expires_at = timezone.now().timestamp() + LOGIN_LOCK_SECONDS
        cache.set(lock_key, expires_at, timeout=LOGIN_LOCK_SECONDS)
        metric_increment('login_lock_set')
        logger.warning('login_lock_set identifier=%s ip=%s fail_count=%s', _safe_token(identifier), ip, count)
        return True, LOGIN_LOCK_SECONDS
    return False, count


def clear_login_failures(identifier: str, ip: str) -> None:
    suffix = f'{_safe_token(identifier)}:{_safe_token(ip)}'
    cache.delete(_window_counter_key('login-fail', suffix))
    cache.delete(_window_counter_key('login-lock', suffix))


def check_captcha_rate_limit(ip: str):
    return _window_rate_limit(
        'captcha',
        _safe_token(ip),
        limit=CAPTCHA_LIMIT_COUNT,
        window_seconds=CAPTCHA_LIMIT_WINDOW_SECONDS,
        metric_name='captcha_rate_limited',
    )


def check_email_send_limits(email: str, ip: str):
    email_token = _safe_token(email)
    ip_token = _safe_token(ip)
    cooldown_key = _window_counter_key('email-cooldown', email_token)
    cooldown_until = int(cache.get(cooldown_key, 0) or 0)
    if cooldown_until > timezone.now().timestamp():
        metric_increment('email_code_cooldown_hit')
        return False, 'cooldown', max(int(cooldown_until - timezone.now().timestamp()), 0)

    allowed_email, email_count = _window_rate_limit(
        'email-send',
        email_token,
        limit=EMAIL_LIMIT_COUNT,
        window_seconds=EMAIL_LIMIT_WINDOW_SECONDS,
        metric_name='email_code_rate_limited',
    )
    if not allowed_email:
        return False, 'email_limit', email_count

    allowed_ip, ip_count = _window_rate_limit(
        'email-send-ip',
        ip_token,
        limit=EMAIL_IP_LIMIT_COUNT,
        window_seconds=EMAIL_IP_LIMIT_WINDOW_SECONDS,
        metric_name='email_code_ip_rate_limited',
    )
    if not allowed_ip:
        return False, 'ip_limit', ip_count

    return True, 'ok', 0


def record_email_send_success(email: str) -> None:
    email_token = _safe_token(email)
    expires_at = timezone.now().timestamp() + EMAIL_COOLDOWN_SECONDS
    cache.set(_window_counter_key('email-cooldown', email_token), expires_at, timeout=EMAIL_COOLDOWN_SECONDS)
