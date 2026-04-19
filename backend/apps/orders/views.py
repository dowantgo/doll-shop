from datetime import timedelta
from decimal import Decimal
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cart.models import CartItem
from apps.products.cache_utils import bump_feed_version_on_commit
from apps.products.models import Product
from apps.users.models import Address

from .models import Order
from .serializers import CreateOrderSerializer, OrderSerializer, UpdateShippingSerializer

logger = logging.getLogger(__name__)


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
            if payment_status == 'pending':
                queryset = queryset.filter(status='pending')
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        self._cleanup_expired_orders()
        return super().list(request, *args, **kwargs)

    def _cleanup_expired_orders(self):
        now = timezone.now()
        expired_time = now - timedelta(minutes=30)
        expired_orders = Order.objects.filter(
            payment_status='pending',
            status='pending',
        ).filter(
            Q(expires_at__lt=now) | Q(expires_at__isnull=True, created_at__lt=expired_time)
        )

        for order in expired_orders:
            has_sales_change = False
            try:
                with transaction.atomic():
                    for item in order.items.all():
                        if item.product:
                            product = Product.objects.select_for_update().get(id=item.product.id)
                            product.stock += item.quantity
                            product.sales -= item.quantity
                            product.save()
                            has_sales_change = True

                    seckill_reservation = getattr(order, 'seckill_reservation', None)
                    if seckill_reservation and seckill_reservation.status in ('reserved', 'ordered'):
                        from apps.seckill.models import SeckillActivity, SeckillReservation

                        locked_reservation = (
                            SeckillReservation.objects
                            .select_for_update()
                            .filter(id=seckill_reservation.id)
                            .first()
                        )
                        if locked_reservation and locked_reservation.status in ('reserved', 'ordered'):
                            activity = SeckillActivity.objects.select_for_update().get(id=locked_reservation.activity_id)
                            activity.reserved_stock = max(activity.reserved_stock - locked_reservation.quantity, 0)
                            activity.save(update_fields=['reserved_stock', 'updated_at'])

                            locked_reservation.status = 'expired'
                            locked_reservation.order = None
                            locked_reservation.reserved_expires_at = None
                            locked_reservation.save(
                                update_fields=['status', 'order', 'reserved_expires_at', 'updated_at']
                            )
                    order.status = 'cancelled'
                    order.save(update_fields=['status', 'updated_at'])
                if has_sales_change:
                    bump_feed_version_on_commit()
            except Exception:
                logger.exception(
                    'Failed to cleanup expired order id=%s order_id=%s created_at=%s fallback_expired_time=%s',
                    order.id,
                    order.order_id,
                    order.created_at,
                    expired_time,
                )

    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        address_id = serializer.validated_data['address_id']
        remark = serializer.validated_data.get('remark', '')

        cart_items = CartItem.objects.filter(user=request.user).select_related('product')
        if not cart_items.exists():
            return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

        for item in cart_items:
            if item.product.stock < item.quantity:
                return Response(
                    {'error': f'Insufficient stock for product "{item.product.name}".'},
                    status=status.HTTP_400_BAD_REQUEST,
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
                    remark=remark,
                )

                for item in cart_items:
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    if product.stock < item.quantity:
                        raise Exception(f'Insufficient stock for product "{product.name}".')

                    product.stock -= item.quantity
                    product.sales += item.quantity
                    product.save()

                    order.items.create(
                        product=product,
                        quantity=item.quantity,
                        price=product.price,
                    )

                cart_items.delete()

            bump_feed_version_on_commit()
            serializer = OrderSerializer(order, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Order create failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.payment_status != 'pending':
            return Response({'error': 'Only pending payment orders can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                for item in order.items.all():
                    if item.product:
                        product = Product.objects.select_for_update().get(id=item.product.id)
                        product.stock += item.quantity
                        product.sales -= item.quantity
                        product.save()

                seckill_reservation = getattr(order, 'seckill_reservation', None)
                if seckill_reservation and seckill_reservation.status in ('reserved', 'ordered'):
                    from apps.seckill.models import SeckillActivity, SeckillReservation

                    locked_reservation = (
                        SeckillReservation.objects
                        .select_for_update()
                        .filter(id=seckill_reservation.id)
                        .first()
                    )
                    if locked_reservation and locked_reservation.status in ('reserved', 'ordered'):
                        activity = SeckillActivity.objects.select_for_update().get(id=locked_reservation.activity_id)
                        activity.reserved_stock = max(activity.reserved_stock - locked_reservation.quantity, 0)
                        activity.save(update_fields=['reserved_stock', 'updated_at'])

                        locked_reservation.status = 'cancelled'
                        locked_reservation.reserved_expires_at = None
                        locked_reservation.save(update_fields=['status', 'reserved_expires_at', 'updated_at'])

                order.status = 'cancelled'
                order.payment_status = 'pending'
                order.save()

            bump_feed_version_on_commit()
            return Response({'message': 'Order cancelled and stock restored.'})
        except Exception as e:
            return Response({'error': f'Cancel order failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def ship(self, request, pk=None):
        order = self.get_object()

        if order.payment_status != 'paid':
            return Response({'error': 'Only paid orders can be shipped.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'shipped'
        order.shipping_status = 'shipped'
        order.shipped_at = timezone.now()
        order.save()

        return Response({'message': 'Order shipped.'})

    @action(detail=True, methods=['post'])
    def confirm_delivery(self, request, pk=None):
        order = self.get_object()

        if order.shipping_status not in ['shipped', 'in_transit', 'arrived']:
            return Response({'error': 'Only shipped orders can be confirmed.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'delivered'
        order.shipping_status = 'signed'
        order.delivered_at = timezone.now()
        order.save()

        return Response({'message': 'Order delivered.'})

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
