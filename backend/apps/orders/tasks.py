import logging

from celery import shared_task

from .services.expiration import cleanup_expired_orders

logger = logging.getLogger(__name__)


@shared_task(name='orders.cleanup_expired_orders')
def cleanup_expired_orders_task():
    result = cleanup_expired_orders()
    logger.info(
        'orders.cleanup_expired_orders done scanned=%s cleaned=%s released_coupon_count=%s seckill_reset_count=%s errors=%s',
        result.get('scanned'),
        result.get('cleaned'),
        result.get('released_coupon_count'),
        result.get('seckill_reset_count'),
        result.get('errors'),
    )
    return result
