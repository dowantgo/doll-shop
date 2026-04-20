import threading
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework import serializers

from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import Address

from .models import RefundRequest
from .serializers import validate_refund_request


class RefundConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='refund_race_user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Race Product',
            description='race',
            price=Decimal('99.00'),
            stock=50,
            status=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Race',
            phone='13800000000',
            province='Guizhou',
            city='Guiyang',
            district='Nanming',
            address='Road',
            is_default=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('99.00'),
            address=self.address,
            payment_status='paid',
            status='paid',
            paid_at=timezone.now(),
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=Decimal('99.00'),
        )

    def _try_create_refund(self, barrier: threading.Barrier, result_bucket: list, idx: int):
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait(timeout=5)
                order, order_item, requested_amount = validate_refund_request(
                    user=self.user,
                    order_id=self.order.order_id,
                    order_item_id=self.order_item.id,
                    quantity=1,
                )
                # Hold lock briefly to increase race visibility in test.
                time.sleep(0.2)
                refund = RefundRequest.objects.create(
                    user=self.user,
                    order=order,
                    order_item=order_item,
                    quantity=1,
                    reason='race',
                    requested_amount=requested_amount,
                    approved_amount=requested_amount,
                    status=RefundRequest.STATUS_PENDING,
                )
                result_bucket[idx] = ('ok', refund.id)
        except serializers.ValidationError as exc:
            result_bucket[idx] = ('validation_error', str(exc.detail))
        except Exception as exc:
            result_bucket[idx] = ('error', str(exc))
        finally:
            close_old_connections()

    def test_same_order_item_concurrent_refund_only_one_succeeds(self):
        barrier = threading.Barrier(2)
        results = [None, None]
        t1 = threading.Thread(target=self._try_create_refund, args=(barrier, results, 0))
        t2 = threading.Thread(target=self._try_create_refund, args=(barrier, results, 1))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        active_count = (
            RefundRequest.objects
            .exclude(status__in=[RefundRequest.STATUS_REJECTED, RefundRequest.STATUS_FAILED])
            .filter(order_item=self.order_item)
            .count()
        )
        self.assertEqual(active_count, 1, msg=f'Unexpected results: {results}')

        ok_count = len([x for x in results if x and x[0] == 'ok'])
        self.assertEqual(ok_count, 1, msg=f'Unexpected results: {results}')

