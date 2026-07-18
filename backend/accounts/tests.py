from rest_framework.test import APITestCase

from manufacturing.models import Operation, Tsex, Workstation
from orders.models import Order, Part

from .models import Role, User


class LoginTests(APITestCase):
    def test_user_can_login_with_phone_and_password(self):
        user = User.objects.create_superuser(
            username="admin",
            phone="+998901112201",
            password="secret-pass",
        )

        response = self.client.post(
            "/api/auth/login",
            {"phone": user.phone, "password": "secret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["phone"], user.phone)

    def test_non_admin_role_cannot_login_to_admin_panel(self):
        user = User.objects.create_user(
            username="operator",
            phone="+998901112202",
            password="secret-pass",
            role=Role.OPERATOR,
        )

        response = self.client.post(
            "/api/auth/login",
            {"phone": user.phone, "password": "secret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_wrong_password_returns_generic_error(self):
        User.objects.create_user(
            username="pinuser",
            phone="+998901112203",
            password="secret-pass",
            role=Role.OPERATOR,
        )

        response = self.client.post(
            "/api/auth/login",
            {"phone": "+998901112203", "password": "wrong-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Telefon raqam yoki parol noto'g'ri")

    def test_unknown_phone_returns_generic_error(self):
        response = self.client.post(
            "/api/auth/login",
            {"phone": "+998901112299", "password": "whatever123"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Telefon raqam yoki parol noto'g'ri")

    def test_superuser_has_management_api_access_even_with_non_admin_role(self):
        # create_superuser() always forces role=Super Admin now, so this scenario —
        # is_superuser=True with a non-admin role — is built by hand instead.
        user = User.objects.create_user(
            username="root",
            phone="+998901112204",
            password="secret-pass",
            role=Role.OPERATOR,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/employees/")

        self.assertEqual(response.status_code, 200)

    def test_createsuperuser_always_forces_super_admin_role(self):
        user = User.objects.create_superuser(
            username="forced-root",
            phone="+998901112206",
            password="secret-pass",
            role=Role.OPERATOR,
        )
        self.assertEqual(user.role, Role.SUPER_ADMIN)

    def test_super_admin_role_cannot_be_changed(self):
        user = User.objects.create_user(
            username="locked-admin",
            phone="+998901112207",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        user.role = Role.OPERATOR
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.role, Role.SUPER_ADMIN)

    def test_super_admin_role_is_staff_and_superuser(self):
        user = User.objects.create_user(
            username="superadmin",
            phone="+998901112205",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class TerminalPinValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="terminal-user",
            phone="+998901112208",
            password="secret-pass",
            role=Role.OPERATOR,
            pin_code="0123",
        )

    def test_four_digit_pin_is_accepted(self):
        response = self.client.post(
            "/api/auth/terminal-pin-lookup", {"pin_code": "0123"}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)

    def test_lookup_rejects_pin_that_is_not_exactly_four_digits(self):
        for pin_code in ("123", "12345", "12a4", "١٢٣٤"):
            with self.subTest(pin_code=pin_code):
                response = self.client.post(
                    "/api/auth/terminal-pin-lookup", {"pin_code": pin_code}, format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)

    def test_login_rejects_pin_that_is_not_exactly_four_digits(self):
        for pin_code in ("123", "12345", "12a4", "١٢٣٤"):
            with self.subTest(pin_code=pin_code):
                response = self.client.post(
                    "/api/auth/terminal-login",
                    {"pin_code": pin_code, "device_id": "test-device"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)


class SuperAdminMutualProtectionTests(APITestCase):
    """One super admin must not be able to update, deactivate, or delete another
    super admin's account via the /api/employees/ management endpoint."""

    def setUp(self):
        self.actor = User.objects.create_user(
            username="actor-admin",
            phone="+998901112501",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.other = User.objects.create_user(
            username="other-admin",
            phone="+998901112502",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.actor)

    def test_cannot_update_another_super_admin(self):
        response = self.client.patch(
            f"/api/employees/{self.other.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.other.refresh_from_db()
        self.assertNotEqual(self.other.first_name, "Changed")

    def test_cannot_deactivate_another_super_admin(self):
        response = self.client.patch(
            f"/api/employees/{self.other.id}/", {"is_active_employee": False}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_active_employee)

    def test_cannot_delete_another_super_admin(self):
        response = self.client.delete(f"/api/employees/{self.other.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.other.id).exists())


class SuperAdminSelfEditTests(APITestCase):
    """A Super Admin may update their own account via /api/employees/, but never
    their own phone number. Non-super-admin roles still can't self-edit at all."""

    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="self-super",
            phone="+998901112601",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )

    def test_super_admin_can_update_own_non_phone_fields(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/", {"first_name": "Yangilangan"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.first_name, "Yangilangan")

    def test_super_admin_cannot_change_own_phone(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/", {"phone": "+998901112699"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.phone, "+998901112601")

    def test_super_admin_cannot_change_own_role(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/", {"role": Role.OPERATOR}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.role, Role.SUPER_ADMIN)

    def test_resubmitting_same_role_is_allowed(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/",
            {"first_name": "Ok", "role": Role.SUPER_ADMIN},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_resubmitting_same_phone_is_allowed(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/",
            {"first_name": "Ok", "phone": self.super_admin.phone},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_non_super_admin_still_cannot_self_edit(self):
        director = User.objects.create_user(
            username="self-director",
            phone="+998901112602",
            password="secret-pass",
            role=Role.DIRECTOR,
        )
        self.client.force_authenticate(user=director)
        response = self.client.patch(
            f"/api/employees/{director.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class SuperAdminFullAccessTests(APITestCase):
    """Regression guard: a Super Admin (role=super_admin, not just is_superuser=True
    set directly) must retain full CRUD on every module, even if a future change
    adds a new roles_allowed(...) permission somewhere that forgets about it."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="fullaccess-admin",
            phone="+998901112401",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def test_orders_full_crud(self):
        create = self.client.post("/api/orders/", {"product_name": "Test mahsulot"}, format="json")
        self.assertEqual(create.status_code, 201, create.data)
        order_id = create.data["id"]

        update = self.client.patch(f"/api/orders/{order_id}/", {"priority": "urgent"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/orders/{order_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(Order.objects.filter(id=order_id).exists())

    def test_parts_full_crud(self):
        order = Order.objects.create(product_name="Buyurtma")
        create = self.client.post(
            "/api/parts/",
            {"order": order.id, "code": "P-1", "name": "Detal", "quantity": 1},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        part_id = create.data["id"]

        update = self.client.patch(f"/api/parts/{part_id}/", {"status": "in_progress"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/parts/{part_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(Part.objects.filter(id=part_id).exists())

    def test_employees_full_crud(self):
        create = self.client.post(
            "/api/employees/",
            {"username": "yangi-xodim", "phone": "+998901112402", "role": Role.OPERATOR, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        employee_id = create.data["id"]

        update = self.client.patch(f"/api/employees/{employee_id}/", {"first_name": "Yangilangan"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/employees/{employee_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(User.objects.filter(id=employee_id).exists())

    def test_manufacturing_infrastructure_full_crud(self):
        operation = Operation.objects.create(code="TEST-OP", name="Test bosqich", measure_unit="piece")
        tsex = Tsex.objects.create(name="Tsex")

        ws_create = self.client.post(
            "/api/workstations/",
            {"tsex": tsex.id, "operation": operation.id, "name": "Post-1"},
            format="json",
        )
        self.assertEqual(ws_create.status_code, 201, ws_create.data)
        workstation_id = ws_create.data["id"]

        ws_update = self.client.patch(f"/api/workstations/{workstation_id}/", {"status": "maintenance"}, format="json")
        self.assertEqual(ws_update.status_code, 200, ws_update.data)

        machine_create = self.client.post(
            "/api/machines/",
            {"machine_id": "M-1", "name": "Stanok", "operation": operation.id, "workstation": workstation_id},
            format="json",
        )
        self.assertEqual(machine_create.status_code, 201, machine_create.data)
        machine_id = machine_create.data["id"]

        machine_delete = self.client.delete(f"/api/machines/{machine_id}/")
        self.assertEqual(machine_delete.status_code, 204)

        ws_delete = self.client.delete(f"/api/workstations/{workstation_id}/")
        self.assertEqual(ws_delete.status_code, 204)
        self.assertFalse(Workstation.objects.filter(id=workstation_id).exists())
