from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cart.models import CartItem
from apps.coupons.models import CouponTemplate, UserCoupon
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import Address


class Iter3TradeFlowTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='iter3_user',
            password='TestPass123!',
            role='user',
        )
        self.admin = user_model.objects.create_user(
            username='iter3_admin',
            password='TestPass123!',
            role='admin',
        )
        self.product = Product.objects.create(
            name='Iter3 Product',
            description='iter3',
            price=Decimal('100.00'),
            stock=30,
            status=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138000',
            province='Guizhou',
            city='Guiyang',
            district='Nanming',
            address='Road 1',
            is_default=True,
        )

    def test_price_preview_and_apply_coupon(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        tpl = CouponTemplate.objects.create(
            name='Iter3-30off',
            discount_amount=Decimal('30.00'),
            min_spend_amount=Decimal('100.00'),
            total_quota=100,
            claimed_count=0,
            per_user_limit=1,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=1),
            status='active',
        )
        user_coupon = UserCoupon.objects.create(user=self.user, template=tpl, status='unused')

        self.client.force_authenticate(user=self.user)
        preview_resp = self.client.post(
            '/api/orders/orders/price-preview/',
            {'coupon_id': user_coupon.id},
            format='json',
        )
        self.assertEqual(preview_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(preview_resp.data['subtotal_amount'], '300.00')
        self.assertEqual(preview_resp.data['full_reduction_amount'], '20.00')
        self.assertEqual(preview_resp.data['coupon_discount_amount'], '30.00')
        self.assertEqual(preview_resp.data['final_payable_amount'], '250.00')

        order_resp = self.client.post(
            '/api/orders/orders/create_from_cart/',
            {'address_id': self.address.id, 'remark': ''},
            format='json',
        )
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED)
        order_id = order_resp.data['order_id']

        apply_resp = self.client.post(
            f'/api/orders/orders/{order_id}/apply-coupon/',
            {'coupon_id': user_coupon.id},
            format='json',
        )
        self.assertEqual(apply_resp.status_code, status.HTTP_200_OK)

        order = Order.objects.get(order_id=order_id)
        user_coupon.refresh_from_db()
        self.assertEqual(str(order.total_price), '250.00')
        self.assertEqual(user_coupon.status, 'locked')

    def test_refund_create_and_admin_review(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('199.00'),
            address=self.address,
            payment_status='paid',
            status='paid',
            paid_at=timezone.now(),
        )
        item = OrderItem.objects.create(order=order, product=self.product, quantity=2, price=Decimal('100.00'))

        self.client.force_authenticate(user=self.user)
        create_resp = self.client.post(
            '/api/refunds/',
            {
                'order_id': order.order_id,
                'order_item_id': item.id,
                'quantity': 1,
                'reason': 'No longer needed',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        refund_id = create_resp.data['id']

        self.client.force_authenticate(user=self.admin)
        review_resp = self.client.patch(
            f'/api/admin/refunds/{refund_id}/review/',
            {'action': 'approve', 'note': 'approved'},
            format='json',
        )
        self.assertEqual(review_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(review_resp.data['status'], 'success')

    def test_order_logistics_endpoint(self):
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('100.00'),
            address=self.address,
            payment_status='paid',
            status='paid',
            shipping_status='in_transit',
            shipping_company='sf',
            tracking_no='SF123456789CN',
            paid_at=timezone.now(),
            shipped_at=timezone.now(),
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=Decimal('100.00'))

        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f'/api/orders/orders/{order.id}/logistics/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('provider', resp.data)
        self.assertIn('traces', resp.data)
