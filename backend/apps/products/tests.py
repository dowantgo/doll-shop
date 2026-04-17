from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Product


class AdminProductValidationTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='admin_api_tester',
            password='TestPass123!',
            role='admin',
        )
        self.client.force_authenticate(user=self.admin)
        self.url = '/api/admin/products/'

    def test_admin_product_rejects_negative_price(self):
        payload = {
            'name': 'Invalid Price Product',
            'description': 'test',
            'price': '-1.00',
            'stock': 10,
            'status': True,
        }

        resp = self.client.post(self.url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price', resp.data)
        self.assertEqual(Product.objects.count(), 0)

    def test_admin_product_rejects_negative_stock(self):
        payload = {
            'name': 'Invalid Stock Product',
            'description': 'test',
            'price': '1.00',
            'stock': -1,
            'status': True,
        }

        resp = self.client.post(self.url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock', resp.data)
        self.assertEqual(Product.objects.count(), 0)

    def test_admin_product_allows_zero_price_and_zero_stock(self):
        payload = {
            'name': 'Zero Product',
            'description': 'test',
            'price': '0.00',
            'stock': 0,
            'status': True,
        }

        resp = self.client.post(self.url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)
