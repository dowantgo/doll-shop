from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase


class UserDetailIsolationTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(
            username='user_a',
            email='user_a@example.com',
            password='TestPass123!',
            role='user',
        )
        self.user_b = user_model.objects.create_user(
            username='user_b',
            email='user_b@example.com',
            password='TestPass123!',
            role='user',
        )
        self.admin = user_model.objects.create_user(
            username='admin_reader',
            email='admin_reader@example.com',
            password='TestPass123!',
            role='admin',
        )

    def test_normal_user_cannot_read_other_user_detail(self):
        self.client.force_authenticate(self.user_a)
        resp = self.client.get(f'/api/users/users/{self.user_b.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_read_other_user_detail(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f'/api/users/users/{self.user_b.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], self.user_b.id)


class UserSecurityFlowTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='iter5_login_user',
            email='iter5_login@example.com',
            password='TestPass123!',
            role='user',
        )

    @patch('apps.users.views.verify_captcha', return_value=True)
    def test_login_locks_after_five_failures(self, _mock_captcha):
        payload = {
            'username': self.user.username,
            'password': 'wrong-password',
            'captcha_id': 'c1',
            'captcha_code': 'ok',
        }
        for _ in range(4):
            resp = self.client.post('/api/users/users/login/', payload, format='json')
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        final_resp = self.client.post('/api/users/users/login/', payload, format='json')
        self.assertEqual(final_resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_captcha_rate_limit_hits_after_twenty_requests(self):
        for _ in range(20):
            resp = self.client.get('/api/users/users/captcha/')
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        limited = self.client.get('/api/users/users/captcha/')
        self.assertEqual(limited.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch('apps.users.views.send_email_code_util', return_value={'ok': True, 'error': ''})
    def test_email_code_respects_cooldown(self, _mock_send):
        payload = {'email': 'new_user@example.com', 'type': 'register'}
        first = self.client.post('/api/users/users/send_email_code/', payload, format='json')
        second = self.client.post('/api/users/users/send_email_code/', payload, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch('apps.users.views.verify_captcha', return_value=True)
    def test_refresh_token_and_logout_flow(self, _mock_captcha):
        login_resp = self.client.post(
            '/api/users/users/login/',
            {
                'username': self.user.username,
                'password': 'TestPass123!',
                'captcha_id': 'refresh',
                'captcha_code': 'ok',
            },
            format='json',
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertIn('refresh_token', login_resp.cookies)

        refresh_resp = self.client.post('/api/users/users/refresh-token/')
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', refresh_resp.data)

        logout_resp = self.client.post('/api/users/users/logout/')
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)
