from django.urls import path

from .views import MyReviewListView, ProductReviewView, ReviewReplyView

urlpatterns = [
    path('product/<int:id>/', ProductReviewView.as_view(), name='product-reviews'),
    path('my/', MyReviewListView.as_view(), name='my-reviews'),
    path('<int:id>/reply/', ReviewReplyView.as_view(), name='review-reply'),
]
