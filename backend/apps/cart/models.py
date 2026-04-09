from django.db import models
from apps.users.models import User
from apps.products.models import Product

class CartItem(models.Model):
    """Shopping cart items"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items', verbose_name='用户')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    quantity = models.IntegerField(default=1, verbose_name='数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '购物车项目'
        verbose_name_plural = '购物车项目'
        unique_together = ['user', 'product']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.product.name}'
