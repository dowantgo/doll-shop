from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from apps.coupons.models import OrderDiscountSnapshot
from apps.orders.models import Order, OrderItem

from .models import RefundRequest


MONEY_ZERO = Decimal('0.00')


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def order_subtotal(order: Order) -> Decimal:
    subtotal = order.items.aggregate(total=Sum('price'))['total']
    if subtotal is None:
        subtotal = MONEY_ZERO
    # aggregate on price misses quantity, compute explicitly
    real = MONEY_ZERO
    for item in order.items.all():
        real += money(item.price) * item.quantity
    return money(real)


def order_item_paid_total(order: Order, order_item: OrderItem) -> Decimal:
    base = money(order_item.price) * order_item.quantity
    subtotal = order_subtotal(order)
    if subtotal <= MONEY_ZERO:
        return MONEY_ZERO

    final_payable = money(order.total_price)
    if hasattr(order, 'discount_snapshot') and order.discount_snapshot:
        final_payable = money(order.discount_snapshot.final_payable_amount)
    elif final_payable <= MONEY_ZERO:
        final_payable = subtotal

    share = (base / subtotal) * final_payable
    return money(share)


def order_item_refunded_quantity(order_item: OrderItem) -> int:
    used = (
        RefundRequest.objects.filter(order_item=order_item)
        .exclude(status__in=[RefundRequest.STATUS_REJECTED, RefundRequest.STATUS_FAILED])
        .aggregate(total=Sum('quantity'))
        .get('total')
    )
    return int(used or 0)


def order_item_refunded_amount(order_item: OrderItem) -> Decimal:
    used = (
        RefundRequest.objects.filter(order_item=order_item)
        .exclude(status__in=[RefundRequest.STATUS_REJECTED, RefundRequest.STATUS_FAILED])
        .aggregate(total=Sum('approved_amount'))
        .get('total')
    )
    return money(used or MONEY_ZERO)
