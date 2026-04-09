from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer, OrderItemSerializer, UpdateShippingSerializer
from apps.users.models import Address
from apps.products.models import Product
from apps.cart.models import CartItem
from decimal import Decimal


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'admin':
            queryset = Order.objects.all()
        else:
            queryset = Order.objects.filter(user=user)
        
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        self._cleanup_expired_orders()
        return super().list(request, *args, **kwargs)

    def _cleanup_expired_orders(self):
        expired_time = timezone.now() - timedelta(minutes=30)
        expired_orders = Order.objects.filter(
            payment_status='pending',
            created_at__lt=expired_time
        )
        
        for order in expired_orders:
            try:
                with transaction.atomic():
                    for item in order.items.all():
                        if item.product:
                            product = Product.objects.select_for_update().get(id=item.product.id)
                            product.stock += item.quantity
                            product.sales -= item.quantity
                            product.save()
                    order.delete()
            except Exception:
                pass

    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        address_id = serializer.validated_data['address_id']
        remark = serializer.validated_data.get('remark', '')

        cart_items = CartItem.objects.filter(user=request.user).select_related('product')
        if not cart_items.exists():
            return Response({'error': '购物车为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': '地址不存在'}, status=status.HTTP_404_NOT_FOUND)

        for item in cart_items:
            if item.product.stock < item.quantity:
                return Response(
                    {'error': f'商品"{item.product.name}"库存不足，当前库存: {item.product.stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            with transaction.atomic():
                total_price = Decimal('0.00')
                for item in cart_items:
                    total_price += item.product.price * item.quantity

                order = Order.objects.create(
                    user=request.user,
                    total_price=total_price,
                    address=address,
                    remark=remark
                )

                for item in cart_items:
                    product = Product.objects.select_for_update().get(id=item.product.id)

                    if product.stock < item.quantity:
                        raise Exception(f'商品"{product.name}"库存不足')

                    product.stock -= item.quantity
                    product.sales += item.quantity
                    product.save()

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        price=product.price
                    )

                cart_items.delete()

            serializer = OrderSerializer(order, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'订单创建失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.payment_status != 'pending':
            return Response({'error': '只能取消待支付的订单'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                for item in order.items.all():
                    if item.product:
                        product = Product.objects.select_for_update().get(id=item.product.id)
                        product.stock += item.quantity
                        product.sales -= item.quantity
                        product.save()

                order.status = 'cancelled'
                order.payment_status = 'pending'
                order.save()

            return Response({'message': '订单已取消，库存已恢复'})
        except Exception as e:
            return Response({'error': f'取消订单失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def ship(self, request, pk=None):
        order = self.get_object()

        if order.payment_status != 'paid':
            return Response({'error': '只能发货已支付的订单'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'shipped'
        order.shipping_status = 'shipped'
        order.shipped_at = timezone.now()
        order.save()

        return Response({'message': '订单已发货'})

    @action(detail=True, methods=['post'])
    def confirm_delivery(self, request, pk=None):
        order = self.get_object()

        if order.shipping_status not in ['shipped', 'in_transit', 'arrived']:
            return Response({'error': '只能确认已发货的订单'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'delivered'
        order.shipping_status = 'signed'
        order.delivered_at = timezone.now()
        order.save()

        return Response({'message': '订单已收货'})

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_shipping(self, request, pk=None):
        order = self.get_object()
        
        serializer = UpdateShippingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if 'shipping_company' in data:
            order.shipping_company = data['shipping_company']
        if 'shipping_status' in data:
            order.shipping_status = data['shipping_status']
        if 'tracking_no' in data:
            order.tracking_no = data['tracking_no']
        
        order.save()
        
        return Response(OrderSerializer(order, context={'request': request}).data)
