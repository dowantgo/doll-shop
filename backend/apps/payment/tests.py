from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order
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
