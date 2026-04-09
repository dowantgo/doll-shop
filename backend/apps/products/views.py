from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product, ProductImage, InventoryLog
from .serializers import (CategorySerializer, ProductSerializer,
                           ProductDetailSerializer, InventoryLogSerializer,
                           ProductImageSerializer)


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
        if self.action in ['list', 'retrieve', 'hot_products']:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer

    @action(detail=False, methods=['get'])
    def hot_products(self, request):
        """Get hot products"""
        hot_products = Product.objects.filter(is_hot=True, status=True).order_by('-hot_sort_order')[:10]
        serializer = self.get_serializer(hot_products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust product stock"""
        product = self.get_object()
        quantity = request.data.get('quantity', 0)
        log_type = request.data.get('type', 'adjust')
        remark = request.data.get('remark', '')

        if not quantity:
            return Response({'error': '数量不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        before_stock = product.stock
        product.stock += quantity
        if product.stock < 0:
            return Response({'error': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)

        product.save()

        InventoryLog.objects.create(
            product=product,
            log_type=log_type,
            quantity=quantity,
            before_stock=before_stock,
            after_stock=product.stock,
            remark=remark
        )

        return Response({'message': '库存调整成功', 'stock': product.stock})

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload product image"""
        product = self.get_object()
        image_file = request.FILES.get('image')
        is_main = request.data.get('is_main', 'false').lower() == 'true'

        if not image_file:
            return Response({'error': '请选择图片文件'}, status=status.HTTP_400_BAD_REQUEST)

        if not image_file.content_type.startswith('image/'):
            return Response({'error': '只允许上传图片文件'}, status=status.HTTP_400_BAD_REQUEST)

        if is_main:
            ProductImage.objects.filter(product=product, is_main=True).update(is_main=False)

        product_image = ProductImage.objects.create(
            product=product,
            image=image_file,
            is_main=is_main
        )

        serializer = ProductImageSerializer(product_image, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'delete-image/(\d+)')
    def delete_image(self, request, pk=None, image_id=None):
        """Delete product image"""
        try:
            product_image = ProductImage.objects.get(id=image_id, product_id=pk)
            product_image.delete()
            return Response({'message': '图片删除成功'})
        except ProductImage.DoesNotExist:
            return Response({'error': '图片不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path=r'set-main-image/(\d+)')
    def set_main_image(self, request, pk=None, image_id=None):
        """Set product main image"""
        try:
            product_image = ProductImage.objects.get(id=image_id, product_id=pk)
            ProductImage.objects.filter(product_id=pk).update(is_main=False)
            product_image.is_main = True
            product_image.save()
            return Response({'message': '主图设置成功'})
        except ProductImage.DoesNotExist:
            return Response({'error': '图片不存在'}, status=status.HTTP_404_NOT_FOUND)


class InventoryLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Inventory log"""
    queryset = InventoryLog.objects.all()
    serializer_class = InventoryLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'log_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
