from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order
from apps.products.models import Product
from apps.users.models import Address

from .models import SeckillActivity, SeckillReservation
from .redis_flow import get_activity_remaining_stock, load_reservation_ticket
from .views import cleanup_expired_reservations


@override_settings(SECKILL_RESERVATION_EXPIRE_MINUTES=1)
class SeckillRedisFlowTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='iter52-seckill-user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Iter5.2 Seckill Product',
            description='redis seckill',
            price=Decimal('99.00'),
            stock=10,
            sales=0,
            status=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138002',
            province='Guizhou',
            city='Guiyang',
            district='Nanming',
            address='Road 7',
            is_default=True,
        )
        self.activity = SeckillActivity.objects.create(
            name='Iter5.2 Redis Activity',
            product=self.product,
            seckill_price=Decimal('59.90'),
            total_stock=3,
            reserved_stock=0,
            start_at=timezone.now() - timedelta(minutes=5),
            end_at=timezone.now() + timedelta(minutes=30),
            status=SeckillActivity.STATUS_ONLINE,
            is_enabled=True,
            per_user_limit=1,
        )
        self.client.force_authenticate(self.user)

    def _issue_token(self):
        resp = self.client.post(
            '/api/seckill/issue-submit-token/',
            {'activity_id': self.activity.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp.data['submit_token']

    def test_pre_reserve_uses_redis_ticket_and_reduces_bucket(self):
        submit_token = self._issue_token()
        resp = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': submit_token},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-1',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['data']['reservation_token'])
        self.assertIsNone(resp.data['data']['id'])
        self.assertEqual(get_activity_remaining_stock(self.activity.id, self.activity.remaining_stock), 2)
        self.assertIsNotNone(load_reservation_ticket(resp.data['data']['reservation_token']))
        self.assertEqual(SeckillReservation.objects.count(), 0)

    def test_pre_reserve_idempotency_returns_same_ticket(self):
        submit_token = self._issue_token()
        first = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': submit_token},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-2',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': 'stale-token'},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-2',
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(
            first.data['data']['reservation_token'],
            second.data['data']['reservation_token'],
        )

    def test_submit_token_is_one_time_only(self):
        submit_token = self._issue_token()
        first = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': submit_token},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-3a',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': submit_token},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-3b',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_from_reservation_token_materializes_reservation(self):
        submit_token = self._issue_token()
        reserve_resp = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': submit_token},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-4',
        )
        reservation_token = reserve_resp.data['data']['reservation_token']

        order_resp = self.client.post(
            '/api/seckill/create-order/',
            {'reservation_token': reservation_token, 'address_id': self.address.id},
            format='json',
        )
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        reservation = SeckillReservation.objects.get(user=self.user)
        self.assertEqual(reservation.reservation_token, reservation_token)
        self.assertEqual(reservation.status, SeckillReservation.STATUS_ORDERED)
        self.activity.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.activity.reserved_stock, 1)
        self.assertEqual(self.product.stock, 9)
        self.assertEqual(self.product.sales, 1)
        self.assertIsNone(load_reservation_ticket(reservation_token))

    def test_cleanup_expired_redis_ticket_restores_stock(self):
        submit_token = self._issue_token()
        reserve_resp = self.client.post(
            '/api/seckill/pre-reserve/',
            {'activity_id': self.activity.id, 'quantity': 1, 'submit_token': submit_token},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter52-pre-5',
        )
        reservation_token = reserve_resp.data['data']['reservation_token']
        ticket = load_reservation_ticket(reservation_token)
        self.assertIsNotNone(ticket)

        redis_conn = cache.client.get_client(write=True)
        expire_index_key = 'iter5.2:seckill:reservation-expire-index'
        redis_conn.zadd(expire_index_key, {reservation_token: int(timezone.now().timestamp()) - 1})

        result = cleanup_expired_reservations()

        self.assertEqual(result['released_ticket_count'], 1)
        self.assertEqual(get_activity_remaining_stock(self.activity.id, self.activity.remaining_stock), 3)
        self.assertIsNone(load_reservation_ticket(reservation_token))
