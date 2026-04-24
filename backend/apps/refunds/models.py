import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def gen_refund_no():
    return f'RFD{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid.uuid4().hex[:8].upper()}'


class RefundRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_REFUNDING = 'refunding'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_REFUNDING, 'Refunding'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    )

    refund_no = models.CharField(max_length=64, unique=True, default=gen_refund_no)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='refund_requests',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='refund_requests',
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.CASCADE,
        related_name='refund_requests',
    )
    quantity = models.PositiveIntegerField(default=1)
    reason = models.CharField(max_length=255, blank=True, default='')
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    review_note = models.CharField(max_length=255, blank=True, default='')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_refunds',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    external_refund_no = models.CharField(max_length=128, blank=True, default='')
    idempotency_key = models.CharField(max_length=128, blank=True, default='')
    last_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['order_item', 'status'], name='idx_refund_item_status'),
            models.Index(fields=['user', 'idempotency_key'], name='idx_refund_user_idem'),
        ]

    def __str__(self):
        return self.refund_no


class RefundAuditLog(models.Model):
    refund = models.ForeignKey(
        RefundRequest,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refund_audit_logs',
    )
    action = models.CharField(max_length=64)
    note = models.CharField(max_length=255, blank=True, default='')
    before_data = models.JSONField(default=dict, blank=True)
    after_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
