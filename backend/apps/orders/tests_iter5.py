from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone

from apps.cart.models import CartItem
from apps.coupons.models import CouponTemplate, OrderDiscountSnapshot, UserCoupon
from apps.orders.models import Order, OrderItem, OrderSubmission
from apps.orders.services.expiration import cleanup_expired_orders
from apps.products.models import Product
from apps.seckill.models import SeckillActivity, SeckillReservation
from apps.users.models import Address


class OrderIdempotencyTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='iter5_order_user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Iter5 Order Product',
            description='iter5',
            price=Decimal('88.00'),
            stock=20,
            status=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138000',
            province='Guizhou',
            city='Guiyang',
            district='Nanming',
            address='Road 5',
            is_default=True,
        )
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        self.client.force_authenticate(self.user)

    def test_create_from_cart_requires_idempotency_header(self):
        resp = self.client.post(
            '/api/orders/orders/create_from_cart/',
            {'address_id': self.address.id, 'remark': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_from_cart_reuses_successful_result(self):
        key = 'iter5-key-001'
        first = self.client.post(
            '/api/orders/orders/create_from_cart/',
            {'address_id': self.address.id, 'remark': ''},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(
            '/api/orders/orders/create_from_cart/',
            {'address_id': self.address.id, 'remark': ''},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data['order_id'], second.data['order_id'])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderSubmission.objects.filter(user=self.user, idempotency_key=key).count(), 1)

    def test_processing_submission_returns_conflict(self):
        OrderSubmission.objects.create(
            user=self.user,
            idempotency_key='iter5-processing',
            status=OrderSubmission.STATUS_PROCESSING,
        )
        resp = self.client.post(
            '/api/orders/orders/create_from_cart/',
            {'address_id': self.address.id, 'remark': ''},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='iter5-processing',
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


class ExpiredOrderCleanupTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='iter5_cleanup_user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Iter5 Cleanup Product',
            description='cleanup',
            price=Decimal('50.00'),
            stock=10,
            sales=3,
            status=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Cleaner',
            phone='13800138001',
            province='Guizhou',
            city='Guiyang',
            district='Yunyan',
            address='Road 6',
            is_default=True,
        )

    def test_cleanup_releases_stock_coupon_and_seckill_reservation(self):
        template = CouponTemplate.objects.create(
            name='Iter5 Expire Coupon',
            discount_amount=Decimal('10.00'),
            min_spend_amount=Decimal('30.00'),
            total_quota=10,
            claimed_count=0,
            per_user_limit=1,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=1),
            status='active',
        )
        user_coupon = UserCoupon.objects.create(
            user=self.user,
            template=template,
            status=UserCoupon.STATUS_LOCKED,
            locked_at=timezone.now(),
        )
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('50.00'),
            status='pending',
            payment_status='pending',
            address=self.address,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=2, price=Decimal('25.00'))
        OrderDiscountSnapshot.objects.create(
            order=order,
            user_coupon=user_coupon,
            subtotal_amount=Decimal('50.00'),
            full_reduction_amount=Decimal('0.00'),
            coupon_discount_amount=Decimal('10.00'),
            final_payable_amount=Decimal('40.00'),
            pricing_version='iter5-test',
            pricing_snapshot={},
        )
        activity = SeckillActivity.objects.create(
            name='Iter5 Cleanup Activity',
            product=self.product,
            seckill_price=Decimal('39.90'),
            total_stock=5,
            reserved_stock=2,
            start_at=timezone.now() - timedelta(minutes=10),
            end_at=timezone.now() + timedelta(minutes=20),
            status='online',
            per_user_limit=1,
        )
        reservation = SeckillReservation.objects.create(
            activity=activity,
            product=self.product,
            user=self.user,
            quantity=2,
            status='ordered',
            reserved_expires_at=timezone.now() + timedelta(minutes=5),
            order=order,
        )
        result = cleanup_expired_orders()

        order.refresh_from_db()
        self.product.refresh_from_db()
        user_coupon.refresh_from_db()
        activity.refresh_from_db()
        reservation.refresh_from_db()

        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.product.stock, 12)
        self.assertEqual(self.product.sales, 1)
        self.assertEqual(user_coupon.status, UserCoupon.STATUS_UNUSED)
        self.assertEqual(activity.reserved_stock, 0)
        self.assertEqual(reservation.status, 'expired')
        self.assertEqual(result['cleaned'], 1)

    def test_order_list_no_longer_triggers_cleanup_side_effect(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('20.00'),
            status='pending',
            payment_status='pending',
            address=self.address,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=Decimal('20.00'))
        self.client.force_authenticate(self.user)

        resp = self.client.get('/api/orders/orders/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
