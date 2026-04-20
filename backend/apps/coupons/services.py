from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone

from .models import CouponTemplate, UserCoupon


MONEY_ZERO = Decimal('0.00')


def to_money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_full_reduction_rules():
    raw = getattr(settings, 'ORDER_FULL_REDUCTION_RULES', [(200, 20), (500, 60)])
    rules = []
    for threshold, reduction in raw:
        rules.append((to_money(threshold), to_money(reduction)))
    rules.sort(key=lambda x: x[0], reverse=True)
    return rules


def calc_full_reduction(subtotal: Decimal) -> Decimal:
    subtotal = to_money(subtotal)
    for threshold, reduction in get_full_reduction_rules():
        if subtotal >= threshold:
            return reduction
    return MONEY_ZERO


def validate_coupon_for_amount(user_coupon: UserCoupon, amount_after_full_reduction: Decimal):
    now = timezone.now()
    if user_coupon.status != UserCoupon.STATUS_UNUSED:
        return False, 'Coupon is not available.'
    template: CouponTemplate = user_coupon.template
    if template.status != CouponTemplate.STATUS_ACTIVE:
        return False, 'Coupon template is not active.'
    if not (template.valid_from <= now <= template.valid_to):
        return False, 'Coupon is out of valid time range.'
    if amount_after_full_reduction < template.min_spend_amount:
        return False, 'Order amount does not meet coupon minimum spend.'
    return True, ''


def calc_coupon_discount(user_coupon: UserCoupon, amount_after_full_reduction: Decimal) -> Decimal:
    if not user_coupon:
        return MONEY_ZERO
    discount = to_money(user_coupon.template.discount_amount)
    return min(discount, to_money(amount_after_full_reduction))
