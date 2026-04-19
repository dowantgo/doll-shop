from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from apps.products.models import Product, Category, ProductImage
from apps.products.cache_utils import bump_feed_version_on_commit
from apps.orders.models import Order
from .models import User
from apps.products.serializers import ProductSerializer, CategorySerializer, ProductImageSerializer
from apps.orders.serializers import AdminOrderSerializer
from .serializers import UserSerializer


class IsAdminUser(IsAuthenticated):
    """Custom permission to only allow admin users."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


class AdminStatsViewSet(viewsets.ViewSet):
    """Admin statistics."""

    permission_classes = [IsAdminUser]

    def list(self, request):
        stats = {
            'product_count': Product.objects.count(),
            'order_count': Order.objects.count(),
            'user_count': User.objects.filter(role='user').count(),
            'total_revenue': Order.objects.filter(status__in=['paid', 'shipped', 'completed']).aggregate(
                total=Sum('total_price')
            )['total'] or 0,
        }
        return Response(stats)


class AdminProductViewSet(viewsets.ModelViewSet):
    """Admin product management."""

    queryset = Product.objects.all().prefetch_related('images').order_by('-id')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        bump_feed_version_on_commit()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        bump_feed_version_on_commit()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        bump_feed_version_on_commit()

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust product inventory."""
        product = self.get_object()
        new_stock = request.data.get('stock')
        if new_stock is None or int(new_stock) < 0:
            return Response({'error': '库存值无效'}, status=status.HTTP_400_BAD_REQUEST)
        product.stock = int(new_stock)
        product.save(update_fields=['stock'])
        bump_feed_version_on_commit()
        return Response({'message': '库存调整成功', 'stock': product.stock})

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload product image for admin endpoint."""
        product = self.get_object()
        image_file = request.FILES.get('image')
        is_main = str(request.data.get('is_main', 'false')).lower() == 'true'

        if not image_file:
            return Response({'error': '请选择图片文件'}, status=status.HTTP_400_BAD_REQUEST)

        content_type = (getattr(image_file, 'content_type', '') or '').lower()
        filename = (getattr(image_file, 'name', '') or '').lower()
        allowed_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        looks_like_image = content_type.startswith('image/') or filename.endswith(allowed_ext)

        if not looks_like_image:
            return Response({'error': '只允许上传图片文件'}, status=status.HTTP_400_BAD_REQUEST)

        if is_main:
            ProductImage.objects.filter(product=product, is_main=True).update(is_main=False)

        product_image = ProductImage.objects.create(
            product=product,
            image=image_file,
            is_main=is_main,
        )
        serializer = ProductImageSerializer(product_image, context={'request': request})
        bump_feed_version_on_commit()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'delete-image/(?P<image_id>[^/.]+)')
    def delete_image(self, request, pk=None, image_id=None):
        """Delete product image for admin endpoint."""
        try:
            product_image = ProductImage.objects.get(id=image_id, product_id=pk)
        except ProductImage.DoesNotExist:
            return Response({'error': '图片不存在'}, status=status.HTTP_404_NOT_FOUND)

        if product_image.image:
            product_image.image.delete(save=False)
        product_image.delete()
        bump_feed_version_on_commit()
        return Response({'message': '图片删除成功'})

    @action(detail=True, methods=['post'], url_path=r'set-main-image/(?P<image_id>[^/.]+)')
    def set_main_image(self, request, pk=None, image_id=None):
        """Set main product image for admin endpoint."""
        try:
            product_image = ProductImage.objects.get(id=image_id, product_id=pk)
        except ProductImage.DoesNotExist:
            return Response({'error': '图片不存在'}, status=status.HTTP_404_NOT_FOUND)

        ProductImage.objects.filter(product_id=pk).update(is_main=False)
        product_image.is_main = True
        product_image.save(update_fields=['is_main'])
        bump_feed_version_on_commit()
        return Response({'message': '主图设置成功'})


class AdminCategoryViewSet(viewsets.ModelViewSet):
    """Admin category management."""

    queryset = Category.objects.all().order_by('-id')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

    @action(detail=True, methods=['get'])
    def product_count(self, request, pk=None):
        """Get the number of products in this category."""
        category = self.get_object()
        count = category.products.count()
        return Response({'category_id': category.id, 'category_name': category.name, 'product_count': count})


class AdminOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-id')
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        order = self.get_object()
        if order.payment_status != 'paid':
            return Response({'error': '只能发货已支付的订单'}, status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        order.status = 'shipped'
        order.shipping_status = 'shipped'
        order.shipped_at = timezone.now()
        order.save()
        return Response({'message': '发货成功'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status in ['shipped', 'completed', 'cancelled']:
            return Response({'error': '当前状态无法取消'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.save()
        return Response({'message': '订单已取消'})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        if order.status != 'shipped':
            return Response({'error': '订单状态不正确'}, status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        order.status = 'completed'
        order.shipping_status = 'signed'
        order.delivered_at = timezone.now()
        order.save()
        return Response({'message': '订单已完成'})


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin user management."""

    queryset = User.objects.all().order_by('-id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def set_admin(self, request, pk=None):
        """Set user as admin."""
        user = self.get_object()
        if user.role == 'admin':
            return Response({'error': '该用户已经是管理员'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = 'admin'
        user.save()
        return Response({'message': '设置成功'})

    @action(detail=True, methods=['post'])
    def set_user(self, request, pk=None):
        """Set user as normal user."""
        user = self.get_object()
        if user.role == 'user':
            return Response({'error': '该用户已经是普通用户'}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser:
            return Response({'error': '无法修改超级管理员'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = 'user'
        user.save()
        return Response({'message': '设置成功'})

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable user."""
        user = self.get_object()
        if user.is_superuser:
            return Response({'error': '无法禁用超级管理员'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save()
        return Response({'message': '用户已禁用'})

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable user."""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'message': '用户已启用'})
