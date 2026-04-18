from django.contrib import admin

from .models import Review, ReviewReply


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'content')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'created_at')
    search_fields = ('review__content', 'user__username', 'content')
    readonly_fields = ('created_at', 'updated_at')
