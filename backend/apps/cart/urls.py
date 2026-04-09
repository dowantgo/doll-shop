from django.urls import path
from .views import CartViewSet

cart_view = CartViewSet.as_view({
    'get': 'me',
    'post': 'add',
})

urlpatterns = [
    path('', cart_view, name='cart'),
    path('add/', CartViewSet.as_view({'post': 'add'}), name='cart-add'),
    path('update_quantity/', CartViewSet.as_view({'post': 'update_quantity'}), name='cart-update-quantity'),
    path('remove/', CartViewSet.as_view({'post': 'remove'}), name='cart-remove'),
    path('clear/', CartViewSet.as_view({'post': 'clear'}), name='cart-clear'),
]
