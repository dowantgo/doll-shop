from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CartItem
from .serializers import CartItemSerializer, AddToCartSerializer
from apps.products.models import Product


class CartViewSet(viewsets.ViewSet):
    """Shopping cart management"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's cart"""
        cart_items = CartItem.objects.filter(user=request.user)
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
        """Add product to cart"""
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data.get('quantity', 1)
        
        # Check product exists
        try:
            product = Product.objects.get(id=product_id, status=True)
        except Product.DoesNotExist:
            return Response({'error': '商品不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check stock
        if product.stock < quantity:
            return Response({'error': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        """Update cart item quantity"""
        cart_item_id = request.data.get('cart_item_id')
        quantity = request.data.get('quantity')
        
        if not cart_item_id or quantity is None:
            return Response({'error': '参数不完整'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)
        except CartItem.DoesNotExist:
            return Response({'error': '购物车项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        if quantity <= 0:
            cart_item.delete()
            return Response({'message': '已删除'})
        
        cart_item.quantity = quantity
        cart_item.save()
        
        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def remove(self, request):
        """Remove cart item"""
        cart_item_id = request.data.get('cart_item_id')
        
        if not cart_item_id:
            return Response({'error': '参数不完整'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)
            cart_item.delete()
            return Response({'message': '已删除'})
        except CartItem.DoesNotExist:
            return Response({'error': '购物车项目不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all cart items"""
        CartItem.objects.filter(user=request.user).delete()
        return Response({'message': '购物车已清空'})
