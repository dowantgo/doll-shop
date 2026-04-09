from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Custom user model"""
    ROLE_CHOICES = (
        ('user', '普通用户'),
        ('admin', '管理员'),
    )
    
    phone = models.CharField(max_length=20, blank=True, verbose_name='电话')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user', verbose_name='角色')
    avatar = models.ImageField(upload_to='avatars/', blank=True, verbose_name='头像')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username


class Address(models.Model):
    """User address model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', verbose_name='用户')
    name = models.CharField(max_length=100, verbose_name='收货人名字')
    phone = models.CharField(max_length=20, verbose_name='电话')
    province = models.CharField(max_length=100, verbose_name='省')
    city = models.CharField(max_length=100, verbose_name='市')
    district = models.CharField(max_length=100, verbose_name='区')
    address = models.CharField(max_length=200, verbose_name='详细地址')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '地址'
        verbose_name_plural = '地址'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.name}'


class PaymentRecord(models.Model):
    """Payment record model"""
    PAYMENT_METHOD_CHOICES = (
        ('alipay', '支付宝'),
        ('wechat', '微信'),
    )
    
    STATUS_CHOICES = (
        ('pending', '待支付'),
        ('success', '支付成功'),
        ('failed', '支付失败'),
        ('cancelled', '已取消'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_records', verbose_name='用户')
    order_id = models.CharField(max_length=100, verbose_name='订单号')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name='支付方式')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='支付金额')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='交易号')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '支付记录'
        verbose_name_plural = '支付记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.order_id}'
