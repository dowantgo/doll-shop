from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admin_views import (
    AdminStatsViewSet,
    AdminProductViewSet,
    AdminCategoryViewSet,
    AdminOrderViewSet,
    AdminUserViewSet
)
from apps.seckill.admin_views import (
    AdminSeckillActionLogViewSet,
    AdminSeckillActivityViewSet,
    AdminSeckillReservationViewSet,
    AdminSeckillStatsViewSet,
)
from apps.reviews.views import AdminReviewViewSet

router = DefaultRouter()
router.register(r'stats', AdminStatsViewSet, basename='admin-stats')
router.register(r'products', AdminProductViewSet, basename='admin-products')
router.register(r'categories', AdminCategoryViewSet, basename='admin-categories')
router.register(r'orders', AdminOrderViewSet, basename='admin-orders')
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'reviews', AdminReviewViewSet, basename='admin-reviews')
router.register(r'seckill-stats', AdminSeckillStatsViewSet, basename='admin-seckill-stats')
router.register(r'seckill-activities', AdminSeckillActivityViewSet, basename='admin-seckill-activities')
router.register(r'seckill-reservations', AdminSeckillReservationViewSet, basename='admin-seckill-reservations')
router.register(r'seckill-action-logs', AdminSeckillActionLogViewSet, basename='admin-seckill-action-logs')

urlpatterns = [
    path('', include(router.urls)),
]
