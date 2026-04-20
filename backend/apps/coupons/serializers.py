from rest_framework import serializers

from .models import CouponTemplate, OrderDiscountSnapshot, UserCoupon


class CouponTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponTemplate
        fields = [
            'id',
            'name',
            'coupon_type',
            'discount_amount',
            'min_spend_amount',
            'total_quota',
            'claimed_count',
            'per_user_limit',
            'valid_from',
            'valid_to',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['claimed_count', 'created_at', 'updated_at']


class UserCouponSerializer(serializers.ModelSerializer):
    template = CouponTemplateSerializer(read_only=True)

    class Meta:
        model = UserCoupon
        fields = [
            'id',
            'coupon_no',
            'status',
            'claimed_at',
            'locked_at',
            'used_at',
            'template',
        ]


class ClaimCouponSerializer(serializers.Serializer):
    template_id = serializers.IntegerField()


class AdminIssueCouponSerializer(serializers.Serializer):
    template_id = serializers.IntegerField()
    user_id = serializers.IntegerField(required=False)
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )

    def validate(self, attrs):
        if not attrs.get('user_id') and not attrs.get('user_ids'):
            raise serializers.ValidationError('user_id or user_ids is required.')
        return attrs


class PricePreviewItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PricePreviewSerializer(serializers.Serializer):
    items = PricePreviewItemSerializer(many=True, required=False)
    coupon_id = serializers.IntegerField(required=False, allow_null=True)


class ApplyCouponSerializer(serializers.Serializer):
    coupon_id = serializers.IntegerField(required=False, allow_null=True)


class OrderDiscountSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDiscountSnapshot
        fields = [
            'subtotal_amount',
            'full_reduction_amount',
            'coupon_discount_amount',
            'final_payable_amount',
            'pricing_version',
            'pricing_snapshot',
        ]
