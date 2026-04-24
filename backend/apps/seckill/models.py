import uuid

from django.conf import settings
from django.db import models

from apps.orders.models import Order
from apps.products.models import Product


def gen_group_id():
    return str(uuid.uuid4())


class SeckillActivity(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PREHEATING = 'preheating'
    STATUS_ONLINE = 'online'
    STATUS_ENDED = 'ended'
    STATUS_OFFLINE = 'offline'

    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PREHEATING, 'Preheating'),
        (STATUS_ONLINE, 'Online'),
        (STATUS_ENDED, 'Ended'),
        (STATUS_OFFLINE, 'Offline'),
    )

    name = models.CharField(max_length=120, verbose_name='Activity name')
    group_id = models.CharField(
        max_length=36,
        default=gen_group_id,
        db_index=True,
        verbose_name='Activity group id',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='seckill_activities',
        verbose_name='Product',
    )
    seckill_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Seckill price')
    total_stock = models.PositiveIntegerField(default=0, verbose_name='Total stock')
    reserved_stock = models.PositiveIntegerField(default=0, verbose_name='Reserved stock')
    per_user_limit = models.PositiveIntegerField(default=1, verbose_name='Per user limit')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Status',
    )
    is_enabled = models.BooleanField(default=True, verbose_name='Enabled')
    start_at = models.DateTimeField(verbose_name='Start time')
    end_at = models.DateTimeField(verbose_name='End time')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    class Meta:
        verbose_name = 'Seckill activity'
        verbose_name_plural = 'Seckill activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_enabled', 'start_at']),
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['group_id', 'status', 'is_enabled'], name='idx_seckill_group_status'),
            models.Index(fields=['status', 'start_at', 'end_at'], name='idx_seckill_window'),
        ]

    def __str__(self):
        return f'{self.name}<{self.group_id}:{self.product_id}>'

    @property
    def remaining_stock(self):
        remain = self.total_stock - self.reserved_stock
        return remain if remain > 0 else 0


class SeckillReservation(models.Model):
    STATUS_RESERVED = 'reserved'
    STATUS_ORDERED = 'ordered'
    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = (
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_ORDERED, 'Ordered'),
        (STATUS_PAID, 'Paid'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
    )

    activity = models.ForeignKey(
        SeckillActivity,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Activity',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='seckill_reservations',
        verbose_name='Product',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seckill_reservations',
        verbose_name='User',
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Quantity')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RESERVED,
        verbose_name='Status',
    )
    idempotency_key = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Idempotency key',
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seckill_reservation',
        verbose_name='Order',
    )
    reserved_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Reserved expires at',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    class Meta:
        verbose_name = 'Seckill reservation'
        verbose_name_plural = 'Seckill reservations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity', 'status', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'idempotency_key'], name='idx_seckill_user_idem'),
            models.Index(fields=['status', 'reserved_expires_at'], name='idx_seckill_expire_scan'),
        ]

    def __str__(self):
        return f'Reservation<{self.id}> activity={self.activity_id} user={self.user_id}'


class SeckillAdminActionLog(models.Model):
    ACTION_CREATE_ACTIVITY = 'create_activity'
    ACTION_UPDATE_ACTIVITY = 'update_activity'
    ACTION_DELETE_ACTIVITY = 'delete_activity'
    ACTION_ADJUST_STOCK = 'adjust_stock'
    ACTION_ADJUST_PRICE = 'adjust_price'
    ACTION_CHANGE_STATUS = 'change_status'
    ACTION_RELEASE_RESERVATION = 'release_reservation'

    ACTION_CHOICES = (
        (ACTION_CREATE_ACTIVITY, 'Create activity'),
        (ACTION_UPDATE_ACTIVITY, 'Update activity'),
        (ACTION_DELETE_ACTIVITY, 'Delete activity'),
        (ACTION_ADJUST_STOCK, 'Adjust stock'),
        (ACTION_ADJUST_PRICE, 'Adjust price'),
        (ACTION_CHANGE_STATUS, 'Change status'),
        (ACTION_RELEASE_RESERVATION, 'Release reservation'),
    )

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seckill_admin_action_logs',
        verbose_name='Operator',
    )
    activity = models.ForeignKey(
        SeckillActivity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_action_logs',
        verbose_name='Activity',
    )
    reservation = models.ForeignKey(
        SeckillReservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_action_logs',
        verbose_name='Reservation',
    )
    action_type = models.CharField(max_length=40, choices=ACTION_CHOICES, verbose_name='Action type')
    before_data = models.JSONField(default=dict, blank=True, verbose_name='Before data')
    after_data = models.JSONField(default=dict, blank=True, verbose_name='After data')
    remark = models.CharField(max_length=255, blank=True, verbose_name='Remark')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')

    class Meta:
        verbose_name = 'Seckill admin action log'
        verbose_name_plural = 'Seckill admin action logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['operator', '-created_at']),
            models.Index(fields=['activity', '-created_at']),
        ]

    def __str__(self):
        return f'ActionLog<{self.id}> {self.action_type}'
