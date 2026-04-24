from rest_framework import serializers

from apps.orders.models import Order, OrderItem

from .models import RefundRequest
from .services import (
    money,
    order_item_paid_total,
    order_item_refund_usage,
)


class RefundCreateSerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=100)
    order_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class RefundReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class RefundRequestSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    product_name = serializers.CharField(source='order_item.product.name', read_only=True)
    payment_method = serializers.CharField(source='order.payment_method', read_only=True)

    class Meta:
        model = RefundRequest
        fields = [
            'id',
            'refund_no',
            'order_id',
            'order_item',
            'product_name',
            'quantity',
            'reason',
            'requested_amount',
            'approved_amount',
            'status',
            'review_note',
            'payment_method',
            'reviewed_at',
            'processed_at',
            'last_error',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


def validate_refund_request(*, user, order_id: str, order_item_id: int, quantity: int):
    # Must be called inside transaction.atomic() so select_for_update can serialize
    # concurrent refund creation requests on the same order item.
    try:
        order = (
            Order.objects
            .select_for_update()
            .select_related('discount_snapshot')
            .prefetch_related('items')
            .get(order_id=order_id, user=user)
        )
    except Order.DoesNotExist:
        raise serializers.ValidationError('Order not found.')

    if order.payment_status != 'paid':
        raise serializers.ValidationError('Only paid orders can request refund.')

    try:
        order_item = (
            OrderItem.objects
            .select_for_update()
            .select_related('order', 'product')
            .get(id=order_item_id, order=order)
        )
    except OrderItem.DoesNotExist:
        raise serializers.ValidationError('Order item not found.')

    used_qty, used_amount = order_item_refund_usage(order_item)
    remaining_qty = max(order_item.quantity - used_qty, 0)
    if quantity > remaining_qty:
        raise serializers.ValidationError(f'Refund quantity exceeds remaining quantity ({remaining_qty}).')

    paid_total = order_item_paid_total(order, order_item)
    if order_item.quantity <= 0:
        raise serializers.ValidationError('Order item quantity invalid.')
    unit_paid = money(paid_total / order_item.quantity)
    requested_amount = money(unit_paid * quantity)
    refundable_amount = money(paid_total - used_amount)
    if requested_amount > refundable_amount:
        requested_amount = refundable_amount
    if requested_amount <= 0:
        raise serializers.ValidationError('No refundable amount left.')

    return order, order_item, requested_amount
