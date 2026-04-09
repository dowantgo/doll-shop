from django.db import models

class Category(models.Model):
    """Product category"""
    name = models.CharField(max_length=100, unique=True, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='描述')
    icon = models.ImageField(upload_to='categories/', blank=True, verbose_name='分类图标')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['sort_order', '-created_at']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model"""
    name = models.CharField(max_length=200, verbose_name='商品名称')
    description = models.TextField(verbose_name='描述')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, related_name='products', verbose_name='分类')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='价格')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='成本')
    stock = models.IntegerField(default=0, verbose_name='库存')
    sales = models.IntegerField(default=0, verbose_name='销售数量')
    is_hot = models.BooleanField(default=False, verbose_name='热点商品')
    hot_sort_order = models.IntegerField(default=0, verbose_name='热点排序')
    status = models.BooleanField(default=True, verbose_name='上架状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-is_hot', '-hot_sort_order', '-created_at']
        indexes = [
            models.Index(fields=['-is_hot', '-hot_sort_order']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='商品')
    image = models.ImageField(upload_to='products/', verbose_name='图片')
    is_main = models.BooleanField(default=False, verbose_name='是否主图')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '商品图片'
        verbose_name_plural = '商品图片'
        ordering = ['-is_main', 'sort_order', '-created_at']
    
    def __str__(self):
        return f'{self.product.name} - {self.image}'


class InventoryLog(models.Model):
    """Inventory change log"""
    LOG_TYPE_CHOICES = (
        ('in', '入库'),
        ('out', '出库'),
        ('adjust', '调整'),
        ('return', '退货'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs', verbose_name='商品')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, verbose_name='类型')
    quantity = models.IntegerField(verbose_name='数量')
    before_stock = models.IntegerField(verbose_name='变更前库存')
    after_stock = models.IntegerField(verbose_name='变更后库存')
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '库存日志'
        verbose_name_plural = '库存日志'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.product.name} - {self.get_log_type_display()}'
