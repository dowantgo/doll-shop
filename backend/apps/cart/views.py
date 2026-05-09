from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.products.models import Product
from dollshop.metrics import metric_increment

from .models import CartItem
from .serializers import AddToCartSerializer, CartItemSerializer


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        cart_items = CartItem.objects.filter(user=request.user).select_related('product')
        serializer = CartItemSerializer(cart_items, many=True, context={'request': request})

        total_price = sum(item.product.price * item.quantity for item in cart_items)
        total_quantity = sum(item.quantity for item in cart_items)

        return Response({
            'items': serializer.data,
            'total_quantity': total_quantity,
            'total_price': str(total_price),
        })

    @action(detail=False, methods=['post'])
    def add(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data.get('quantity', 1)

        try:
            product = Product.objects.get(id=product_id, status=True)
        except Product.DoesNotExist:
            return Response({'error': '商品不存在'}, status=status.HTTP_404_NOT_FOUND)

        if product.stock < quantity:
            return Response({'error': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                cart_item = CartItem.objects.filter(user=request.user, product=product).first()
                if cart_item:
                    updated = (
                        CartItem.objects
                        .filter(pk=cart_item.pk, quantity__lte=product.stock - quantity)
                        .update(quantity=F('quantity') + quantity)
                    )
                    if not updated:
                        return Response({'error': '加入购物车失败，库存不足'}, status=status.HTTP_400_BAD_REQUEST)
                    cart_item.refresh_from_db()
                else:
                    try:
                        cart_item = CartItem.objects.create(user=request.user, product=product, quantity=quantity)
                    except IntegrityError:
                        updated = (
                            CartItem.objects
                            .filter(user=request.user, product=product, quantity__lte=product.stock - quantity)
                            .update(quantity=F('quantity') + quantity)
                        )
                        if not updated:
                            return Response({'error': '加入购物车失败，库存不足'}, status=status.HTTP_400_BAD_REQUEST)
                        cart_item = CartItem.objects.get(user=request.user, product=product)
        except Exception as exc:
            return Response({'error': f'加入购物车失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST)

        metric_increment('cart_add_success')
        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        cart_item_id = request.data.get('cart_item_id')
        quantity = request.data.get('quantity')

        if not cart_item_id or quantity is None:
            return Response({'error': '参数不完整'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({'error': '数量参数非法'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart_item = CartItem.objects.select_related('product').get(id=cart_item_id, user=request.user)
        except CartItem.DoesNotExist:
            return Response({'error': '购物车项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        if quantity <= 0:
            cart_item.delete()
            metric_increment('cart_remove_via_update')
            return Response({'message': '已删除'})

        if cart_item.product.stock < quantity:
            metric_increment('cart_update_rejected', reason='stock')
            return Response({'error': f'库存不足，当前最多可购买 {cart_item.product.stock} 件'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity', 'updated_at'])

        metric_increment('cart_update_success')
        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        cart_item_id = request.data.get('cart_item_id')

        if not cart_item_id:
            return Response({'error': '参数不完整'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)
            cart_item.delete()
            metric_increment('cart_remove_success')
            return Response({'message': '已删除'})
        except CartItem.DoesNotExist:
            return Response({'error': '购物车项目不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        CartItem.objects.filter(user=request.user).delete()
        metric_increment('cart_clear_success')
        return Response({'message': '购物车已清空'})
