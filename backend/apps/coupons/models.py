import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def _coupon_no(prefix: str) -> str:
    now_text = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'{prefix}{now_text}{uuid.uuid4().hex[:8].upper()}'


def gen_user_coupon_no() -> str:
    return _coupon_no('CPN')


class CouponTemplate(models.Model):
    TYPE_FIXED = 'fixed'
    TYPE_CHOICES = (
        (TYPE_FIXED, 'Fixed amount off'),
    )

    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    )

    name = models.CharField(max_length=120, verbose_name='Template name')
    coupon_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_FIXED,
        verbose_name='Coupon type',
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    min_spend_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_quota = models.PositiveIntegerField(default=0)
    claimed_count = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_coupon_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'valid_from', 'valid_to']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_valid_now(self) -> bool:
        now = timezone.now()
        return self.status == self.STATUS_ACTIVE and self.valid_from <= now <= self.valid_to


class UserCoupon(models.Model):
    STATUS_UNUSED = 'unused'
    STATUS_LOCKED = 'locked'
    STATUS_USED = 'used'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = (
        (STATUS_UNUSED, 'Unused'),
        (STATUS_LOCKED, 'Locked'),
        (STATUS_USED, 'Used'),
        (STATUS_EXPIRED, 'Expired'),
    )

    coupon_no = models.CharField(max_length=64, unique=True, default=gen_user_coupon_no)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_coupons',
    )
    template = models.ForeignKey(
        CouponTemplate,
        on_delete=models.CASCADE,
        related_name='user_coupons',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNUSED)
    claimed_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-claimed_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['template', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'template', 'coupon_no'],
                name='uniq_user_template_coupon_no',
            )
        ]

    def __str__(self):
        return f'{self.coupon_no}:{self.user_id}'


class OrderDiscountSnapshot(models.Model):
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='discount_snapshot',
    )
    user_coupon = models.ForeignKey(
        UserCoupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_orders',
    )
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    full_reduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_payable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pricing_version = models.CharField(max_length=32, default='iter3-v1')
    pricing_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.order.order_id}'
