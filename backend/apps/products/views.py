import logging

from django.core.cache import cache
from django.db.models import Case, ExpressionWrapper, F, FloatField, Value, When
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .cache_utils import bump_feed_version_on_commit, get_feed_ttl, make_feed_cache_key
from .models import Category, InventoryLog, Product, ProductImage
from .serializers import (
    CategorySerializer,
    InventoryLogSerializer,
    ProductDetailSerializer,
    ProductFeedSerializer,
    ProductImageSerializer,
    ProductSerializer,
)

logger = logging.getLogger(__name__)


class IsAdminUser(IsAuthenticated):
    """Permission to only allow admin users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


class CategoryViewSet(viewsets.ModelViewSet):
    """Category management"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]


class ProductViewSet(viewsets.ModelViewSet):
    """Product management"""

    queryset = Product.objects.filter(status=True)
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_hot', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'sales', 'created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'hot_products', 'top_sales', 'hot_feed']:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        if self.action in ['top_sales', 'hot_feed']:
            return ProductFeedSerializer
        return ProductSerializer

    def perform_create(self, serializer):
        super().perform_create(serializer)
        bump_feed_version_on_commit()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        bump_feed_version_on_commit()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        bump_feed_version_on_commit()

    @action(detail=False, methods=['get'])
    def hot_products(self, request):
        """Get hot products"""

        hot_products = Product.objects.filter(is_hot=True, status=True).order_by('-hot_sort_order')[:10]
        serializer = ProductSerializer(hot_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='top-sales')
    def top_sales(self, request):
        """GET /api/products/products/top-sales/"""

        try:
            limit = min(max(int(request.query_params.get('limit', 10)), 1), 50)
        except ValueError:
            limit = 10

        cache_key = make_feed_cache_key('top-sales', limit)
        try:
            cached = cache.get(cache_key)
        except Exception as exc:
            cached = None
            logger.warning('top-sales cache get failed, fallback to db: %s', exc)
        if cached is not None:
            return Response(cached)

        queryset = (
            Product.objects.filter(status=True)
            .annotate(hot_score=ExpressionWrapper(F('sales') * Value(1.0), output_field=FloatField()))
            .prefetch_related('images')
            .order_by('-sales', '-created_at')[:limit]
        )
        serializer = ProductFeedSerializer(queryset, many=True, context={'request': request})
        data = serializer.data
        try:
            cache.set(cache_key, data, get_feed_ttl('top-sales'))
        except Exception as exc:
            logger.warning('top-sales cache set failed, fallback to db only: %s', exc)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='hot-feed')
    def hot_feed(self, request):
        """GET /api/products/products/hot-feed/"""

        try:
            limit = min(max(int(request.query_params.get('limit', 10)), 1), 50)
        except ValueError:
            limit = 10

        cache_key = make_feed_cache_key('hot-feed', limit)
        try:
            cached = cache.get(cache_key)
        except Exception as exc:
            cached = None
            logger.warning('hot-feed cache get failed, fallback to db: %s', exc)
        if cached is not None:
            return Response(cached)

        hot_score_expr = ExpressionWrapper(
            F('sales') * Value(1.0)
            + Case(When(is_hot=True, then=Value(20.0)), default=Value(0.0), output_field=FloatField())
            + F('hot_sort_order') * Value(0.1),
            output_field=FloatField(),
        )
        queryset = (
            Product.objects.filter(status=True)
            .annotate(hot_score=hot_score_expr)
            .prefetch_related('images')
            .order_by('-hot_score', '-sales', '-created_at')[:limit]
        )
        serializer = ProductFeedSerializer(queryset, many=True, context={'request': request})
        data = serializer.data
        try:
            cache.set(cache_key, data, get_feed_ttl('hot-feed'))
        except Exception as exc:
            logger.warning('hot-feed cache set failed, fallback to db only: %s', exc)
        return Response(data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust product stock"""

        product = self.get_object()
        quantity = request.data.get('quantity', 0)
        log_type = request.data.get('type', 'adjust')
        remark = request.data.get('remark', '')

        if not quantity:
            return Response({'error': 'Quantity cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        before_stock = product.stock
        product.stock += quantity
        if product.stock < 0:
            return Response({'error': 'Insufficient stock.'}, status=status.HTTP_400_BAD_REQUEST)

        product.save()
        bump_feed_version_on_commit()

        InventoryLog.objects.create(
            product=product,
            log_type=log_type,
            quantity=quantity,
            before_stock=before_stock,
            after_stock=product.stock,
            remark=remark,
        )

        return Response({'message': 'Stock adjusted successfully.', 'stock': product.stock})

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload product image"""

        product = self.get_object()
        image_file = request.FILES.get('image')
        is_main = request.data.get('is_main', 'false').lower() == 'true'

        if not image_file:
            return Response({'error': 'Please select an image file.'}, status=status.HTTP_400_BAD_REQUEST)

        if not image_file.content_type.startswith('image/'):
            return Response({'error': 'Only image files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

        if is_main:
            ProductImage.objects.filter(product=product, is_main=True).update(is_main=False)

        product_image = ProductImage.objects.create(product=product, image=image_file, is_main=is_main)
        serializer = ProductImageSerializer(product_image, context={'request': request})
        bump_feed_version_on_commit()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'delete-image/(\d+)')
    def delete_image(self, request, pk=None, image_id=None):
        """Delete product image"""

        try:
            product_image = ProductImage.objects.get(id=image_id, product_id=pk)
            product_image.delete()
            bump_feed_version_on_commit()
            return Response({'message': 'Image deleted successfully.'})
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path=r'set-main-image/(\d+)')
    def set_main_image(self, request, pk=None, image_id=None):
        """Set product main image"""

        try:
            product_image = ProductImage.objects.get(id=image_id, product_id=pk)
            ProductImage.objects.filter(product_id=pk).update(is_main=False)
            product_image.is_main = True
            product_image.save()
            bump_feed_version_on_commit()
            return Response({'message': 'Main image updated successfully.'})
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image not found.'}, status=status.HTTP_404_NOT_FOUND)


class InventoryLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Inventory log"""

    queryset = InventoryLog.objects.all()
    serializer_class = InventoryLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'log_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
