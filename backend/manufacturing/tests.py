from rest_framework.test import APITestCase

from accounts.models import Role, User
from orders.models import Order, OrderDetail, Part, PartRoute
from orders.production_workflow import approve_order
from orders.services import create_part_for_order_detail

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

    def test_seed_stage_can_be_deleted_once_unused(self):
        # OPERATION_SEEDS is only initial demo data — it must not grant the
        # seeded rows any special runtime protection. Deletion is allowed
        # purely based on whether anything is actually linked to the stage.
        operation = Operation.objects.get(code="ARRA")
        self.client.force_authenticate(user=self.super_admin)

        response = self.client.delete(f"/api/operations/{operation.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Operation.objects.filter(pk=operation.pk).exists())

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

    def test_new_stage_is_included_in_new_orders_route_but_not_existing_ones(self):
        # A new order created after the stage exists must route through it;
        # an order whose part route was already built before the stage
        # existed must be left untouched.
        existing_order = Order.objects.create(product_name="Pre-existing order")
        existing_detail = OrderDetail.objects.create(
            order=existing_order, name="Eski detal", quantity=1, length_mm=500, width_mm=500,
        )
        create_part_for_order_detail(existing_detail)
        existing_codes_before = set(
            existing_detail.part.routes.values_list("operation__code", flat=True)
        )

        self.client.force_authenticate(user=self.super_admin)
        create_response = self.client.post(
            "/api/operations/",
            {"name": "Yangi bosqich", "order_index": 4, "is_active": True},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        new_code = create_response.data["code"]

        new_order = Order.objects.create(product_name="Post-stage order")
        new_detail = OrderDetail.objects.create(
            order=new_order, name="Yangi detal", quantity=1, length_mm=500, width_mm=500,
        )
        create_part_for_order_detail(new_detail)

        new_codes = set(new_detail.part.routes.values_list("operation__code", flat=True))
        self.assertIn(new_code, new_codes, "new active stage must appear in a new order's route")

        existing_detail.part.refresh_from_db()
        existing_codes_after = set(
            existing_detail.part.routes.values_list("operation__code", flat=True)
        )
        self.assertEqual(
            existing_codes_before, existing_codes_after,
            "an already-routed part must not be retroactively changed by a later stage",
        )

    def test_inactive_stage_is_excluded_from_new_orders_route(self):
        self.client.force_authenticate(user=self.super_admin)
        create_response = self.client.post(
            "/api/operations/",
            {"name": "Nofaol boshlanadi", "order_index": 5, "is_active": False},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        inactive_code = create_response.data["code"]

        order = Order.objects.create(product_name="Order with inactive stage")
        detail = OrderDetail.objects.create(
            order=order, name="Detal", quantity=1, length_mm=500, width_mm=500,
        )
        create_part_for_order_detail(detail)

        codes = set(detail.part.routes.values_list("operation__code", flat=True))
        self.assertNotIn(inactive_code, codes)

    def test_new_active_stage_appears_in_terminal_operations_list(self):
        self.client.force_authenticate(user=self.super_admin)
        create_response = self.client.post(
            "/api/operations/",
            {"name": "Terminal uchun bosqich", "order_index": 6, "is_active": True},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)

        self.client.force_authenticate(user=None)
        response = self.client.get("/api/terminal/operations")

        self.assertEqual(response.status_code, 200, response.data)
        codes = [row["code"] for row in response.data]
        self.assertIn(create_response.data["code"], codes)

    def test_new_stage_appears_in_production_report_after_use(self):
        self.client.force_authenticate(user=self.super_admin)
        create_response = self.client.post(
            "/api/operations/",
            {"name": "Hisobot bosqichi", "order_index": 7, "is_active": True},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        stage_code = create_response.data["code"]

        order = Order.objects.create(product_name="Report order")
        part = Part.objects.create(order=order, code="REPORT-PART", name="Detal")
        PartRoute.objects.create(
            part=part, operation_id=create_response.data["id"], sequence_index=1,
            status=PartRoute.Status.IN_PROGRESS,
        )

        response = self.client.get("/api/reports/production")

        self.assertEqual(response.status_code, 200, response.data)
        row = next(r for r in response.data if r["code"] == stage_code)
        self.assertEqual(row["total"], 1)
        self.assertEqual(row["in_progress"], 1)
        self.assertEqual(row["completed"], 0)
