from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'total_price', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('订单信息', {
            'fields': ('order_id', 'user', 'total_price', 'status')
        }),
        ('支付信息', {
            'fields': ('payment_method', 'paid_at')
        }),
        ('发货信息', {
            'fields': ('address', 'shipped_at', 'delivered_at')
        }),
        ('其他', {
            'fields': ('remark', 'expires_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    list_filter = ('order__created_at',)
    search_fields = ('order__order_id', 'product__name')
    readonly_fields = ('created_at',)
