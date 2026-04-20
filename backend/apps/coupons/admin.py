from django.contrib import admin

from .models import CouponTemplate, OrderDiscountSnapshot, UserCoupon


@admin.register(CouponTemplate)
class CouponTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'discount_amount',
        'min_spend_amount',
        'total_quota',
        'claimed_count',
        'per_user_limit',
        'status',
        'valid_from',
        'valid_to',
    )
    list_filter = ('status', 'coupon_type')
    search_fields = ('name',)


@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'coupon_no', 'user', 'template', 'status', 'claimed_at', 'used_at')
    list_filter = ('status',)
    search_fields = ('coupon_no', 'user__username', 'template__name')


@admin.register(OrderDiscountSnapshot)
class OrderDiscountSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'user_coupon',
        'subtotal_amount',
        'full_reduction_amount',
        'coupon_discount_amount',
        'final_payable_amount',
        'updated_at',
    )
    search_fields = ('order__order_id',)
