from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admin_views import (
    AdminStatsViewSet,
    AdminProductViewSet,
    AdminCategoryViewSet,
    AdminOrderViewSet,
    AdminUserViewSet
)

router = DefaultRouter()
router.register(r'stats', AdminStatsViewSet, basename='admin-stats')
router.register(r'products', AdminProductViewSet, basename='admin-products')
router.register(r'categories', AdminCategoryViewSet, basename='admin-categories')
router.register(r'orders', AdminOrderViewSet, basename='admin-orders')
router.register(r'users', AdminUserViewSet, basename='admin-users')

urlpatterns = [
    path('', include(router.urls)),
]
