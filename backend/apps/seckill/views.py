from datetime import timedelta
from decimal import Decimal
import logging

from django.conf import settings
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
from apps.users.security import get_client_ip
from apps.users.models import Address
from dollshop.metrics import metric_increment

from .guardrails import check_pre_reserve_limits
from .models import SeckillActivity, SeckillReservation
from .redis_flow import (
    SECKILL_SUBMIT_TOKEN_TTL_SECONDS,
    acquire_create_order_lock,
    clear_reservation_ticket,
    consume_submit_token,
    ensure_activity_stock_bucket,
    get_activity_remaining_stock,
    get_cached_reservation_token,
    hold_stock_and_create_ticket,
    issue_submit_token,
    load_reservation_ticket,
    pop_expired_reservation_tokens,
    release_create_order_lock,
    restore_stock_from_db,
    restore_stock_from_ticket,
    sync_activity_stock_bucket,
)
from .serializers import (
    SeckillActivitySerializer,
    SeckillCreateOrderSerializer,
    SeckillIssueSubmitTokenSerializer,
    SeckillPreReserveSerializer,
    SeckillReservationSerializer,
)

logger = logging.getLogger(__name__)


def _reserve_expire_minutes():
    raw = getattr(settings, 'SECKILL_RESERVATION_EXPIRE_MINUTES', 10)
    try:
        return max(int(raw), 1)
    except (TypeError, ValueError):
        return 10


def _reserve_expire_seconds():
    return _reserve_expire_minutes() * 60


def _serialize_ticket_payload(ticket: dict, *, activity=None, product=None):
    expires_at = ticket.get('expires_at')
    return {
        'id': None,
        'activity_id': int(ticket.get('activity_id', 0) or 0),
        'product_id': int(ticket.get('product_id', 0) or 0),
        'product_name': product.name if product else '',
        'user_id': int(ticket.get('user_id', 0) or 0),
        'activity_name': activity.name if activity else '',
        'quantity': int(ticket.get('quantity', 1) or 1),
        'status': ticket.get('status') or SeckillReservation.STATUS_RESERVED,
        'idempotency_key': ticket.get('idempotency_key') or '',
        'reservation_token': ticket.get('reservation_token') or '',
        'order_id': '',
        'reserved_expires_at': expires_at,
        'created_at': ticket.get('created_at') or timezone.now().isoformat(),
    }


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
        restore_stock_from_db(activity.id, release_qty, reason=new_status)

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
    released_ticket_count = 0
    for reservation_token in pop_expired_reservation_tokens():
        if restore_stock_from_ticket(reservation_token, reason='expired'):
            released_ticket_count += 1

    expired_ids = list(
        SeckillReservation.objects.filter(
            status=SeckillReservation.STATUS_RESERVED,
            reserved_expires_at__isnull=False,
            reserved_expires_at__lte=now,
        ).values_list('id', flat=True)
    )

    released_db_count = 0
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
            released_db_count += 1

    summary = {
        'released_ticket_count': released_ticket_count,
        'released_db_count': released_db_count,
    }
    if released_ticket_count or released_db_count:
        logger.info('cleanup_expired_seckill_reservations_summary %s', summary)
    return summary


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


class SeckillIssueSubmitTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = SeckillIssueSubmitTokenSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        activity_id = payload.validated_data['activity_id']
        now = timezone.now()
        activity = (
            SeckillActivity.objects
            .select_related('product')
            .filter(
                id=activity_id,
                status=SeckillActivity.STATUS_ONLINE,
                is_enabled=True,
                start_at__lte=now,
                end_at__gte=now,
                product__status=True,
            )
            .first()
        )
        if not activity:
            return Response({'error': 'Activity not found or unavailable.'}, status=status.HTTP_404_NOT_FOUND)

        ensure_activity_stock_bucket(activity_id=activity.id, fallback_remaining=activity.remaining_stock)
        submit_token = issue_submit_token(user_id=request.user.id, activity_id=activity.id)
        metric_increment('seckill_submit_token_issued')
        return Response(
            {
                'activity_id': activity.id,
                'submit_token': submit_token,
                'expires_in_seconds': SECKILL_SUBMIT_TOKEN_TTL_SECONDS,
            }
        )


class SeckillActivityListView(APIView):
    """
    GET /api/seckill/activities/
    """

    permission_classes = [AllowAny]

    def get(self, request):
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
        for activity in queryset:
            ensure_activity_stock_bucket(activity_id=activity.id, fallback_remaining=activity.remaining_stock)
        return Response(build_activity_groups(queryset, request))


class SeckillProductActivityView(APIView):
    """
    GET /api/seckill/product/{product_id}/active/
    """

    permission_classes = [AllowAny]

    def get(self, request, product_id):
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

        ensure_activity_stock_bucket(activity_id=activity.id, fallback_remaining=activity.remaining_stock)
        serializer = SeckillActivitySerializer(activity, context={'request': request})
        return Response(serializer.data)


class SeckillPreReserveView(APIView):
    """
    POST /api/seckill/pre-reserve/
    Reserve quota and stock first, then order can be created from reservation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = SeckillPreReserveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        activity_id = payload.validated_data['activity_id']
        quantity = payload.validated_data['quantity']
        submit_token = payload.validated_data['submit_token']
        idempotency_key = (request.headers.get('X-Idempotency-Key') or '').strip()

        if idempotency_key:
            cached_token = get_cached_reservation_token(user_id=request.user.id, idempotency_key=idempotency_key)
            if cached_token:
                cached_ticket = load_reservation_ticket(cached_token)
                if cached_ticket:
                    activity = SeckillActivity.objects.select_related('product').filter(id=activity_id).first()
                    product = activity.product if activity else None
                    return Response(
                        {
                            'message': 'Idempotent replay, returning existing reservation.',
                            'order_created': False,
                            'payment_triggered': False,
                            'data': _serialize_ticket_payload(cached_ticket, activity=activity, product=product),
                        },
                        status=status.HTTP_200_OK,
                    )

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

        allowed, throttle_message = check_pre_reserve_limits(
            user_id=request.user.id,
            ip=get_client_ip(request),
            activity_id=activity_id,
        )
        if not allowed:
            logger.warning(
                'seckill_pre_reserve_rate_limited user_id=%s activity_id=%s',
                request.user.id,
                activity_id,
            )
            return Response({'error': throttle_message}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        now = timezone.now()
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

            if not consume_submit_token(user_id=request.user.id, activity_id=activity.id, submit_token=submit_token):
                return Response({'error': '秒杀令牌已失效，请重新发起秒杀。'}, status=status.HTTP_400_BAD_REQUEST)

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
            ensure_activity_stock_bucket(activity_id=activity.id, fallback_remaining=activity.remaining_stock)
            held, ticket, remaining_stock = hold_stock_and_create_ticket(
                user_id=request.user.id,
                activity_id=activity.id,
                product_id=activity.product_id,
                quantity=quantity,
                idempotency_key=idempotency_key,
            )
            if not held:
                if remaining_stock < 0:
                    sync_activity_stock_bucket(activity_id=activity.id, remaining_stock=activity.remaining_stock)
                    return Response({'error': '秒杀库存同步中，请稍后再试。'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                return Response({'error': 'Insufficient reservation stock.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'message': 'Pre-reserve succeeded. Create order before reservation expires.',
                'order_created': False,
                'payment_triggered': False,
                'data': _serialize_ticket_payload(ticket, activity=activity, product=activity.product),
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
        payload = SeckillCreateOrderSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        reservation_id = payload.validated_data.get('reservation_id')
        reservation_token = (payload.validated_data.get('reservation_token') or '').strip()
        address_id = payload.validated_data['address_id']
        remark = payload.validated_data.get('remark', '').strip()

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

        if reservation_token:
            guard_acquired = acquire_create_order_lock(reservation_token)
            if not guard_acquired:
                return Response({'error': '秒杀订单正在处理中，请稍后刷新结果。'}, status=status.HTTP_409_CONFLICT)
        else:
            guard_acquired = False

        now = timezone.now()

        try:
            with transaction.atomic():
                reservation = None
                ticket = None

                if reservation_token:
                    reservation = (
                        SeckillReservation.objects
                        .select_for_update()
                        .select_related('activity', 'product', 'order')
                        .filter(reservation_token=reservation_token, user=request.user)
                        .first()
                    )
                    if not reservation:
                        ticket = load_reservation_ticket(reservation_token)
                        if not ticket:
                            return Response({'error': 'Reservation expired. Please reserve again.'}, status=status.HTTP_400_BAD_REQUEST)
                        if int(ticket.get('user_id') or 0) != request.user.id:
                            return Response({'error': 'Reservation not found.'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    reservation = (
                        SeckillReservation.objects
                        .select_for_update()
                        .select_related('activity', 'product', 'order')
                        .filter(id=reservation_id, user=request.user)
                        .first()
                    )
                    if not reservation:
                        return Response({'error': 'Reservation not found.'}, status=status.HTTP_404_NOT_FOUND)

                if reservation and reservation.status in [SeckillReservation.STATUS_ORDERED, SeckillReservation.STATUS_PAID] and reservation.order:
                    serializer = OrderSerializer(reservation.order, context={'request': request})
                    return Response(
                        {
                            'message': 'Order already created from this reservation.',
                            'data': serializer.data,
                            'reservation': SeckillReservationSerializer(reservation).data,
                        },
                        status=status.HTTP_200_OK,
                    )

                if reservation:
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
                    product = Product.objects.select_for_update().get(id=reservation.product_id)
                    quantity = reservation.quantity
                else:
                    activity = (
                        SeckillActivity.objects
                        .select_for_update()
                        .select_related('product')
                        .filter(id=int(ticket['activity_id']))
                        .first()
                    )
                    if not activity:
                        restore_stock_from_ticket(reservation_token, reason='activity_missing')
                        return Response({'error': 'Activity not found or unavailable.'}, status=status.HTTP_404_NOT_FOUND)
                    product = Product.objects.select_for_update().get(id=activity.product_id)
                    quantity = int(ticket['quantity'])
                    if product.stock < quantity:
                        restore_stock_from_ticket(reservation_token, reason='db_stock_insufficient')
                        return Response({'error': 'Product stock is insufficient for reservation.'}, status=status.HTTP_400_BAD_REQUEST)

                if activity.status != SeckillActivity.STATUS_ONLINE or not activity.is_enabled or not (activity.start_at <= now <= activity.end_at):
                    if reservation:
                        _release_reservation_quota(
                            reservation,
                            new_status=SeckillReservation.STATUS_CANCELLED,
                            restore_product_stock=True,
                        )
                    else:
                        restore_stock_from_ticket(reservation_token, reason='activity_offline')
                    return Response({'error': 'Activity is offline. Reservation has been released.'}, status=status.HTTP_400_BAD_REQUEST)

                if not reservation:
                    reservation = SeckillReservation.objects.create(
                        activity=activity,
                        product=activity.product,
                        user=request.user,
                        quantity=quantity,
                        status=SeckillReservation.STATUS_RESERVED,
                        idempotency_key=(ticket.get('idempotency_key') or None),
                        reservation_token=reservation_token,
                        reserved_expires_at=now + timedelta(minutes=_reserve_expire_minutes()),
                    )
                    activity.reserved_stock += quantity
                    activity.save(update_fields=['reserved_stock', 'updated_at'])
                    product.stock -= quantity
                    product.save(update_fields=['stock', 'updated_at'])

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

                product.sales += reservation.quantity
                product.save(update_fields=['sales', 'updated_at'])

                reservation.status = SeckillReservation.STATUS_ORDERED
                reservation.order = order
                reservation.reserved_expires_at = order.expires_at
                if reservation_token and not reservation.reservation_token:
                    reservation.reservation_token = reservation_token
                reservation.save(update_fields=['status', 'order', 'reserved_expires_at', 'reservation_token', 'updated_at'])

            if reservation_token:
                clear_reservation_ticket(reservation_token)
        finally:
            if guard_acquired:
                release_create_order_lock(reservation_token)

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
