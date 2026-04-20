import threading
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.coupons.models import CouponTemplate, UserCoupon
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import Address


class Iter3CouponCancelRaceTests(TransactionTestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='iter3_race_user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Race Coupon Product',
            description='race',
            price=Decimal('120.00'),
            stock=200,
            status=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Race',
            phone='13800138000',
            province='Guizhou',
            city='Guiyang',
            district='Nanming',
            address='Road 9',
            is_default=True,
        )
        self.template = CouponTemplate.objects.create(
            name='Race-20off',
            discount_amount=Decimal('20.00'),
            min_spend_amount=Decimal('100.00'),
            total_quota=999,
            claimed_count=0,
            per_user_limit=1,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=3),
            status='active',
        )

    def _create_pending_order_and_coupon(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('120.00'),
            address=self.address,
            payment_status='pending',
            status='pending',
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=Decimal('120.00'))
        coupon = UserCoupon.objects.create(user=self.user, template=self.template, status='unused')
        return order, coupon

    def _worker_apply_coupon(self, order_id, coupon_id, barrier: threading.Barrier, result_bucket: list, idx: int):
        close_old_connections()
        client = APIClient()
        client.force_authenticate(user=self.user)
        try:
            barrier.wait(timeout=5)
            resp = client.post(
                f'/api/orders/orders/{order_id}/apply-coupon/',
                {'coupon_id': coupon_id},
                format='json',
            )
            result_bucket[idx] = resp.status_code
        except Exception:
            result_bucket[idx] = 500
        finally:
            close_old_connections()

    def _worker_cancel_order(self, order_pk, barrier: threading.Barrier, result_bucket: list, idx: int):
        close_old_connections()
        client = APIClient()
        client.force_authenticate(user=self.user)
        try:
            barrier.wait(timeout=5)
            resp = client.post(f'/api/orders/orders/{order_pk}/cancel/')
            result_bucket[idx] = resp.status_code
        except Exception:
            result_bucket[idx] = 500
        finally:
            close_old_connections()

    def test_coupon_lock_and_cancel_race_keeps_consistency(self):
        for _ in range(5):
            order, coupon = self._create_pending_order_and_coupon()
            barrier = threading.Barrier(2)
            statuses = [None, None]
            t1 = threading.Thread(
                target=self._worker_apply_coupon,
                args=(order.order_id, coupon.id, barrier, statuses, 0),
            )
            t2 = threading.Thread(
                target=self._worker_cancel_order,
                args=(order.id, barrier, statuses, 1),
            )
            t1.start()
            t2.start()
            t1.join(timeout=10)
            t2.join(timeout=10)
            self.assertFalse(t1.is_alive(), msg='apply coupon thread did not finish in time')
            self.assertFalse(t2.is_alive(), msg='cancel order thread did not finish in time')

            order.refresh_from_db()
            coupon.refresh_from_db()

            if order.status == 'cancelled':
                self.assertEqual(
                    coupon.status,
                    'unused',
                    msg=f'order={order.order_id}, statuses={statuses}, coupon_status={coupon.status}',
                )
