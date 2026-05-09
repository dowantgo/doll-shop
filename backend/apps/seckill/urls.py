from django.urls import path

from .views import (
    CancelSeckillReservationView,
    ExpireOrReleaseReservationView,
    MySeckillReservationsView,
    SeckillActivityListView,
    SeckillCreateOrderView,
    SeckillIssueSubmitTokenView,
    SeckillPreReserveView,
    SeckillProductActivityView,
)

urlpatterns = [
    path('activities/', SeckillActivityListView.as_view(), name='seckill-activities'),
    path('product/<int:product_id>/active/', SeckillProductActivityView.as_view(), name='seckill-product-active'),
    path('issue-submit-token/', SeckillIssueSubmitTokenView.as_view(), name='seckill-issue-submit-token'),
    path('pre-reserve/', SeckillPreReserveView.as_view(), name='seckill-pre-reserve'),
    path('create-order/', SeckillCreateOrderView.as_view(), name='seckill-create-order'),
    path('my-reservations/', MySeckillReservationsView.as_view(), name='seckill-my-reservations'),
    path('reservations/<int:id>/cancel/', CancelSeckillReservationView.as_view(), name='seckill-cancel-reservation'),
    path('reservations/<int:id>/expire-or-release/', ExpireOrReleaseReservationView.as_view(), name='seckill-expire-or-release'),
]
