import logging
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from apps.coupons.models import UserCoupon
from apps.coupons.services import (
    calc_coupon_discount,
    calc_full_reduction,
    to_money,
    validate_coupon_for_amount,
)

logger = logging.getLogger(__name__)
_PAYMENT_PROBE_CACHE_KEY = 'orders:pricing:payment-probe:user:{user_id}'
_PAYMENT_PROBE_CACHE_TTL = int(timedelta(minutes=15).total_seconds())


def build_pricing_preview(*, subtotal_amount: Decimal, user_coupon: UserCoupon = None):
    subtotal_amount = to_money(subtotal_amount)
    full_reduction_amount = to_money(calc_full_reduction(subtotal_amount))
    amount_after_full_reduction = max(subtotal_amount - full_reduction_amount, Decimal('0.00'))

    coupon_discount_amount = Decimal('0.00')
    coupon_error = ''
    if user_coupon:
        valid, message = validate_coupon_for_amount(user_coupon, amount_after_full_reduction)
        if not valid:
            coupon_error = message
        else:
            coupon_discount_amount = to_money(calc_coupon_discount(user_coupon, amount_after_full_reduction))

    final_payable_amount = to_money(max(amount_after_full_reduction - coupon_discount_amount, Decimal('0.00')))
    return {
        'subtotal_amount': str(subtotal_amount),
        'full_reduction_amount': str(full_reduction_amount),
        'coupon_discount_amount': str(coupon_discount_amount),
        'final_payable_amount': str(final_payable_amount),
        'coupon_error': coupon_error,
    }


def _payment_probe_cache_key(user_id):
    return _PAYMENT_PROBE_CACHE_KEY.format(user_id=user_id)


def set_pending_payment_probe(user_id, payment_id, timeout=_PAYMENT_PROBE_CACHE_TTL):
    if not user_id:
        return
    cache.set(_payment_probe_cache_key(user_id), payment_id or '', timeout=timeout)


def clear_pending_payment_probe(user_id, payment_id=None):
    if not user_id:
        return

    cache_key = _payment_probe_cache_key(user_id)
    if payment_id:
        cached_payment_id = cache.get(cache_key)
        if cached_payment_id and cached_payment_id != payment_id:
            return
    cache.delete(cache_key)


def pending_payment_probe(user):
    """Lightweight observability probe used by performance/logging checks."""
    user_id = getattr(user, 'id', None)
    if not user_id:
        return ''

    cache_key = _payment_probe_cache_key(user_id)
    sentinel = object()
    cached_payment_id = cache.get(cache_key, sentinel)
    if cached_payment_id is not sentinel:
        return cached_payment_id or ''

    try:
        from apps.payment.models import PaymentTransaction

        txn = (
            PaymentTransaction.objects
            .filter(order__user_id=user_id, status='pending')
            .order_by('-created_at')
            .only('out_trade_no')
            .first()
        )
        payment_id = txn.out_trade_no if txn else ''
        cache.set(cache_key, payment_id, timeout=_PAYMENT_PROBE_CACHE_TTL)
        return payment_id
    except Exception as exc:
        logger.debug('pending_payment_probe_failed user_id=%s error=%s', user_id, exc)
        return ''
