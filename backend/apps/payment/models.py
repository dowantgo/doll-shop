from django.db import models
from django.conf import settings


class PaymentTransaction(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('alipay', '支付宝'),
        ('wechat', '微信支付'),
        ('mock', '模拟支付'),
    ]

    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('expired', '已过期'),
        ('closed', '已关闭'),
        ('failed', '支付失败'),
        ('refunded', '已退款'),
    ]

    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment_transactions',
        verbose_name='关联订单'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='alipay',
        verbose_name='支付方式'
    )
    trade_no = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        verbose_name='支付平台交易号'
    )
    out_trade_no = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='商户订单号'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='支付金额'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='支付状态'
    )
    qr_code = models.TextField(
        blank=True,
        null=True,
        verbose_name='支付二维码'
    )
    expire_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='过期时间'
    )
    paid_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='支付时间'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'payment_transaction'
        verbose_name = '支付交易记录'
        verbose_name_plural = '支付交易记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.out_trade_no} - {self.amount}"
