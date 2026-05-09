from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.cart.models import CartItem
from apps.products.models import Product


class CartAtomicUpdateTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='cart_user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Cart Atomic Product',
            description='cart',
            price=Decimal('19.90'),
            stock=5,
            status=True,
        )
        self.client.force_authenticate(self.user)

    def test_add_merges_existing_item_and_increments_quantity(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)

        resp = self.client.post(
            '/api/cart/add/',
            {'product_id': self.product.id, 'quantity': 2},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 4)

    def test_add_rejects_when_atomic_increment_exceeds_stock(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=4)

        resp = self.client.post(
            '/api/cart/add/',
            {'product_id': self.product.id, 'quantity': 2},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('库存', resp.data['error'])

    def test_update_quantity_rejects_when_stock_is_not_enough(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=1)

        resp = self.client.post(
            '/api/cart/update_quantity/',
            {'cart_item_id': CartItem.objects.get(user=self.user, product=self.product).id, 'quantity': 8},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('库存', resp.data['error'])


class CartConcurrentCreateRecoveryTests(TransactionTestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='cart_race_user',
            password='TestPass123!',
            role='user',
        )
        self.product = Product.objects.create(
            name='Cart Race Product',
            description='cart-race',
            price=Decimal('9.90'),
            stock=20,
            status=True,
        )

    def test_add_recovers_from_get_or_create_race(self):
        client = APIClient()
        client.force_authenticate(self.user)

        original_create = CartItem.objects.create
        call_state = {'count': 0}

        def fake_create(*args, **kwargs):
            call_state['count'] += 1
            if call_state['count'] == 1:
                with transaction.atomic():
                    CartItem.objects.get_or_create(user=self.user, product=self.product, defaults={'quantity': 1})
                from django.db import IntegrityError
                raise IntegrityError('simulated cart create race')
            return original_create(*args, **kwargs)

        with patch('apps.cart.views.CartItem.objects.create', side_effect=fake_create):
            resp = client.post(
                '/api/cart/add/',
                {'product_id': self.product.id, 'quantity': 2},
                format='json',
            )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 3)
