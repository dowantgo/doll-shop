import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.coupons.models import OrderDiscountSnapshot
from apps.products.cache_utils import bump_feed_version_on_commit
from apps.products.models import Product

from ..models import Order
from .lifecycle import release_locked_coupon

logger = logging.getLogger(__name__)


def cleanup_expired_orders() -> dict:
    now = timezone.now()
    expired_time = now - timedelta(minutes=30)
    expired_orders = Order.objects.filter(
        payment_status='pending',
        status='pending',
    ).filter(expires_at__lt=now) | Order.objects.filter(
        payment_status='pending',
        status='pending',
        expires_at__isnull=True,
        created_at__lt=expired_time,
    )

    scanned = 0
    cleaned = 0
    released_coupon_count = 0
    seckill_reset_count = 0
    errors = 0

    for order in expired_orders.distinct():
        scanned += 1
        has_sales_change = False
        try:
            with transaction.atomic():
                locked_order = (
                    Order.objects
                    .select_for_update()
                    .prefetch_related('items')
                    .get(pk=order.pk)
                )
                if locked_order.payment_status != 'pending' or locked_order.status != 'pending':
                    continue

                for item in locked_order.items.all():
                    if item.product:
                        product = Product.objects.select_for_update().get(id=item.product.id)
                        product.stock += item.quantity
                        product.sales -= item.quantity
                        product.save(update_fields=['stock', 'sales', 'updated_at'])
                        has_sales_change = True

                seckill_reservation = getattr(locked_order, 'seckill_reservation', None)
                if seckill_reservation and seckill_reservation.status in ('reserved', 'ordered'):
                    from apps.seckill.models import SeckillActivity, SeckillReservation
                    from apps.seckill.redis_flow import restore_stock_from_db

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
                        restore_stock_from_db(activity.id, locked_reservation.quantity, reason='order_expired')

                        locked_reservation.status = 'expired'
                        locked_reservation.order = None
                        locked_reservation.reserved_expires_at = None
                        locked_reservation.save(update_fields=['status', 'order', 'reserved_expires_at', 'updated_at'])
                        seckill_reset_count += 1

                locked_order.status = 'cancelled'
                locked_order.save(update_fields=['status', 'updated_at'])

                snapshot = (
                    OrderDiscountSnapshot.objects
                    .select_for_update()
                    .select_related('user_coupon')
                    .filter(order=locked_order)
                    .first()
                )
                coupon_id, coupon_no = release_locked_coupon(snapshot)
                if coupon_id:
                    released_coupon_count += 1
                    logger.info(
                        'expired_order_release_coupon order_id=%s coupon_id=%s coupon_no=%s',
                        locked_order.order_id,
                        coupon_id,
                        coupon_no,
                    )
            if has_sales_change:
                bump_feed_version_on_commit()
            cleaned += 1
            logger.info('expired_order_cancelled order_id=%s user_id=%s', order.order_id, order.user_id)
        except Exception:
            errors += 1
            logger.exception(
                'cleanup_expired_orders_failed id=%s order_id=%s created_at=%s fallback_expired_time=%s',
                order.id,
                order.order_id,
                order.created_at,
                expired_time,
            )

    summary = {
        'scanned': scanned,
        'cleaned': cleaned,
        'released_coupon_count': released_coupon_count,
        'seckill_reset_count': seckill_reset_count,
        'errors': errors,
    }
    logger.info('cleanup_expired_orders_summary %s', summary)
    return summary
