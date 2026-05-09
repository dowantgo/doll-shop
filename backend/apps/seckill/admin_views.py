import uuid

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SeckillActivity, SeckillAdminActionLog, SeckillReservation
from .redis_flow import drop_activity_stock_bucket, sync_activity_stock_bucket
from .serializers import (
    AdminSeckillActionLogSerializer,
    AdminSeckillActivitySerializer,
    AdminSeckillReservationSerializer,
    AdjustSeckillPriceSerializer,
    AdjustSeckillStockSerializer,
    ChangeSeckillStatusSerializer,
    ReleaseReservationSerializer,
)
from .views import _get_release_target_status, _release_reservation_quota, _reservation_is_paid


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


def _snapshot_activity(activity):
    return {
        'id': activity.id,
        'group_id': activity.group_id,
        'name': activity.name,
        'product_id': activity.product_id,
        'seckill_price': str(activity.seckill_price),
        'total_stock': activity.total_stock,
        'reserved_stock': activity.reserved_stock,
        'remaining_stock': activity.remaining_stock,
        'per_user_limit': activity.per_user_limit,
        'status': activity.status,
        'is_enabled': activity.is_enabled,
        'start_at': activity.start_at.isoformat() if activity.start_at else None,
        'end_at': activity.end_at.isoformat() if activity.end_at else None,
    }


def _snapshot_reservation(reservation):
    return {
        'id': reservation.id,
        'activity_id': reservation.activity_id,
        'activity_group_id': reservation.activity.group_id if reservation.activity_id else '',
        'product_id': reservation.product_id,
        'user_id': reservation.user_id,
        'quantity': reservation.quantity,
        'status': reservation.status,
        'order_id': reservation.order.order_id if reservation.order else None,
        'reserved_expires_at': reservation.reserved_expires_at.isoformat() if reservation.reserved_expires_at else None,
    }


def _log_action(*, operator, action_type, activity=None, reservation=None, before_data=None, after_data=None, remark=''):
    SeckillAdminActionLog.objects.create(
        operator=operator,
        activity=activity,
        reservation=reservation,
        action_type=action_type,
        before_data=before_data or {},
        after_data=after_data or {},
        remark=remark or '',
    )


class AdminSeckillStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        total_activities = SeckillActivity.objects.count()
        online_activities = SeckillActivity.objects.filter(status=SeckillActivity.STATUS_ONLINE, is_enabled=True).count()

        reservation_stats = {
            item['status']: item['count']
            for item in SeckillReservation.objects.values('status').annotate(count=Count('id'))
        }
        total_reservations = sum(reservation_stats.values())
        paid_count = reservation_stats.get(SeckillReservation.STATUS_PAID, 0)

        total_stock = SeckillActivity.objects.aggregate(v=Sum('total_stock'))['v'] or 0
        reserved_stock = SeckillActivity.objects.aggregate(v=Sum('reserved_stock'))['v'] or 0

        return Response(
            {
                'activity_total': total_activities,
                'activity_online': online_activities,
                'reservation_total': total_reservations,
                'reservation_reserved': reservation_stats.get(SeckillReservation.STATUS_RESERVED, 0),
                'reservation_ordered': reservation_stats.get(SeckillReservation.STATUS_ORDERED, 0),
                'reservation_paid': paid_count,
                'reservation_cancelled': reservation_stats.get(SeckillReservation.STATUS_CANCELLED, 0),
                'reservation_expired': reservation_stats.get(SeckillReservation.STATUS_EXPIRED, 0),
                'stock_total': total_stock,
                'stock_reserved': reserved_stock,
                'stock_remaining': max(total_stock - reserved_stock, 0),
                'paid_conversion_rate': round((paid_count / total_reservations * 100), 2) if total_reservations else 0,
            }
        )


class AdminSeckillActivityViewSet(viewsets.ModelViewSet):
    queryset = SeckillActivity.objects.select_related('product').all().order_by('-id')
    serializer_class = AdminSeckillActivitySerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        status_value = (self.request.query_params.get('status') or '').strip()
        if status_value:
            queryset = queryset.filter(status=status_value)

        product_id = self.request.query_params.get('product_id')
        if product_id:
            try:
                queryset = queryset.filter(product_id=int(product_id))
            except (TypeError, ValueError):
                pass

        keyword = (self.request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(product__name__icontains=keyword))

        return queryset

    def create(self, request, *args, **kwargs):
        """
        If request includes products[], create one activity group with multiple products.
        """
        products = request.data.get('products')
        if products is None:
            return super().create(request, *args, **kwargs)

        if isinstance(products, str):
            raw = [x.strip() for x in products.split(',') if x.strip()]
        elif isinstance(products, (list, tuple)):
            raw = list(products)
        else:
            return Response({'error': 'products 参数格式错误'}, status=status.HTTP_400_BAD_REQUEST)

        product_ids = []
        for item in raw:
            try:
                product_ids.append(int(item))
            except (TypeError, ValueError):
                return Response({'error': f'无效商品ID: {item}'}, status=status.HTTP_400_BAD_REQUEST)
        product_ids = list(dict.fromkeys(product_ids))
        if not product_ids:
            return Response({'error': '请至少选择一个商品'}, status=status.HTTP_400_BAD_REQUEST)

        group_id = str(uuid.uuid4())
        base_payload = dict(request.data)
        base_payload.pop('products', None)
        base_payload['group_id'] = group_id

        created = []
        with transaction.atomic():
            for pid in product_ids:
                payload = dict(base_payload)
                payload['product'] = pid
                serializer = self.get_serializer(data=payload)
                serializer.is_valid(raise_exception=True)
                activity = serializer.save()
                _log_action(
                    operator=request.user,
                    action_type=SeckillAdminActionLog.ACTION_CREATE_ACTIVITY,
                    activity=activity,
                    after_data=_snapshot_activity(activity),
                    remark='Create seckill activity (batch)',
                )
                sync_activity_stock_bucket(activity_id=activity.id, remaining_stock=activity.remaining_stock)
                created.append(self.get_serializer(activity).data)

        return Response({'group_id': group_id, 'count': len(created), 'results': created}, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        activity = serializer.save()
        sync_activity_stock_bucket(activity_id=activity.id, remaining_stock=activity.remaining_stock)
        _log_action(
            operator=self.request.user,
            action_type=SeckillAdminActionLog.ACTION_CREATE_ACTIVITY,
            activity=activity,
            after_data=_snapshot_activity(activity),
            remark='Create seckill activity',
        )

    def perform_update(self, serializer):
        before = _snapshot_activity(self.get_object())
        activity = serializer.save()
        sync_activity_stock_bucket(activity_id=activity.id, remaining_stock=activity.remaining_stock)
        _log_action(
            operator=self.request.user,
            action_type=SeckillAdminActionLog.ACTION_UPDATE_ACTIVITY,
            activity=activity,
            before_data=before,
            after_data=_snapshot_activity(activity),
            remark='Update seckill activity',
        )

    def destroy(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.reserved_stock > 0:
            return Response(
                {'error': 'Current activity still has reserved stock and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = _snapshot_activity(activity)
        drop_activity_stock_bucket(activity.id)
        response = super().destroy(request, *args, **kwargs)
        _log_action(
            operator=request.user,
            action_type=SeckillAdminActionLog.ACTION_DELETE_ACTIVITY,
            activity=None,
            before_data=before,
            remark='Delete seckill activity',
        )
        return response

    @action(detail=True, methods=['patch'])
    def adjust_stock(self, request, pk=None):
        activity = self.get_object()
        payload = AdjustSeckillStockSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        mode = payload.validated_data['mode']
        qty = payload.validated_data['quantity']
        remark = payload.validated_data.get('remark', '')

        before = _snapshot_activity(activity)
        target_stock = activity.total_stock
        if mode == 'set':
            target_stock = qty
        elif mode == 'increase':
            target_stock = activity.total_stock + qty
        elif mode == 'decrease':
            target_stock = activity.total_stock - qty

        if target_stock < activity.reserved_stock:
            return Response(
                {'error': 'Total stock cannot be lower than reserved stock.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activity.total_stock = target_stock
        activity.save(update_fields=['total_stock', 'updated_at'])
        sync_activity_stock_bucket(activity_id=activity.id, remaining_stock=activity.remaining_stock)

        _log_action(
            operator=request.user,
            action_type=SeckillAdminActionLog.ACTION_ADJUST_STOCK,
            activity=activity,
            before_data=before,
            after_data=_snapshot_activity(activity),
            remark=remark,
        )

        return Response({'message': 'Stock adjusted successfully.', 'data': AdminSeckillActivitySerializer(activity).data})

    @action(detail=True, methods=['patch'])
    def adjust_price(self, request, pk=None):
        activity = self.get_object()
        payload = AdjustSeckillPriceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        before = _snapshot_activity(activity)
        activity.seckill_price = payload.validated_data['seckill_price']
        activity.save(update_fields=['seckill_price', 'updated_at'])

        _log_action(
            operator=request.user,
            action_type=SeckillAdminActionLog.ACTION_ADJUST_PRICE,
            activity=activity,
            before_data=before,
            after_data=_snapshot_activity(activity),
            remark=payload.validated_data.get('remark', ''),
        )

        return Response({'message': 'Price adjusted successfully.', 'data': AdminSeckillActivitySerializer(activity).data})

    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        activity = self.get_object()
        payload = ChangeSeckillStatusSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        target_status = payload.validated_data['status']
        now = timezone.now()

        if activity.start_at >= activity.end_at:
            return Response({'error': 'Invalid activity time range.'}, status=status.HTTP_400_BAD_REQUEST)

        if target_status == SeckillActivity.STATUS_PREHEATING:
            if activity.start_at <= now:
                return Response({'error': 'Preheating requires start_at to be in the future.'}, status=status.HTTP_400_BAD_REQUEST)

        if target_status == SeckillActivity.STATUS_ONLINE:
            if not (activity.start_at <= now <= activity.end_at):
                return Response({'error': 'Activity must be within the active time window to go online.'}, status=status.HTTP_400_BAD_REQUEST)

        before = _snapshot_activity(activity)
        activity.status = target_status
        activity.is_enabled = target_status != SeckillActivity.STATUS_OFFLINE
        activity.save(update_fields=['status', 'is_enabled', 'updated_at'])
        sync_activity_stock_bucket(activity_id=activity.id, remaining_stock=activity.remaining_stock)

        _log_action(
            operator=request.user,
            action_type=SeckillAdminActionLog.ACTION_CHANGE_STATUS,
            activity=activity,
            before_data=before,
            after_data=_snapshot_activity(activity),
            remark=payload.validated_data.get('remark', ''),
        )

        return Response({'message': 'Status updated successfully.', 'data': AdminSeckillActivitySerializer(activity).data})


class AdminSeckillReservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeckillReservation.objects.select_related('activity', 'product', 'user', 'order').all().order_by('-id')
    serializer_class = AdminSeckillReservationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        status_value = (self.request.query_params.get('status') or '').strip()
        if status_value:
            queryset = queryset.filter(status=status_value)

        activity_id = self.request.query_params.get('activity_id')
        if activity_id:
            try:
                queryset = queryset.filter(activity_id=int(activity_id))
            except (TypeError, ValueError):
                pass

        keyword = (self.request.query_params.get('keyword') or '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(user__username__icontains=keyword)
                | Q(product__name__icontains=keyword)
                | Q(activity__name__icontains=keyword)
            )

        return queryset

    @action(detail=True, methods=['patch'])
    def release(self, request, pk=None):
        payload = ReleaseReservationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        remark = payload.validated_data.get('remark', '')

        with transaction.atomic():
            reservation = (
                SeckillReservation.objects
                .select_for_update()
                .select_related('activity', 'product', 'order')
                .filter(id=pk)
                .first()
            )
            if not reservation:
                return Response({'error': 'Reservation not found.'}, status=status.HTTP_404_NOT_FOUND)

            if _reservation_is_paid(reservation):
                return Response(
                    {'error': 'Paid reservation cannot be released.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            target_status = _get_release_target_status(reservation)
            if target_status is None:
                return Response(
                    {
                        'message': 'Reservation is already released or bound to an order and cannot be released directly.',
                        'released': False,
                        'data': AdminSeckillReservationSerializer(reservation).data,
                    },
                    status=status.HTTP_200_OK,
                )

            before = _snapshot_reservation(reservation)
            _release_reservation_quota(
                reservation,
                new_status=target_status,
                restore_product_stock=True,
            )
            reservation.refresh_from_db()

        _log_action(
            operator=request.user,
            action_type=SeckillAdminActionLog.ACTION_RELEASE_RESERVATION,
            activity=reservation.activity,
            reservation=reservation,
            before_data=before,
            after_data=_snapshot_reservation(reservation),
            remark=remark,
        )

        return Response({'message': 'Reservation released successfully.', 'released': True, 'data': AdminSeckillReservationSerializer(reservation).data})


class AdminSeckillActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeckillAdminActionLog.objects.select_related('operator', 'activity', 'reservation').all().order_by('-id')
    serializer_class = AdminSeckillActionLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()

        action_type = (self.request.query_params.get('action_type') or '').strip()
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        activity_id = self.request.query_params.get('activity_id')
        if activity_id:
            try:
                queryset = queryset.filter(activity_id=int(activity_id))
            except (TypeError, ValueError):
                pass

        return queryset

