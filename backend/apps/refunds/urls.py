from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RefundViewSet

router = DefaultRouter()
router.register(r'', RefundViewSet, basename='refund')

urlpatterns = [
    # Iter3 contract alias: explicit "my" endpoint for user-side refund list.
    path('my/', RefundViewSet.as_view({'get': 'list'}), name='refund-my-list'),
    path('', include(router.urls)),
]
