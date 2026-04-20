from django.contrib import admin

from .models import RefundAuditLog, RefundRequest


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'refund_no',
        'user',
        'order',
        'order_item',
        'quantity',
        'requested_amount',
        'approved_amount',
        'status',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('refund_no', 'order__order_id', 'user__username')


@admin.register(RefundAuditLog)
class RefundAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'refund', 'operator', 'action', 'note', 'created_at')
    search_fields = ('refund__refund_no', 'operator__username', 'action', 'note')
