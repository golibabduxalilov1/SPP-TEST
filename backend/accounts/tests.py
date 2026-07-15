from rest_framework.test import APITestCase

from manufacturing.models import Factory, Operation, Tsex, Workstation
from orders.models import Order, Part

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


class SuperAdminFullAccessTests(APITestCase):
    """Regression guard: a Super Admin (role=super_admin, not just is_superuser=True
    set directly) must retain full CRUD on every module, even if a future change
    adds a new roles_allowed(...) permission somewhere that forgets about it."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="fullaccess-admin",
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
            {"username": "yangi-xodim", "role": Role.OPERATOR, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        employee_id = create.data["id"]

        update = self.client.patch(f"/api/employees/{employee_id}/", {"phone": "+998901234567"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/employees/{employee_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(User.objects.filter(id=employee_id).exists())

    def test_manufacturing_infrastructure_full_crud(self):
        operation = Operation.objects.create(code="TEST-OP", name="Test bosqich", measure_unit="piece")
        factory = Factory.objects.create(name="Fabrika")
        tsex = Tsex.objects.create(factory=factory, name="Tsex")

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
