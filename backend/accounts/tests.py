from rest_framework.test import APITestCase

from .models import Role, User


class AdminLoginTests(APITestCase):
    def test_superuser_can_login_even_with_non_admin_role(self):
        user = User.objects.create_superuser(
            username="admin",
            password="secret-pass",
            role=Role.OPERATOR,
        )

        response = self.client.post(
            "/api/auth/login",
            {"username": user.username, "password": "secret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["username"], user.username)

    def test_non_admin_role_cannot_login_to_admin_panel(self):
        user = User.objects.create_user(
            username="operator",
            password="secret-pass",
            role=Role.OPERATOR,
        )

        response = self.client.post(
            "/api/auth/login",
            {"username": user.username, "password": "secret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_superuser_has_management_api_access_even_with_non_admin_role(self):
        user = User.objects.create_superuser(
            username="root",
            password="secret-pass",
            role=Role.OPERATOR,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/employees/")

        self.assertEqual(response.status_code, 200)

    def test_super_admin_role_is_staff_and_superuser(self):
        user = User.objects.create_user(
            username="superadmin",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
