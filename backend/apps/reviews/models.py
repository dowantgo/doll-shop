from django.db import models

from apps.orders.models import OrderItem
from apps.products.models import Product
from apps.users.models import User


class Review(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    )

    # One paid order item can be reviewed once.
    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='Order item',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Product',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='User',
    )
    rating = models.PositiveSmallIntegerField(verbose_name='Rating')
    content = models.TextField(verbose_name='Content')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_APPROVED,
        verbose_name='Status',
    )
    audit_remark = models.CharField(max_length=255, blank=True, verbose_name='Audit remark')
    audit_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audited_reviews',
        verbose_name='Audited by',
    )
    audit_at = models.DateTimeField(null=True, blank=True, verbose_name='Audited at')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'status', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f'Review<{self.id}> user={self.user_id} product={self.product_id}'


class ReviewReply(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='Review',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_replies',
        verbose_name='User',
    )
    content = models.TextField(verbose_name='Content')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    class Meta:
        verbose_name = 'Review reply'
        verbose_name_plural = 'Review replies'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['review', 'created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'ReviewReply<{self.id}> review={self.review_id} user={self.user_id}'
