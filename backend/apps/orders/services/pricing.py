import logging
from decimal import Decimal

from apps.coupons.models import UserCoupon
from apps.coupons.services import (
    calc_coupon_discount,
    calc_full_reduction,
    to_money,
    validate_coupon_for_amount,
)

logger = logging.getLogger(__name__)


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


def pending_payment_probe(user):
    """Lightweight observability probe used by performance/logging checks."""
    try:
        from apps.payment.models import PaymentTransaction

        txn = (
            PaymentTransaction.objects
            .filter(order__user=user, status='pending')
            .order_by('-created_at')
            .only('out_trade_no')
            .first()
        )
        return txn.out_trade_no if txn else ''
    except Exception as exc:
        logger.debug('pending_payment_probe_failed user_id=%s error=%s', getattr(user, 'id', ''), exc)
        return ''
