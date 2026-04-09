from django.db import models
from apps.users.models import User, Address
from apps.products.models import Product
from django.utils import timezone
from datetime import timedelta


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('shipped', '已发货'),
        ('delivered', '已收货'),
        ('cancelled', '已取消'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', '待支付'),
        ('paid', '已支付'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('alipay', '支付宝'),
        ('wechat', '微信支付'),
        ('mock', '模拟支付'),
    )
    
    SHIPPING_COMPANY_CHOICES = (
        ('sf', '顺丰速运'),
        ('zto', '中通快递'),
        ('yto', '圆通速递'),
        ('sto', '申通快递'),
        ('yunda', '韵达速递'),
    )
    
    SHIPPING_STATUS_CHOICES = (
        ('not_shipped', '未发货'),
        ('shipped', '已发货'),
        ('in_transit', '运输中'),
        ('arrived', '已到达'),
        ('signed', '已签收'),
    )
    
    order_id = models.CharField(max_length=100, unique=True, verbose_name='订单号')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='用户')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总价')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='支付状态')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, verbose_name='支付方式')
    
    shipping_company = models.CharField(max_length=20, choices=SHIPPING_COMPANY_CHOICES, blank=True, verbose_name='快递公司')
    shipping_status = models.CharField(max_length=20, choices=SHIPPING_STATUS_CHOICES, default='not_shipped', verbose_name='物流状态')
    tracking_no = models.CharField(max_length=100, blank=True, verbose_name='快递单号')
    trade_no = models.CharField(max_length=128, blank=True, verbose_name='第三方交易号')
    
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, verbose_name='收货地址')
    remark = models.TextField(blank=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='支付时间')
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='发货时间')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='收货时间')
    expires_at = models.DateTimeField(verbose_name='支付过期时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return self.order_id
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            import uuid
            from django.utils.timezone import now
            self.order_id = f"ORD{now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"
        
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        
        if self.payment_status == 'paid' and self.status == 'pending':
            self.status = 'paid'
        
        super().save(*args, **kwargs)
    
    @property
    def shipping_company_display(self):
        return dict(self.SHIPPING_COMPANY_CHOICES).get(self.shipping_company, '')
    
    @property
    def shipping_status_display(self):
        return dict(self.SHIPPING_STATUS_CHOICES).get(self.shipping_status, '')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='订单')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name='商品')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='购买时价格')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '订单项目'
        verbose_name_plural = '订单项目'
        ordering = ['id']
    
    def __str__(self):
        product_name = self.product.name if self.product else '已删除商品'
        return f'{self.order.order_id} - {product_name}'
    
    @property
    def subtotal(self):
        return self.price * self.quantity
