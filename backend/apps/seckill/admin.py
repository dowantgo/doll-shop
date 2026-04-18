from django.contrib import admin

from .models import SeckillActivity, SeckillAdminActionLog, SeckillReservation


@admin.register(SeckillActivity)
class SeckillActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'product', 'status', 'is_enabled', 'start_at', 'end_at', 'created_at')
    list_filter = ('status', 'is_enabled')
    search_fields = ('name', 'product__name')
    ordering = ('-created_at',)


@admin.register(SeckillReservation)
class SeckillReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'activity',
        'product',
        'user',
        'quantity',
        'status',
        'order',
        'reserved_expires_at',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('activity__name', 'product__name', 'user__username', 'idempotency_key')
    ordering = ('-created_at',)


@admin.register(SeckillAdminActionLog)
class SeckillAdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_type', 'operator', 'activity', 'reservation', 'created_at')
    list_filter = ('action_type',)
    search_fields = ('operator__username', 'activity__name', 'remark')
    ordering = ('-created_at',)
