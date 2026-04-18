from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import OrderItem
from apps.products.models import Product

from .models import Review, ReviewReply
from .sensitive_words import mask_sensitive_words, sanitize_with_feedback
from .serializers import (
    CreateReviewReplySerializer,
    CreateReviewSerializer,
    ReviewSerializer,
)


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


class ProductReviewView(APIView):
    """
    GET|POST /api/reviews/product/{id}/
    """

    pagination_class = PageNumberPagination

    def get_permissions(self):
        if self.request.method.upper() == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, id):
        product_id = id
        get_object_or_404(Product, id=product_id, status=True)
        queryset = (
            Review.objects
            .filter(product_id=product_id, status=Review.STATUS_APPROVED)
            .select_related('user', 'product')
            .prefetch_related('replies__user')
            .order_by('-created_at')
        )

        paginator = self.pagination_class()
        page_size = request.query_params.get('page_size')
        if page_size:
            try:
                paginator.page_size = min(max(int(page_size), 1), 50)
            except ValueError:
                paginator.page_size = 10

        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        product_id = id
        product = get_object_or_404(Product, id=product_id, status=True)
        create_serializer = CreateReviewSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        feedback = sanitize_with_feedback(create_serializer.validated_data['content'])

        with transaction.atomic():
            # Lock eligible order items to avoid duplicate reviews under concurrent requests.
            order_item = (
                OrderItem.objects
                .select_for_update()
                .filter(
                    order__user=request.user,
                    order__payment_status='paid',
                    product_id=product.id,
                )
                .filter(review__isnull=True)
                .order_by('created_at', 'id')
                .first()
            )
            if not order_item:
                return Response(
                    {'error': 'Only purchased products can be reviewed, and each order item can be reviewed once.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            review = Review.objects.create(
                order_item=order_item,
                product=product,
                user=request.user,
                rating=create_serializer.validated_data['rating'],
                content=feedback['sanitized_content'],
                status=Review.STATUS_APPROVED,
            )

        data = ReviewSerializer(review).data
        data.update(
            {
                'hit_sensitive_words': feedback['hit_sensitive_words'],
                'sanitized_content': feedback['sanitized_content'],
                'suggestion': feedback['suggestion'],
            }
        )
        return Response(data, status=status.HTTP_201_CREATED)


class MyReviewListView(APIView):
    """
    GET /api/reviews/my/
    """

    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        queryset = (
            Review.objects
            .filter(user=request.user)
            .select_related('user', 'product')
            .prefetch_related('replies__user')
            .order_by('-created_at')
        )
        paginator = self.pagination_class()
        page_size = request.query_params.get('page_size')
        if page_size:
            try:
                paginator.page_size = min(max(int(page_size), 1), 50)
            except ValueError:
                paginator.page_size = 10
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminReviewViewSet(ListModelMixin, viewsets.GenericViewSet):
    """
    GET /api/admin/reviews/
    PATCH /api/admin/reviews/{id}/audit/
    """

    queryset = Review.objects.select_related('user', 'product').all().order_by('-created_at')
    serializer_class = ReviewSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        params = self.request.query_params

        status_value = params.get('status')
        if status_value:
            queryset = queryset.filter(status=status_value)

        product_id = params.get('product_id')
        if product_id:
            try:
                queryset = queryset.filter(product_id=int(product_id))
            except (TypeError, ValueError):
                pass

        user_id = params.get('user_id')
        if user_id:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except (TypeError, ValueError):
                pass

        keyword = (params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(content__icontains=keyword)
                | Q(product__name__icontains=keyword)
                | Q(user__username__icontains=keyword)
            )

        return queryset

    @action(detail=True, methods=['patch'])
    def audit(self, request, pk=None):
        review = self.get_object()
        return Response(
            {
                'message': '当前版本已关闭评价审核，评价发布后直接展示。',
                'review': ReviewSerializer(review).data,
            },
            status=status.HTTP_200_OK,
        )


class ReviewReplyView(APIView):
    """
    POST /api/reviews/{id}/reply/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        review = get_object_or_404(
            Review.objects.select_related('product'),
            id=id,
            status=Review.STATUS_APPROVED,
        )
        serializer = CreateReviewReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reply = ReviewReply.objects.create(
            review=review,
            user=request.user,
            content=mask_sensitive_words(serializer.validated_data['content']),
        )

        return Response(
            {
                'id': reply.id,
                'review': review.id,
                'user_id': request.user.id,
                'user_name': request.user.username,
                'content': reply.content,
                'created_at': reply.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
