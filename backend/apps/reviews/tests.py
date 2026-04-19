from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.reviews.models import Review
from apps.users.models import Address


class AdminReviewApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='admin_review',
            email='admin_review@example.com',
            password='TestPass123!',
            role='admin',
        )
        self.user = user_model.objects.create_user(
            username='review_user',
            email='review_user@example.com',
            password='TestPass123!',
            role='user',
        )
        address = Address.objects.create(
            user=self.user,
            name='Tester',
            phone='13800138001',
            province='Guizhou',
            city='Guiyang',
            district='Yunyan',
            address='Road 2',
            is_default=True,
        )
        product = Product.objects.create(
            name='Review Product',
            description='review test',
            price=Decimal('9.90'),
            stock=100,
            status=True,
        )
        order = Order.objects.create(
            user=self.user,
            total_price=Decimal('9.90'),
            status='paid',
            payment_status='paid',
            address=address,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            price=Decimal('9.90'),
        )
        self.review = Review.objects.create(
            order_item=order_item,
            product=product,
            user=self.user,
            rating=5,
            content='good',
            status=Review.STATUS_APPROVED,
        )

        self.client.force_authenticate(self.admin)

    def test_admin_review_list_route_exists(self):
        resp = self.client.get('/api/admin/reviews/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_review_audit_route_exists(self):
        resp = self.client.patch(
            f'/api/admin/reviews/{self.review.id}/audit/',
            {'status': 'approved'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('message', resp.data)
