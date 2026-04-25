from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order
from apps.orders.services.pricing import pending_payment_probe
from apps.payment.models import PaymentTransaction
from apps.users.models import Address


class MockPayCancelledOrderTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='pay_user',
            email='pay_user@example.com',
            password='TestPass123!',
            role='user',
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138000',
            province='Guizhou',
            city='Guiyang',
            district='Yunyan',
            address='Road 1',
            is_default=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('39.90'),
            status='cancelled',
            payment_status='pending',
            address=self.address,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.txn = PaymentTransaction.objects.create(
            order=self.order,
            payment_method='mock',
            out_trade_no='PAYTESTCANCELLED0001',
            amount=Decimal('39.90'),
            status='pending',
            expire_time=timezone.now() + timedelta(minutes=15),
        )
        self.client.force_authenticate(self.user)

    def test_mock_pay_rejects_cancelled_order(self):
        resp = self.client.post(f'/api/pay/{self.txn.out_trade_no}/mock_pay/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.txn.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        self.assertNotEqual(self.txn.status, 'paid')


class PaymentProbeCacheLifecycleTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='probe_user',
            email='probe_user@example.com',
            password='TestPass123!',
            role='user',
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138001',
            province='Guizhou',
            city='Guiyang',
            district='Yunyan',
            address='Road 2',
            is_default=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('59.90'),
            status='pending',
            payment_status='pending',
            address=self.address,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.client.force_authenticate(self.user)

    def test_create_payment_warms_probe_cache_and_mock_pay_clears_it(self):
        create_resp = self.client.post(
            '/api/pay/create_payment/',
            {
                'order_id': self.order.order_id,
                'payment_method': 'mock',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_200_OK)
        payment_id = create_resp.data['payment_id']
        self.assertEqual(pending_payment_probe(self.user), payment_id)

        pay_resp = self.client.post(f'/api/pay/{payment_id}/mock_pay/')
        self.assertEqual(pay_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pending_payment_probe(self.user), '')

    def test_close_payment_clears_probe_cache(self):
        txn = PaymentTransaction.objects.create(
            order=self.order,
            payment_method='mock',
            out_trade_no='PAYTESTPENDING0001',
            amount=Decimal('59.90'),
            status='pending',
            expire_time=timezone.now() + timedelta(minutes=15),
        )
        self.assertEqual(pending_payment_probe(self.user), txn.out_trade_no)

        close_resp = self.client.post(f'/api/pay/{txn.out_trade_no}/close/')
        self.assertEqual(close_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pending_payment_probe(self.user), '')
