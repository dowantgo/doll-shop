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
from apps.coupons.models import OrderDiscountSnapshot, UserCoupon
from apps.coupons.serializers import ApplyCouponSerializer, PricePreviewSerializer
from apps.coupons.services import (
    calc_coupon_discount,
    calc_full_reduction,
    to_money,
    validate_coupon_for_amount,
)
from apps.products.cache_utils import bump_feed_version_on_commit
from apps.products.models import Product
from apps.users.models import Address

from .models import Order
from .services.logistics import get_logistics_provider
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

        queryset = queryset.select_related(
            'address',
            'discount_snapshot',
            'discount_snapshot__user_coupon',
            'discount_snapshot__user_coupon__template',
        ).prefetch_related('items', 'items__product')

        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
            if payment_status == 'pending':
                queryset = queryset.filter(status='pending')
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _build_pricing_preview(self, *, subtotal_amount: Decimal, user_coupon: UserCoupon = None):
        subtotal_amount = to_money(subtotal_amount)
        full_reduction_amount = to_money(calc_full_reduction(subtotal_amount))
        amount_after_full_reduction = max(subtotal_amount - full_reduction_amount, Decimal('0.00'))

        coupon_discount_amount = Decimal('0.00')
        coupon_error = ''
        if user_coupon:
            valid, message = validate_coupon_for_amount(user_coupon, amount_after_full_reduction)
            if not valid:
                coupon_error = message
            else:
                coupon_discount_amount = to_money(calc_coupon_discount(user_coupon, amount_after_full_reduction))

        final_payable_amount = to_money(max(amount_after_full_reduction - coupon_discount_amount, Decimal('0.00')))
        return {
            'subtotal_amount': str(subtotal_amount),
            'full_reduction_amount': str(full_reduction_amount),
            'coupon_discount_amount': str(coupon_discount_amount),
            'final_payable_amount': str(final_payable_amount),
            'coupon_error': coupon_error,
        }

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

                    snapshot = getattr(order, 'discount_snapshot', None)
                    if snapshot and snapshot.user_coupon and snapshot.user_coupon.status == UserCoupon.STATUS_LOCKED:
                        snapshot.user_coupon.status = UserCoupon.STATUS_UNUSED
                        snapshot.user_coupon.locked_at = None
                        snapshot.user_coupon.save(update_fields=['status', 'locked_at', 'used_at'])
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

                pricing_preview = self._build_pricing_preview(subtotal_amount=total_price, user_coupon=None)
                final_payable_amount = Decimal(pricing_preview['final_payable_amount'])

                order = Order.objects.create(
                    user=request.user,
                    total_price=final_payable_amount,
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

                OrderDiscountSnapshot.objects.update_or_create(
                    order=order,
                    defaults={
                        'user_coupon': None,
                        'subtotal_amount': Decimal(pricing_preview['subtotal_amount']),
                        'full_reduction_amount': Decimal(pricing_preview['full_reduction_amount']),
                        'coupon_discount_amount': Decimal(pricing_preview['coupon_discount_amount']),
                        'final_payable_amount': Decimal(pricing_preview['final_payable_amount']),
                        'pricing_version': 'iter3-v1',
                        'pricing_snapshot': {
                            'source': 'create_from_cart',
                            **pricing_preview,
                        },
                    },
                )

            bump_feed_version_on_commit()
            serializer = OrderSerializer(order, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Order create failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='price-preview')
    def price_preview(self, request):
        serializer = PricePreviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data.get('items') or []
        coupon_id = serializer.validated_data.get('coupon_id')

        if items_data:
            product_map = {
                product.id: product
                for product in Product.objects.filter(id__in=[x['product_id'] for x in items_data], status=True)
            }
            subtotal = Decimal('0.00')
            normalized_items = []
            for row in items_data:
                product = product_map.get(row['product_id'])
                if not product:
                    return Response({'error': f'Product not found: {row["product_id"]}'}, status=status.HTTP_400_BAD_REQUEST)
                qty = int(row['quantity'])
                subtotal += product.price * qty
                normalized_items.append(
                    {
                        'product_id': product.id,
                        'name': product.name,
                        'quantity': qty,
                        'unit_price': str(to_money(product.price)),
                        'line_subtotal': str(to_money(product.price * qty)),
                    }
                )
        else:
            cart_items = list(CartItem.objects.filter(user=request.user).select_related('product'))
            if not cart_items:
                return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
            subtotal = Decimal('0.00')
            normalized_items = []
            for item in cart_items:
                subtotal += item.product.price * item.quantity
                normalized_items.append(
                    {
                        'product_id': item.product_id,
                        'name': item.product.name,
                        'quantity': int(item.quantity),
                        'unit_price': str(to_money(item.product.price)),
                        'line_subtotal': str(to_money(item.product.price * item.quantity)),
                    }
                )

        user_coupon = None
        if coupon_id:
            try:
                user_coupon = (
                    UserCoupon.objects
                    .select_related('template')
                    .get(id=coupon_id, user=request.user)
                )
            except UserCoupon.DoesNotExist:
                return Response({'error': 'Coupon not found.'}, status=status.HTTP_404_NOT_FOUND)

        pricing = self._build_pricing_preview(subtotal_amount=subtotal, user_coupon=user_coupon)
        return Response(
            {
                'items': normalized_items,
                **pricing,
                'coupon': {
                    'id': user_coupon.id,
                    'coupon_no': user_coupon.coupon_no,
                    'template_name': user_coupon.template.name,
                } if user_coupon else None,
            }
        )

    @action(detail=False, methods=['post'], url_path='(?P<order_id>[^/.]+)/apply-coupon')
    def apply_coupon(self, request, order_id=None):
        serializer = ApplyCouponSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        coupon_id = serializer.validated_data.get('coupon_id')

        with transaction.atomic():
            try:
                order = (
                    Order.objects.select_for_update()
                    .prefetch_related('items')
                    .get(order_id=order_id, user=request.user)
                )
            except Order.DoesNotExist:
                return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

            if order.payment_status != 'pending' or order.status != 'pending':
                return Response({'error': 'Only pending unpaid order can apply coupon.'}, status=status.HTTP_400_BAD_REQUEST)

            subtotal = Decimal('0.00')
            for item in order.items.all():
                subtotal += item.price * item.quantity

            snapshot = OrderDiscountSnapshot.objects.select_for_update().filter(order=order).first()
            user_coupon = None
            if coupon_id:
                try:
                    user_coupon = (
                        UserCoupon.objects.select_for_update().select_related('template')
                        .get(id=coupon_id, user=request.user)
                    )
                except UserCoupon.DoesNotExist:
                    return Response({'error': 'Coupon not found.'}, status=status.HTTP_404_NOT_FOUND)

            pricing = self._build_pricing_preview(subtotal_amount=subtotal, user_coupon=user_coupon)
            if pricing['coupon_error']:
                return Response({'error': pricing['coupon_error']}, status=status.HTTP_400_BAD_REQUEST)

            if snapshot and snapshot.user_coupon and (not user_coupon or snapshot.user_coupon_id != user_coupon.id):
                if snapshot.user_coupon.status == UserCoupon.STATUS_LOCKED:
                    snapshot.user_coupon.status = UserCoupon.STATUS_UNUSED
                    snapshot.user_coupon.locked_at = None
                    snapshot.user_coupon.save(update_fields=['status', 'locked_at', 'used_at'])

            if user_coupon:
                user_coupon.status = UserCoupon.STATUS_LOCKED
                user_coupon.locked_at = timezone.now()
                user_coupon.save(update_fields=['status', 'locked_at'])

            updated_snapshot, _ = OrderDiscountSnapshot.objects.update_or_create(
                order=order,
                defaults={
                    'user_coupon': user_coupon,
                    'subtotal_amount': Decimal(pricing['subtotal_amount']),
                    'full_reduction_amount': Decimal(pricing['full_reduction_amount']),
                    'coupon_discount_amount': Decimal(pricing['coupon_discount_amount']),
                    'final_payable_amount': Decimal(pricing['final_payable_amount']),
                    'pricing_version': 'iter3-v1',
                    'pricing_snapshot': {
                        'source': 'apply_coupon',
                        **pricing,
                    },
                },
            )

            order.total_price = updated_snapshot.final_payable_amount
            order.save(update_fields=['total_price', 'updated_at'])

        return Response(
            {
                'order_id': order.order_id,
                'coupon_id': user_coupon.id if user_coupon else None,
                'pricing': pricing,
            }
        )

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

                snapshot = getattr(order, 'discount_snapshot', None)
                if snapshot and snapshot.user_coupon and snapshot.user_coupon.status == UserCoupon.STATUS_LOCKED:
                    snapshot.user_coupon.status = UserCoupon.STATUS_UNUSED
                    snapshot.user_coupon.locked_at = None
                    snapshot.user_coupon.save(update_fields=['status', 'locked_at', 'used_at'])

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

    @action(detail=True, methods=['get'])
    def logistics(self, request, pk=None):
        order = self.get_object()
        if order.payment_status != 'paid':
            return Response(
                {
                    'order_id': order.order_id,
                    'available': False,
                    'message': 'Order has not been paid yet.',
                    'traces': [],
                }
            )

        provider = get_logistics_provider()
        result = provider.query(order)
        return Response(
            {
                'order_id': order.order_id,
                'shipping_company': order.shipping_company,
                'shipping_status': order.shipping_status,
                'tracking_no': order.tracking_no,
                'provider': result.provider,
                'available': result.available,
                'message': result.message,
                'traces': result.traces,
            }
        )
