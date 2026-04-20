from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClaimCouponViewSet, MyCouponViewSet

router = DefaultRouter()
router.register(r'my', MyCouponViewSet, basename='my-coupons')
router.register(r'claim', ClaimCouponViewSet, basename='claim-coupon')

urlpatterns = [
    path('', include(router.urls)),
]
