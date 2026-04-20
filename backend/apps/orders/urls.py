from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    # Iter3 contract aliases: keep stable external paths while preserving legacy router paths.
    path('price-preview/', OrderViewSet.as_view({'post': 'price_preview'}), name='order-price-preview'),
    path('<str:order_id>/apply-coupon/', OrderViewSet.as_view({'post': 'apply_coupon'}), name='order-apply-coupon'),
    path('<int:pk>/logistics/', OrderViewSet.as_view({'get': 'logistics'}), name='order-logistics'),
    path('', include(router.urls)),
]
