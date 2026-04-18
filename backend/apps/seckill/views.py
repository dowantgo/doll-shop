from datetime import timedelta
from decimal import Decimal
import time

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.products.cache_utils import bump_feed_version_on_commit
from apps.products.models import Product
from apps.users.models import Address

from .models import SeckillActivity, SeckillReservation
from .serializers import (
    SeckillActivitySerializer,
    SeckillCreateOrderSerializer,
    SeckillPreReserveSerializer,
    SeckillReservationSerializer,
)


def check_rate_limit(request, scope='seckill_pre_reserve', limit=60, window_seconds=60):
    """
    Lightweight rate-limit utility based on cache.
    """
    user_tag = f"user:{request.user.id}" if request.user.is_authenticated else f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"
    window_slot = int(time.time() // window_seconds)
    cache_key = f"ratelimit:{scope}:{user_tag}:{window_slot}"
    current = cache.get(cache_key, 0)

    if current >= limit:
        return Response(
            {'error': 'Too many requests, please retry later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if current == 0:
        cache.set(cache_key, 1, timeout=window_seconds)
    else:
        try:
            cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, current + 1, timeout=window_seconds)
    return None


def _reserve_expire_minutes():
    raw = getattr(settings, 'SECKILL_RESERVATION_EXPIRE_MINUTES', 10)
    try:
        return max(int(raw), 1)
    except (TypeError, ValueError):
        return 10


def _release_reservation_quota(reservation, new_status, restore_product_stock):
    """
    Release reserved quota and optionally restore product stock.
    Must be called inside a transaction with reservation locked.
    """
    activity = SeckillActivity.objects.select_for_update().get(id=reservation.activity_id)
    release_qty = reservation.quantity
    if activity.reserved_stock >= release_qty:
        activity.reserved_stock -= release_qty
    else:
        activity.reserved_stock = 0
    activity.save(update_fields=['reserved_stock', 'updated_at'])

    if restore_product_stock:
        product = Product.objects.select_for_update().get(id=reservation.product_id)
        product.stock += release_qty
        product.save(update_fields=['stock', 'updated_at'])

    reservation.status = new_status
    reservation.reserved_expires_at = None
    reservation.save(update_fields=['status', 'reserved_expires_at', 'updated_at'])


def _get_release_target_status(reservation, now=None):
    now = now or timezone.now()

    if reservation.status == SeckillReservation.STATUS_RESERVED:
        if reservation.reserved_expires_at and reservation.reserved_expires_at <= now:
            return SeckillReservation.STATUS_EXPIRED
        return SeckillReservation.STATUS_CANCELLED

    if reservation.status == SeckillReservation.STATUS_ORDERED:
        # Ordered reservations should be released through order-timeout/cancel flow.
        # If no order is bound (dirty legacy row), allow safe release.
        if not reservation.order_id:
            return SeckillReservation.STATUS_CANCELLED
        return None

    return None


def _reservation_is_paid(reservation):
    if reservation.status == SeckillReservation.STATUS_PAID:
        return True

    order = getattr(reservation, 'order', None)
    if order and getattr(order, 'payment_status', None) == 'paid':
        return True
    return False


def cleanup_expired_reservations():
    now = timezone.now()
    expired_ids = list(
        SeckillReservation.objects.filter(
            status=SeckillReservation.STATUS_RESERVED,
            reserved_expires_at__isnull=False,
            reserved_expires_at__lte=now,
        ).values_list('id', flat=True)
    )

    for reservation_id in expired_ids:
        with transaction.atomic():
            reservation = (
                SeckillReservation.objects
                .select_for_update()
                .filter(id=reservation_id)
                .first()
            )
            if not reservation:
                continue
            if reservation.status != SeckillReservation.STATUS_RESERVED:
                continue
            if not reservation.reserved_expires_at or reservation.reserved_expires_at > now:
                continue
            _release_reservation_quota(
                reservation,
                new_status=SeckillReservation.STATUS_EXPIRED,
                restore_product_stock=True,
            )


def build_activity_groups(queryset, request):
    """
    Build grouped response so one activity group can carry multiple products.
    """
    groups = {}
    for activity in queryset:
        item = SeckillActivitySerializer(activity, context={'request': request}).data
        key = activity.group_id or str(activity.id)
        if key not in groups:
            groups[key] = {
                'group_id': key,
                'name': activity.name,
                'status': activity.status,
                'is_enabled': activity.is_enabled,
                'start_at': activity.start_at.isoformat() if activity.start_at else None,
                'end_at': activity.end_at.isoformat() if activity.end_at else None,
                'items': [],
            }
        groups[key]['items'].append(item)
    return list(groups.values())


class SeckillActivityListView(APIView):
    """
    GET /api/seckill/activities/
    """

    permission_classes = [AllowAny]

    def get(self, request):
        cleanup_expired_reservations()
        now = timezone.now()
        queryset = (
            SeckillActivity.objects
            .select_related('product')
            .filter(is_enabled=True, product__status=True)
            .filter(
                Q(status=SeckillActivity.STATUS_PREHEATING, start_at__gt=now)
                | Q(status=SeckillActivity.STATUS_ONLINE, start_at__lte=now, end_at__gte=now)
            )
            .order_by('start_at', '-created_at')
        )
        return Response(build_activity_groups(queryset, request))


class SeckillProductActivityView(APIView):
    """
    GET /api/seckill/product/{product_id}/active/
    """

    permission_classes = [AllowAny]

    def get(self, request, product_id):
        cleanup_expired_reservations()
        now = timezone.now()
        activity = (
            SeckillActivity.objects
            .select_related('product')
            .filter(
                product_id=product_id,
                status=SeckillActivity.STATUS_ONLINE,
                is_enabled=True,
                start_at__lte=now,
                end_at__gte=now,
                product__status=True,
            )
            .order_by('-created_at')
            .first()
        )
        if not activity:
            return Response({'error': 'No active seckill for this product.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SeckillActivitySerializer(activity, context={'request': request})
        return Response(serializer.data)


class SeckillPreReserveView(APIView):
    """
    POST /api/seckill/pre-reserve/
    Reserve quota and stock first, then order can be created from reservation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        cleanup_expired_reservations()

        limited = check_rate_limit(request)
        if limited is not None:
            return limited

        payload = SeckillPreReserveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        activity_id = payload.validated_data['activity_id']
        quantity = payload.validated_data['quantity']
        idempotency_key = (request.headers.get('X-Idempotency-Key') or '').strip()

        if idempotency_key:
            existing = (
                SeckillReservation.objects
                .select_related('activity', 'product', 'user', 'order')
                .filter(user=request.user, idempotency_key=idempotency_key)
                .order_by('-id')
                .first()
            )
            if existing:
                return Response(
                    {
                        'message': 'Idempotent replay, returning existing reservation.',
                        'order_created': bool(existing.order_id),
                        'payment_triggered': False,
                        'data': SeckillReservationSerializer(existing).data,
                    },
                    status=status.HTTP_200_OK,
                )

        now = timezone.now()
        expires_at = now + timedelta(minutes=_reserve_expire_minutes())

        with transaction.atomic():
            activity = (
                SeckillActivity.objects
                .select_for_update()
                .select_related('product')
                .filter(
                    id=activity_id,
                    status=SeckillActivity.STATUS_ONLINE,
                    is_enabled=True,
                    product__status=True,
                )
                .first()
            )
            if not activity:
                return Response({'error': 'Activity not found or unavailable.'}, status=status.HTTP_404_NOT_FOUND)

            if not (activity.start_at <= now <= activity.end_at):
                return Response({'error': 'Activity is not in active time window.'}, status=status.HTTP_400_BAD_REQUEST)

            user_reserved = (
                SeckillReservation.objects
                .filter(
                    activity=activity,
                    user=request.user,
                    status__in=[
                        SeckillReservation.STATUS_RESERVED,
                        SeckillReservation.STATUS_ORDERED,
                        SeckillReservation.STATUS_PAID,
                    ],
                )
                .aggregate(total=Sum('quantity'))
                .get('total')
                or 0
            )
            if user_reserved + quantity > activity.per_user_limit:
                return Response(
                    {'error': f'超出限购数量：该商品每人限购 {activity.per_user_limit} 件。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity > activity.remaining_stock:
                return Response({'error': 'Insufficient reservation stock.'}, status=status.HTTP_400_BAD_REQUEST)

            product = Product.objects.select_for_update().get(id=activity.product_id)
            if product.stock < quantity:
                return Response({'error': 'Product stock is insufficient for reservation.'}, status=status.HTTP_400_BAD_REQUEST)

            reservation = SeckillReservation.objects.create(
                activity=activity,
                product=activity.product,
                user=request.user,
                quantity=quantity,
                status=SeckillReservation.STATUS_RESERVED,
                idempotency_key=idempotency_key or None,
                reserved_expires_at=expires_at,
            )
            activity.reserved_stock += quantity
            activity.save(update_fields=['reserved_stock', 'updated_at'])

            product.stock -= quantity
            product.save(update_fields=['stock', 'updated_at'])

        if idempotency_key:
            cache_key = f"seckill:idempotency:{request.user.id}:{idempotency_key}"
            cache.set(cache_key, reservation.id, timeout=3600)

        return Response(
            {
                'message': 'Pre-reserve succeeded. Create order before reservation expires.',
                'order_created': False,
                'payment_triggered': False,
                'data': SeckillReservationSerializer(reservation).data,
            },
            status=status.HTTP_201_CREATED,
        )


class SeckillCreateOrderView(APIView):
    """
    POST /api/seckill/create-order/
    Create a normal pending order from a reserved seckill quota.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        cleanup_expired_reservations()

        payload = SeckillCreateOrderSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        reservation_id = payload.validated_data['reservation_id']
        address_id = payload.validated_data['address_id']
        remark = payload.validated_data.get('remark', '').strip()

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()

        with transaction.atomic():
            reservation = (
                SeckillReservation.objects
                .select_for_update()
                .select_related('activity', 'product', 'order')
                .filter(id=reservation_id, user=request.user)
                .first()
            )
            if not reservation:
                return Response({'error': 'Reservation not found.'}, status=status.HTTP_404_NOT_FOUND)

            if reservation.status in [SeckillReservation.STATUS_ORDERED, SeckillReservation.STATUS_PAID] and reservation.order:
                serializer = OrderSerializer(reservation.order, context={'request': request})
                return Response(
                    {
                        'message': 'Order already created from this reservation.',
                        'data': serializer.data,
                        'reservation': SeckillReservationSerializer(reservation).data,
                    },
                    status=status.HTTP_200_OK,
                )

            if reservation.status != SeckillReservation.STATUS_RESERVED:
                return Response({'error': 'Reservation is not available for order creation.'}, status=status.HTTP_400_BAD_REQUEST)

            if reservation.reserved_expires_at and reservation.reserved_expires_at <= now:
                _release_reservation_quota(
                    reservation,
                    new_status=SeckillReservation.STATUS_EXPIRED,
                    restore_product_stock=True,
                )
                return Response({'error': 'Reservation expired. Please reserve again.'}, status=status.HTTP_400_BAD_REQUEST)

            activity = SeckillActivity.objects.select_for_update().get(id=reservation.activity_id)
            if activity.status != SeckillActivity.STATUS_ONLINE or not activity.is_enabled:
                _release_reservation_quota(
                    reservation,
                    new_status=SeckillReservation.STATUS_CANCELLED,
                    restore_product_stock=True,
                )
                return Response({'error': 'Activity is offline. Reservation has been released.'}, status=status.HTTP_400_BAD_REQUEST)

            total_price = Decimal(activity.seckill_price) * reservation.quantity
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                address=address,
                remark=remark or f'[SECKILL]{activity.name}',
            )
            order.items.create(
                product=reservation.product,
                quantity=reservation.quantity,
                price=activity.seckill_price,
            )

            product = Product.objects.select_for_update().get(id=reservation.product_id)
            product.sales += reservation.quantity
            product.save(update_fields=['sales', 'updated_at'])

            reservation.status = SeckillReservation.STATUS_ORDERED
            reservation.order = order
            reservation.reserved_expires_at = order.expires_at
            reservation.save(update_fields=['status', 'order', 'reserved_expires_at', 'updated_at'])

        bump_feed_version_on_commit()
        serializer = OrderSerializer(order, context={'request': request})
        return Response(
            {
                'message': 'Seckill order created successfully. You can proceed to payment.',
                'data': serializer.data,
                'reservation': SeckillReservationSerializer(reservation).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MySeckillReservationsView(APIView):
    """
    GET /api/seckill/my-reservations/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cleanup_expired_reservations()
        queryset = (
            SeckillReservation.objects
            .select_related('activity', 'product', 'order')
            .filter(user=request.user)
            .order_by('-created_at')[:50]
        )
        serializer = SeckillReservationSerializer(queryset, many=True)
        return Response(serializer.data)


class CancelSeckillReservationView(APIView):
    """
    POST /api/seckill/reservations/{id}/cancel/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        cleanup_expired_reservations()

        with transaction.atomic():
            reservation = get_object_or_404(
                SeckillReservation.objects.select_for_update(),
                id=id,
                user=request.user,
            )

            if reservation.status != SeckillReservation.STATUS_RESERVED:
                return Response({'error': 'Only reserved reservations can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

            _release_reservation_quota(
                reservation,
                new_status=SeckillReservation.STATUS_CANCELLED,
                restore_product_stock=True,
            )

        return Response({'message': 'Reservation cancelled and stock released.'})


class ExpireOrReleaseReservationView(APIView):
    """
    POST /api/seckill/reservations/{id}/expire-or-release/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        cleanup_expired_reservations()
        now = timezone.now()
        is_admin = getattr(request.user, 'role', '') == 'admin'

        with transaction.atomic():
            reservation = (
                SeckillReservation.objects
                .select_for_update()
                .select_related('activity', 'product', 'user', 'order')
                .filter(id=id)
                .first()
            )
            if not reservation:
                return Response({'error': 'Reservation not found.'}, status=status.HTTP_404_NOT_FOUND)

            if not is_admin and reservation.user_id != request.user.id:
                return Response({'error': 'You do not have permission to operate this reservation.'}, status=status.HTTP_403_FORBIDDEN)

            if _reservation_is_paid(reservation):
                return Response(
                    {
                        'message': 'Reservation is already paid and cannot be released.',
                        'released': False,
                        'current_status': reservation.status,
                        'data': SeckillReservationSerializer(reservation).data,
                    },
                    status=status.HTTP_200_OK,
                )

            target_status = _get_release_target_status(reservation, now=now)
            if target_status is None:
                return Response(
                    {
                        'message': 'Reservation is already released or bound to an order and cannot be released directly.',
                        'released': False,
                        'current_status': reservation.status,
                        'data': SeckillReservationSerializer(reservation).data,
                    },
                    status=status.HTTP_200_OK,
                )

            before_status = reservation.status
            _release_reservation_quota(
                reservation,
                new_status=target_status,
                restore_product_stock=True,
            )
            reservation.refresh_from_db()

        return Response(
            {
                'message': 'Reservation released successfully.',
                'released': True,
                'previous_status': before_status,
                'current_status': reservation.status,
                'data': SeckillReservationSerializer(reservation).data,
            },
            status=status.HTTP_200_OK,
        )
