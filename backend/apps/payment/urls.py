from django.urls import path
from .views import (
    CreatePaymentView,
    PaymentStatusView,
    MockPayView,
    ClosePaymentView,
    PaymentQueryView,
    ReconcilePaymentView,
    AliPayNotifyView,
)

urlpatterns = [
    path('create_payment/', CreatePaymentView.as_view(), name='payment-create'),
    path('reconcile/', ReconcilePaymentView.as_view(), name='payment-reconcile'),
    path('<str:out_trade_no>/status/', PaymentStatusView.as_view(), name='payment-status'),
    path('<str:out_trade_no>/mock_pay/', MockPayView.as_view(), name='payment-mock-pay'),
    path('<str:out_trade_no>/close/', ClosePaymentView.as_view(), name='payment-close'),
    path('query/', PaymentQueryView.as_view(), name='payment-query'),
    path('notify/alipay/', AliPayNotifyView.as_view(), name='alipay-notify'),
]
