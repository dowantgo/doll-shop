import base64
import io
import logging
import secrets
from datetime import timedelta

import qrcode
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.services.pricing import clear_pending_payment_probe, set_pending_payment_probe
from dollshop.metrics import metric_increment

from .models import PaymentTransaction
from .serializers import CreatePaymentSerializer
from .services.alipay import alipay_service
from .services.errors import (
    PaymentConfigurationError,
    PaymentError,
    PaymentNetworkError,
    PaymentSignatureError,
)

logger = logging.getLogger(__name__)
PAYMENT_STATUS_CACHE_TTL = 3
PAYMENT_STATUS_RATE_LIMIT_SECONDS = 2


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and getattr(request.user, 'role', '') == 'admin'


def _gen_out_trade_no() -> str:
    return f"PAY{timezone.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}"


def _generate_qr_code_image(qr_url: str) -> str:
    """生成二维码图片的Base64 DataURL"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        
        base64_data = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/png;base64,{base64_data}"
    except Exception as e:
        logger.error(f"生成二维码图片失败: {e}")
        return ""


def _payment_status_cache_key(out_trade_no: str) -> str:
    return f'iter5:payment:status:{out_trade_no}'


def _payment_rate_limit_key(user_id: int, out_trade_no: str, suffix: str) -> str:
    return f'iter5:payment:rate:{suffix}:{user_id}:{out_trade_no}'


def _build_status_payload(txn: PaymentTransaction) -> dict:
    status_map = {
        'paid': 'success',
        'failed': 'failed',
        'closed': 'closed',
        'expired': 'closed',
        'pending': 'pending',
    }
    return {
        'payment_id': txn.out_trade_no,
        'status': status_map.get(txn.status, 'pending'),
        'trade_no': txn.trade_no or '',
    }


def _cache_payment_status(txn: PaymentTransaction, payload: dict) -> None:
    if txn.status == 'pending':
        cache.set(_payment_status_cache_key(txn.out_trade_no), payload, timeout=PAYMENT_STATUS_CACHE_TTL)
    else:
        cache.delete(_payment_status_cache_key(txn.out_trade_no))


def _allow_payment_status_query(user_id: int, out_trade_no: str, suffix: str) -> bool:
    created = cache.add(
        _payment_rate_limit_key(user_id, out_trade_no, suffix),
        1,
        timeout=PAYMENT_STATUS_RATE_LIMIT_SECONDS,
    )
    if not created:
        metric_increment('payment_status_rate_limited', endpoint=suffix)
    return created


@transaction.atomic
def _mark_paid(txn: PaymentTransaction, trade_no: str = '') -> None:
    now = timezone.now()
    if txn.status != 'paid':
        txn.status = 'paid'
        txn.paid_time = now
    if trade_no:
        duplicated_trade = (
            PaymentTransaction.objects
            .filter(trade_no=trade_no)
            .exclude(pk=txn.pk)
            .exists()
        )
        if duplicated_trade:
            logger.warning(
                'Skip duplicated trade_no while marking paid: out_trade_no=%s trade_no=%s',
                txn.out_trade_no,
                trade_no,
            )
        else:
            txn.trade_no = trade_no
    txn.save(update_fields=['status', 'paid_time', 'trade_no', 'updated_at'])

    order = txn.order
    changed = False
    if order.payment_status != 'paid':
        order.payment_status = 'paid'
        changed = True
    if order.status == 'pending':
        order.status = 'paid'
        changed = True
    if not order.payment_method:
        order.payment_method = txn.payment_method
        changed = True
    if not order.paid_at:
        order.paid_at = now
        changed = True
    if trade_no and not order.trade_no:
        order.trade_no = trade_no
        changed = True
    if changed:
        order.save()
    clear_pending_payment_probe(order.user_id, txn.out_trade_no)
    cache.delete(_payment_status_cache_key(txn.out_trade_no))
    logger.info(
        'payment_mark_paid payment_id=%s order_id=%s trade_no=%s payment_method=%s',
        txn.out_trade_no,
        order.order_id,
        txn.trade_no or '',
        txn.payment_method,
    )

    snapshot = getattr(order, 'discount_snapshot', None)
    if snapshot and snapshot.user_coupon and snapshot.user_coupon.status != 'used':
        snapshot.user_coupon.status = 'used'
        snapshot.user_coupon.used_at = now
        snapshot.user_coupon.save(update_fields=['status', 'used_at'])

    # Sync seckill reservation status if this order is generated by seckill flow.
    seckill_reservation = getattr(order, 'seckill_reservation', None)
    if seckill_reservation and seckill_reservation.status != 'paid':
        seckill_reservation.status = 'paid'
        seckill_reservation.save(update_fields=['status', 'updated_at'])


def _is_reconcile_target(txn: PaymentTransaction, now=None) -> bool:
    now = now or timezone.now()
    return (
        txn.status == 'pending'
        and txn.payment_method == 'alipay'
        and txn.expire_time is not None
        and txn.expire_time <= now
    )


def _record_reconcile_attempt(
    txn: PaymentTransaction,
    *,
    status_text: str,
    error_text: str = '',
) -> None:
    now = timezone.now()
    txn.reconcile_attempts = (txn.reconcile_attempts or 0) + 1
    txn.last_reconcile_at = now
    txn.last_reconcile_status = status_text
    txn.last_reconcile_error = error_text[:2000]
    txn.save(
        update_fields=[
            'reconcile_attempts',
            'last_reconcile_at',
            'last_reconcile_status',
            'last_reconcile_error',
            'updated_at',
        ]
    )


class ReconcilePaymentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        return Response(run_reconcile())


def run_reconcile():
    now = timezone.now()
    candidates = list(
        PaymentTransaction.objects.select_related('order')
        .filter(payment_method='alipay', status='pending', expire_time__lte=now)
        .order_by('created_at')
    )

    scanned = len(candidates)
    fixed_paid = 0
    closed = 0
    skipped = 0
    retried = 0
    errors = []

    for candidate in candidates:
        try:
            alipay_info = alipay_service.query_order(candidate.out_trade_no)
            trade_status = (alipay_info.get('trade_status') or '').strip()
            trade_no = (alipay_info.get('trade_no') or '').strip()
        except PaymentError as exc:
            with transaction.atomic():
                locked_txn = PaymentTransaction.objects.select_for_update().select_related('order').get(pk=candidate.pk)
                if not _is_reconcile_target(locked_txn, now):
                    skipped += 1
                    continue
                _record_reconcile_attempt(locked_txn, status_text='error', error_text=str(exc))
            retried += 1
            errors.append(
                {
                    'payment_id': candidate.out_trade_no,
                    'order_id': candidate.order.order_id if getattr(candidate, 'order', None) else '',
                    'action': 'query',
                    'message': str(exc),
                }
            )
            logger.warning(
                'payment_reconcile_error payment_id=%s order_id=%s action=query error=%s',
                candidate.out_trade_no,
                candidate.order.order_id if getattr(candidate, 'order', None) else '',
                str(exc),
            )
            continue

        if trade_status in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
            with transaction.atomic():
                locked_txn = PaymentTransaction.objects.select_for_update().select_related('order').get(pk=candidate.pk)
                if not _is_reconcile_target(locked_txn, now):
                    skipped += 1
                    continue
                _mark_paid(locked_txn, trade_no)
                locked_txn.reconcile_attempts = (locked_txn.reconcile_attempts or 0) + 1
                locked_txn.last_reconcile_at = timezone.now()
                locked_txn.last_reconcile_status = 'paid'
                locked_txn.last_reconcile_error = ''
                locked_txn.save(
                    update_fields=[
                        'reconcile_attempts',
                        'last_reconcile_at',
                        'last_reconcile_status',
                        'last_reconcile_error',
                        'updated_at',
                    ]
                )
            fixed_paid += 1
            logger.info(
                'payment_reconcile_fixed_paid payment_id=%s order_id=%s trade_no=%s',
                candidate.out_trade_no,
                candidate.order.order_id if getattr(candidate, 'order', None) else '',
                trade_no,
            )
            continue

        if trade_status == 'TRADE_CLOSED':
            with transaction.atomic():
                locked_txn = PaymentTransaction.objects.select_for_update().get(pk=candidate.pk)
                if not _is_reconcile_target(locked_txn, now):
                    skipped += 1
                    continue
                if locked_txn.status != 'closed':
                    locked_txn.status = 'closed'
                    locked_txn.last_reconcile_error = ''
                    locked_txn.last_reconcile_status = 'closed'
                    locked_txn.last_reconcile_at = timezone.now()
                    locked_txn.reconcile_attempts = (locked_txn.reconcile_attempts or 0) + 1
                    locked_txn.save(
                        update_fields=[
                            'status',
                            'reconcile_attempts',
                            'last_reconcile_at',
                            'last_reconcile_status',
                            'last_reconcile_error',
                            'updated_at',
                        ]
                    )
                clear_pending_payment_probe(locked_txn.order.user_id, locked_txn.out_trade_no)
            closed += 1
            logger.info(
                'payment_reconcile_closed payment_id=%s order_id=%s',
                candidate.out_trade_no,
                candidate.order.order_id if getattr(candidate, 'order', None) else '',
            )
            continue

        # Remote still pending or unknown state. Record retry metadata and leave local pending.
        with transaction.atomic():
            locked_txn = PaymentTransaction.objects.select_for_update().get(pk=candidate.pk)
            if not _is_reconcile_target(locked_txn, now):
                skipped += 1
                continue
            message = f"trade_status={trade_status or 'UNKNOWN'}"
            _record_reconcile_attempt(locked_txn, status_text='retry', error_text=message)
        retried += 1
        errors.append(
            {
                'payment_id': candidate.out_trade_no,
                'order_id': candidate.order.order_id if getattr(candidate, 'order', None) else '',
                'action': 'retry',
                'trade_status': trade_status or 'UNKNOWN',
                'message': 'Payment not settled yet.',
            }
        )
        logger.info(
            'payment_reconcile_retry payment_id=%s order_id=%s trade_status=%s',
            candidate.out_trade_no,
            candidate.order.order_id if getattr(candidate, 'order', None) else '',
            trade_status or 'UNKNOWN',
        )

    summary = {
        'scanned': scanned,
        'fixed_paid': fixed_paid,
        'closed': closed,
        'retried': retried,
        'skipped': skipped,
        'errors': errors,
    }
    logger.info('payment_reconcile_summary %s', summary)
    return summary


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']

        try:
            order = Order.objects.select_for_update().get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': '订单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status == 'paid':
            return Response({'error': '订单已支付'}, status=status.HTTP_400_BAD_REQUEST)
        if order.status == 'cancelled':
            return Response({'error': '已取消订单不可创建支付'}, status=status.HTTP_400_BAD_REQUEST)

        txn = PaymentTransaction.objects.filter(order=order, status='pending').order_by('-created_at').first()
        if not txn:
            txn = PaymentTransaction.objects.create(
                order=order,
                payment_method=payment_method,
                out_trade_no=_gen_out_trade_no(),
                amount=order.total_price,
                status='pending',
                expire_time=timezone.now() + timedelta(minutes=15),
            )
        else:
            txn.payment_method = payment_method
            txn.amount = order.total_price
            txn.expire_time = timezone.now() + timedelta(minutes=15)
            txn.save(update_fields=['payment_method', 'amount', 'expire_time', 'updated_at'])

        try:
            qr_code = ''
            expire_time = txn.expire_time.isoformat() if txn.expire_time else ''

            if payment_method == 'alipay':
                result = alipay_service.create_qr_code(
                    out_trade_no=txn.out_trade_no,
                    total_amount=float(txn.amount),
                    subject=f'玩偶商城-{order.order_id}',
                )
                qr_code = result.get('qr_code', '')
                expire_time = result.get('expire_time', expire_time)
            else:
                qr_code = f'mock://pay/{txn.out_trade_no}'

            txn.qr_code = qr_code
            txn.save(update_fields=['qr_code', 'updated_at'])
            set_pending_payment_probe(order.user_id, txn.out_trade_no)
            logger.info(
                'payment_created payment_id=%s order_id=%s payment_method=%s amount=%s',
                txn.out_trade_no,
                order.order_id,
                payment_method,
                txn.amount,
            )

            # 生成二维码图片
            qr_code_image = _generate_qr_code_image(qr_code)

            return Response(
                {
                    'payment_id': txn.out_trade_no,
                    'qr_code': qr_code,
                    'qr_code_image': qr_code_image,
                    'expire_time': expire_time,
                    'payment_method': payment_method,
                }
            )
        except (PaymentConfigurationError, PaymentNetworkError, PaymentSignatureError) as exc:
            logger.warning('Create payment failed: %s', exc)
            return Response({'error': f'创建支付失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)
        except PaymentError as exc:
            logger.exception('Create payment error: %s', exc)
            return Response({'error': f'创建支付失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, out_trade_no):
        try:
            txn = PaymentTransaction.objects.select_related('order').get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({'error': '支付单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == 'pending' and txn.expire_time and timezone.now() > txn.expire_time:
            txn.status = 'closed'
            txn.save(update_fields=['status', 'updated_at'])
            clear_pending_payment_probe(txn.order.user_id, txn.out_trade_no)
            cache.delete(_payment_status_cache_key(txn.out_trade_no))

        if txn.status == 'pending':
            cached_payload = cache.get(_payment_status_cache_key(txn.out_trade_no))
            if cached_payload:
                metric_increment('payment_status_cache_hit', endpoint='status')
                return Response(cached_payload)

        if not _allow_payment_status_query(request.user.id, txn.out_trade_no, 'status'):
            return Response({'error': '支付状态查询过于频繁，请稍后再试。'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if txn.status == 'pending' and txn.payment_method == 'alipay':
            try:
                metric_increment('payment_third_party_query', endpoint='status')
                query = alipay_service.query_order(txn.out_trade_no)
                trade_status = query.get('trade_status')
                if trade_status in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
                    _mark_paid(txn, query.get('trade_no', ''))
                    txn.refresh_from_db()
                elif trade_status in ('TRADE_CLOSED', 'TRADE_FINISHED') and txn.status != 'paid':
                    txn.status = 'closed'
                    txn.save(update_fields=['status', 'updated_at'])
                    clear_pending_payment_probe(txn.order.user_id, txn.out_trade_no)
                    cache.delete(_payment_status_cache_key(txn.out_trade_no))
            except PaymentError:
                pass

        payload = _build_status_payload(txn)
        _cache_payment_status(txn, payload)
        logger.info(
            'payment_status payment_id=%s order_id=%s user_id=%s status=%s',
            txn.out_trade_no,
            txn.order.order_id,
            request.user.id,
            payload['status'],
        )

        return Response(payload)


class MockPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, out_trade_no):
        try:
            txn = PaymentTransaction.objects.select_related('order').get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({'error': '支付单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == 'paid':
            return Response({'message': '已支付'})
        if txn.status in ('closed', 'expired', 'failed'):
            return Response({'error': '支付单已关闭或失效'}, status=status.HTTP_400_BAD_REQUEST)
        if txn.order.status == 'cancelled':
            if txn.status == 'pending':
                txn.status = 'closed'
                txn.save(update_fields=['status', 'updated_at'])
            return Response({'error': '已取消订单不能继续支付'}, status=status.HTTP_400_BAD_REQUEST)

        _mark_paid(txn)
        logger.info(
            'mock_pay_success payment_id=%s order_id=%s user_id=%s',
            txn.out_trade_no,
            txn.order.order_id,
            request.user.id,
        )
        return Response({'message': '支付成功', 'status': 'success'})


class ClosePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, out_trade_no):
        try:
            txn = PaymentTransaction.objects.select_related('order').get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({'error': '支付单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == 'paid':
            return Response({'error': '已支付订单不能关闭'}, status=status.HTTP_400_BAD_REQUEST)

        txn.status = 'closed'
        txn.save(update_fields=['status', 'updated_at'])
        clear_pending_payment_probe(txn.order.user_id, txn.out_trade_no)
        cache.delete(_payment_status_cache_key(txn.out_trade_no))
        logger.info(
            'payment_closed payment_id=%s order_id=%s user_id=%s',
            txn.out_trade_no,
            txn.order.order_id,
            request.user.id,
        )
        return Response({'message': '支付单已关闭', 'status': 'closed'})


class PaymentQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        out_trade_no = request.query_params.get('out_trade_no', '').strip()
        if not out_trade_no:
            return Response({'error': 'out_trade_no is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            txn = PaymentTransaction.objects.select_related('order').get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({'error': 'Payment transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == 'pending' and txn.expire_time and timezone.now() > txn.expire_time:
            txn.status = 'closed'
            txn.save(update_fields=['status', 'updated_at'])
            clear_pending_payment_probe(txn.order.user_id, txn.out_trade_no)
            cache.delete(_payment_status_cache_key(txn.out_trade_no))

        if txn.status == 'pending':
            cached_payload = cache.get(_payment_status_cache_key(txn.out_trade_no))
            if cached_payload:
                metric_increment('payment_status_cache_hit', endpoint='query')
                logger.info(
                    'payment_query payment_id=%s order_id=%s user_id=%s status=%s cached=%s',
                    txn.out_trade_no,
                    txn.order.order_id,
                    request.user.id,
                    cached_payload['status'],
                    True,
                )
                return Response(
                    {
                        **cached_payload,
                        'amount': str(txn.amount),
                        'payment_method': txn.payment_method,
                        'alipay': {},
                    }
                )

        if not _allow_payment_status_query(request.user.id, txn.out_trade_no, 'query'):
            return Response({'error': 'Payment status query is too frequent. Please try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        alipay_info = {}
        if txn.status == 'pending' and txn.payment_method == 'alipay':
            try:
                metric_increment('payment_third_party_query', endpoint='query')
                alipay_info = alipay_service.query_order(out_trade_no)
                trade_status = alipay_info.get('trade_status')
                if trade_status in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
                    _mark_paid(txn, alipay_info.get('trade_no', ''))
                    txn.refresh_from_db()
                elif trade_status == 'TRADE_CLOSED' and txn.status != 'paid':
                    txn.status = 'closed'
                    txn.save(update_fields=['status', 'updated_at'])
                    clear_pending_payment_probe(txn.order.user_id, txn.out_trade_no)
                    cache.delete(_payment_status_cache_key(txn.out_trade_no))
            except PaymentError as exc:
                alipay_info = {'error': str(exc)}

        payload = _build_status_payload(txn)
        _cache_payment_status(txn, payload)
        logger.info(
            'payment_query payment_id=%s order_id=%s user_id=%s status=%s',
            txn.out_trade_no,
            txn.order.order_id,
            request.user.id,
            payload['status'],
        )

        return Response(
            {
                **payload,
                'amount': str(txn.amount),
                'payment_method': txn.payment_method,
                'alipay': alipay_info,
            }
        )


class AliPayNotifyView(View):
    def post(self, request):
        data = request.POST.dict()
        if not data:
            return HttpResponse('fail')

        if not alipay_service.verify_notification(data):
            logger.warning('Alipay notify verify failed: %s', data)
            return HttpResponse('fail')

        out_trade_no = data.get('out_trade_no', '').strip()
        trade_no = data.get('trade_no', '').strip()
        trade_status = data.get('trade_status', '').strip()

        if not out_trade_no:
            return HttpResponse('fail')

        try:
            txn = PaymentTransaction.objects.select_related('order').get(out_trade_no=out_trade_no)
        except PaymentTransaction.DoesNotExist:
            logger.warning('Alipay notify unknown out_trade_no: %s', out_trade_no)
            return HttpResponse('fail')

        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            _mark_paid(txn, trade_no)
            logger.info(
                'alipay_notify_paid payment_id=%s order_id=%s trade_no=%s',
                txn.out_trade_no,
                txn.order.order_id,
                trade_no,
            )
        elif trade_status == 'TRADE_CLOSED' and txn.status != 'paid':
            txn.status = 'closed'
            txn.save(update_fields=['status', 'updated_at'])
            clear_pending_payment_probe(txn.order.user_id, txn.out_trade_no)
            cache.delete(_payment_status_cache_key(txn.out_trade_no))
            logger.info(
                'alipay_notify_closed payment_id=%s order_id=%s',
                txn.out_trade_no,
                txn.order.order_id,
            )

        return HttpResponse('success')
