from rest_framework.test import APITestCase

from accounts.models import Role, User
from orders.models import Order, Part, PartRoute
from orders.production_workflow import approve_order

from .models import Operation


class OperationApiTests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="stage-admin",
            phone="+998901119001",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.manager = User.objects.create_user(
            username="stage-manager",
            phone="+998901119002",
            password="secret-pass",
            role=Role.MANAGER,
        )

    def test_super_admin_can_create_stage_without_managing_internal_code(self):
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.post(
            "/api/operations/",
            {"name": "Silliqlash", "order_index": 10, "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        operation = Operation.objects.get(pk=response.data["id"])
        self.assertEqual(operation.code, "SILLIQLASH")
        self.assertEqual(operation.measure_unit, "piece")
        self.assertTrue(operation.is_active)

    def test_created_active_stage_automatically_appears_in_production_table(self):
        self.client.force_authenticate(user=self.super_admin)
        create_response = self.client.post(
            "/api/operations/",
            {"name": "Avtomatik tablo bosqichi", "order_index": 10, "is_active": True},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)

        table_response = self.client.get("/api/production/table")

        self.assertEqual(table_response.status_code, 200, table_response.data)
        codes = [stage["code"] for stage in table_response.data["operations"]]
        self.assertIn(create_response.data["code"], codes)

        self.client.patch(
            f"/api/operations/{create_response.data['id']}/",
            {"is_active": False},
            format="json",
        )
        refreshed_response = self.client.get("/api/production/table")
        refreshed_codes = [stage["code"] for stage in refreshed_response.data["operations"]]
        self.assertNotIn(create_response.data["code"], refreshed_codes)

    def test_name_update_keeps_stable_code(self):
        operation = Operation.objects.create(
            code="POLIROVKA", name="Polirovka", measure_unit="piece", order_index=10,
        )
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.patch(
            f"/api/operations/{operation.id}/",
            {"name": "Yakuniy silliqlash", "order_index": 11},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        operation.refresh_from_db()
        self.assertEqual(operation.code, "POLIROVKA")
        self.assertEqual(operation.name, "Yakuniy silliqlash")
        self.assertEqual(operation.order_index, 11)

    def test_non_super_admin_cannot_mutate_stages(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            "/api/operations/",
            {"name": "Ruxsatsiz", "order_index": 10},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_list_stages_and_filter_active(self):
        Operation.objects.create(
            code="NOFAOL_TEST", name="Nofaol test", measure_unit="piece", order_index=99, is_active=False,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/operations/", {"is_active": "true"})

        self.assertEqual(response.status_code, 200)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertTrue(rows)
        self.assertTrue(all(row["is_active"] for row in rows))

    def test_default_stage_cannot_be_deleted(self):
        operation = Operation.objects.get(code="ARRA")
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.delete(f"/api/operations/{operation.id}/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Default", response.data["detail"])
        self.assertTrue(Operation.objects.filter(pk=operation.pk).exists())

    def test_stage_linked_to_active_order_cannot_be_deleted(self):
        operation = Operation.objects.create(
            code="ACTIVE_LINK", name="Faol bog'lanish", measure_unit="piece", order_index=20,
        )
        order = Order.objects.create(product_name="Test", status=Order.Status.IN_PRODUCTION)
        part = Part.objects.create(order=order, code="STAGE-PART", name="Detal", current_operation=operation)
        PartRoute.objects.create(part=part, operation=operation, sequence_index=1)
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.delete(f"/api/operations/{operation.id}/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("faol buyurtma", response.data["detail"])
        self.assertTrue(Operation.objects.filter(pk=operation.pk).exists())

    def test_unused_custom_stage_can_be_deleted(self):
        operation = Operation.objects.create(
            code="DELETE_ME", name="O'chiriladigan", measure_unit="piece", order_index=20,
        )
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.delete(f"/api/operations/{operation.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Operation.objects.filter(pk=operation.pk).exists())

    def test_deactivating_current_stage_advances_stuck_orders(self):
        arra = Operation.objects.get(code="ARRA")
        kromka = Operation.objects.get(code="KROMKA")
        order = Order.objects.create(product_name="Stuck on deactivated stage")
        approve_order(order.id)
        order.refresh_from_db()
        self.assertEqual(order.current_stage, arra)

        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(f"/api/operations/{arra.id}/", {"is_active": False}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.current_stage, kromka)
        self.assertEqual(order.stage_status, Order.StageStatus.IN_PROGRESS)

    def test_deactivating_a_stage_orders_are_not_on_does_nothing(self):
        arra = Operation.objects.get(code="ARRA")
        kromka = Operation.objects.get(code="KROMKA")
        order = Order.objects.create(product_name="Not on kromka")
        approve_order(order.id)
        order.refresh_from_db()
        self.assertEqual(order.current_stage, arra)

        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(f"/api/operations/{kromka.id}/", {"is_active": False}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.current_stage, arra, "order wasn't parked on the deactivated stage")
