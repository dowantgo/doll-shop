import logging

from celery import shared_task

from .views import cleanup_expired_reservations

logger = logging.getLogger(__name__)


@shared_task(name='seckill.cleanup_expired_reservations')
def cleanup_expired_reservations_task():
    result = cleanup_expired_reservations()
    logger.info(
        'seckill.cleanup_expired_reservations done released_ticket_count=%s released_db_count=%s',
        result.get('released_ticket_count'),
        result.get('released_db_count'),
    )
    return result
