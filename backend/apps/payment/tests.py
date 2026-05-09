from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

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


class PaymentStatusQueryProtectionTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='payment_query_user',
            email='payment_query_user@example.com',
            password='TestPass123!',
            role='user',
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138002',
            province='Guizhou',
            city='Guiyang',
            district='Yunyan',
            address='Road 3',
            is_default=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('79.90'),
            status='pending',
            payment_status='pending',
            address=self.address,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.txn = PaymentTransaction.objects.create(
            order=self.order,
            payment_method='alipay',
            out_trade_no='PAYQUERYITER50001',
            amount=Decimal('79.90'),
            status='pending',
            expire_time=timezone.now() + timedelta(minutes=15),
        )
        self.client.force_authenticate(self.user)

    @patch('apps.payment.views.alipay_service.query_order')
    def test_status_endpoint_uses_cache_for_pending_query(self, mock_query):
        mock_query.return_value = {'trade_status': 'WAIT_BUYER_PAY'}

        first = self.client.get(f'/api/pay/{self.txn.out_trade_no}/status/')
        second = self.client.get(f'/api/pay/{self.txn.out_trade_no}/status/')

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_query.call_count, 1)

    @patch('apps.payment.views.alipay_service.query_order')
    def test_query_endpoint_is_rate_limited(self, mock_query):
        mock_query.return_value = {'trade_status': 'WAIT_BUYER_PAY'}

        first = self.client.get(f'/api/pay/query/?out_trade_no={self.txn.out_trade_no}')
        second = self.client.get(f'/api/pay/query/?out_trade_no={self.txn.out_trade_no}')

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch('apps.payment.views.alipay_service.query_order')
    def test_query_endpoint_reuses_cached_pending_payload(self, mock_query):
        mock_query.return_value = {'trade_status': 'WAIT_BUYER_PAY'}

        status_resp = self.client.get(f'/api/pay/{self.txn.out_trade_no}/status/')
        self.assertEqual(status_resp.status_code, status.HTTP_200_OK)

        query_resp = self.client.get(f'/api/pay/query/?out_trade_no={self.txn.out_trade_no}')
        self.assertEqual(query_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(query_resp.data['status'], 'pending')
