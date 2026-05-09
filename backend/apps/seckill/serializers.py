from rest_framework import serializers

from .models import SeckillActivity, SeckillAdminActionLog, SeckillReservation
from .redis_flow import get_activity_remaining_stock


class SeckillActivitySerializer(serializers.ModelSerializer):
    group_id = serializers.CharField(read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    remaining_stock = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = SeckillActivity
        fields = [
            'id',
            'group_id',
            'name',
            'product_id',
            'product_name',
            'main_image',
            'seckill_price',
            'total_stock',
            'reserved_stock',
            'remaining_stock',
            'per_user_limit',
            'status',
            'is_enabled',
            'start_at',
            'end_at',
        ]

    def get_main_image(self, obj):
        main = obj.product.images.filter(is_main=True).first()
        if not main:
            main = obj.product.images.first()
        if not main:
            return ''
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(main.image.url)
        return main.image.url

    def get_remaining_stock(self, obj):
        return get_activity_remaining_stock(obj.id, obj.remaining_stock)


class SeckillPreReserveSerializer(serializers.Serializer):
    activity_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)
    submit_token = serializers.CharField(required=True, allow_blank=False, max_length=128)


class SeckillIssueSubmitTokenSerializer(serializers.Serializer):
    activity_id = serializers.IntegerField(min_value=1)


class SeckillReservationSerializer(serializers.ModelSerializer):
    activity_id = serializers.IntegerField(source='activity.id', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SeckillReservation
        fields = [
            'id',
            'activity_id',
            'product_id',
            'product_name',
            'user_id',
            'activity_name',
            'quantity',
            'status',
            'idempotency_key',
            'reservation_token',
            'order_id',
            'reserved_expires_at',
            'created_at',
        ]


class SeckillCreateOrderSerializer(serializers.Serializer):
    reservation_id = serializers.IntegerField(min_value=1, required=False)
    reservation_token = serializers.CharField(required=False, allow_blank=False, max_length=128)
    address_id = serializers.IntegerField(min_value=1)
    remark = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        reservation_id = attrs.get('reservation_id')
        reservation_token = (attrs.get('reservation_token') or '').strip()
        if not reservation_id and not reservation_token:
            raise serializers.ValidationError('reservation_id or reservation_token is required.')
        attrs['reservation_token'] = reservation_token
        return attrs


class AdminSeckillActivitySerializer(serializers.ModelSerializer):
    group_id = serializers.CharField(required=False, allow_blank=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_current_stock = serializers.IntegerField(source='product.stock', read_only=True)
    remaining_stock = serializers.SerializerMethodField()

    class Meta:
        model = SeckillActivity
        fields = [
            'id',
            'group_id',
            'name',
            'product',
            'product_name',
            'product_current_stock',
            'seckill_price',
            'total_stock',
            'reserved_stock',
            'remaining_stock',
            'per_user_limit',
            'status',
            'is_enabled',
            'start_at',
            'end_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['reserved_stock', 'remaining_stock', 'created_at', 'updated_at']

    def get_remaining_stock(self, obj):
        return get_activity_remaining_stock(obj.id, obj.remaining_stock)

    def validate(self, attrs):
        start_at = attrs.get('start_at')
        end_at = attrs.get('end_at')
        if self.instance:
            if start_at is None:
                start_at = self.instance.start_at
            if end_at is None:
                end_at = self.instance.end_at
        if start_at and end_at and start_at >= end_at:
            raise serializers.ValidationError('Start time must be earlier than end time.')

        total_stock = attrs.get('total_stock')
        reserved_stock = self.instance.reserved_stock if self.instance else 0
        if total_stock is not None and total_stock < reserved_stock:
            raise serializers.ValidationError('Total stock cannot be lower than reserved stock.')

        return attrs


class AdjustSeckillStockSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['set', 'increase', 'decrease'])
    quantity = serializers.IntegerField(min_value=1)
    remark = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdjustSeckillPriceSerializer(serializers.Serializer):
    seckill_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    remark = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ChangeSeckillStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            SeckillActivity.STATUS_DRAFT,
            SeckillActivity.STATUS_PREHEATING,
            SeckillActivity.STATUS_ONLINE,
            SeckillActivity.STATUS_ENDED,
            SeckillActivity.STATUS_OFFLINE,
        ]
    )
    remark = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminSeckillReservationSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    order_payment_status = serializers.CharField(source='order.payment_status', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)

    class Meta:
        model = SeckillReservation
        fields = [
            'id',
            'activity',
            'activity_name',
            'product',
            'product_name',
            'user',
            'user_name',
            'quantity',
            'status',
            'idempotency_key',
            'reservation_token',
            'order',
            'order_id',
            'order_payment_status',
            'order_status',
            'reserved_expires_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ReleaseReservationSerializer(serializers.Serializer):
    remark = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminSeckillActionLogSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.username', read_only=True)
    activity_name = serializers.CharField(source='activity.name', read_only=True)

    class Meta:
        model = SeckillAdminActionLog
        fields = [
            'id',
            'action_type',
            'operator',
            'operator_name',
            'activity',
            'activity_name',
            'reservation',
            'before_data',
            'after_data',
            'remark',
            'created_at',
        ]
        read_only_fields = fields
