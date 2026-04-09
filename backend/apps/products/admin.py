from django.contrib import admin
from .models import Category, Product, ProductImage, InventoryLog

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'created_at')
    list_editable = ('sort_order',)
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'sales', 'is_hot', 'hot_sort_order', 'status', 'created_at')
    list_filter = ('status', 'is_hot', 'category', 'created_at')
    list_editable = ('is_hot', 'hot_sort_order', 'status')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]
    readonly_fields = ('created_at', 'updated_at', 'sales')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_main', 'sort_order')
    list_filter = ('is_main', 'product')
    list_editable = ('is_main', 'sort_order')

@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'log_type', 'quantity', 'before_stock', 'after_stock', 'created_at')
    list_filter = ('log_type', 'created_at', 'product')
    search_fields = ('product__name', 'remark')
    readonly_fields = ('created_at',)
