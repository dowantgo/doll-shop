from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class UserDetailIsolationTests(APITestCase):
    def setUp(self):
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
