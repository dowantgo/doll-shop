from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from apps.products.cache_utils import make_feed_cache_key
from apps.products.models import Product
from apps.products.services.feed_cache import ProductFeedService, get_feed_cache_stats


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


class AdminProductFeedCacheInvalidationTests(APITransactionTestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='admin_feed_tester',
            password='TestPass123!',
            role='admin',
        )
        self.client.force_authenticate(user=self.admin)
        self.product = Product.objects.create(
            name='Feed Cache Product',
            description='feed test',
            price='19.90',
            stock=10,
            status=True,
        )

    def test_admin_update_product_bumps_feed_cache_version(self):
        cache.clear()
        before_key = make_feed_cache_key('hot-feed', 10)

        resp = self.client.patch(
            f'/api/admin/products/{self.product.id}/',
            {'price': '29.90'},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        after_key = make_feed_cache_key('hot-feed', 10)
        self.assertNotEqual(before_key, after_key)

    def test_product_feed_service_records_cache_hit_and_miss(self):
        cache.clear()

        first = ProductFeedService().get_top_sales(10)
        second = ProductFeedService().get_top_sales(10)
        stats = get_feed_cache_stats()['top-sales']

        self.assertEqual(len(first), 1)
        self.assertEqual(first, second)
        self.assertEqual(stats['miss'], 1)
        self.assertEqual(stats['hit'], 1)
