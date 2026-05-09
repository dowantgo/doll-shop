from collections import Counter
from pathlib import Path
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from apps.cart.models import CartItem
from apps.products.cache_utils import make_feed_cache_key
from apps.products.meme_seed import CATEGORY_SPECS, build_catalog, render_catalog_images
from apps.products.models import Category, Product, ProductImage
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


class MemeSeedCatalogTests(TestCase):
    def test_catalog_contains_40_products_and_4_categories(self):
        catalog = build_catalog()

        self.assertEqual(len(catalog), 40)
        self.assertEqual(len({item['name'] for item in catalog}), 40)

        category_counts = Counter(item['category_key'] for item in catalog)
        self.assertEqual(
            category_counts,
            Counter({spec.key: 10 for spec in CATEGORY_SPECS}),
        )

        category_names = {item['category_name'] for item in catalog}
        self.assertEqual(category_names, {spec.name for spec in CATEGORY_SPECS})

    def test_render_catalog_images_creates_png_files(self):
        catalog = build_catalog(seed=20260430, batch_name='test_batch')
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = render_catalog_images(catalog[:3], Path(tmpdir))

            self.assertEqual(len(paths), 3)
            for path in paths:
                self.assertTrue(path.exists())
                self.assertEqual(path.suffix.lower(), '.png')


class ResetMemeProductsCommandTests(TestCase):
    def test_command_replaces_products_and_clears_old_cart_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            media_root = Path(tmpdir) / 'media'
            with override_settings(MEDIA_ROOT=media_root):
                user_model = get_user_model()
                user = user_model.objects.create_user(
                    username='seed_test_user',
                    password='SeedPass123!',
                )
                old_category = Category.objects.create(name='old-category', sort_order=1)
                old_product = Product.objects.create(
                    name='old-product',
                    description='old-data',
                    category=old_category,
                    price='9.90',
                    cost='3.00',
                    stock=5,
                    status=True,
                )
                CartItem.objects.create(user=user, product=old_product, quantity=1)

                call_command(
                    'reset_meme_products',
                    seed=20260430,
                    batch_name='test_reset_batch',
                )

        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(Product.objects.count(), 40)
        self.assertEqual(ProductImage.objects.count(), 40)
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertEqual(
            Counter(Category.objects.values_list('name', flat=True)),
            Counter(spec.name for spec in CATEGORY_SPECS),
        )

