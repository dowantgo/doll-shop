import logging

from celery import shared_task

from .views import run_reconcile

logger = logging.getLogger(__name__)


@shared_task(name='payment.reconcile_pending')
def reconcile_pending():
    result = run_reconcile()
    logger.info(
        'payment.reconcile_pending done scanned=%s fixed_paid=%s closed=%s retried=%s skipped=%s',
        result.get('scanned'),
        result.get('fixed_paid'),
        result.get('closed'),
        result.get('retried'),
        result.get('skipped'),
    )
    return result
