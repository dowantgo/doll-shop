from django.contrib import admin
from .models import User, Address, PaymentRecord

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('username', 'email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'city', 'is_default')
    list_filter = ('is_default', 'created_at')
    search_fields = ('user__username', 'name')

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'payment_method', 'amount', 'status')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
