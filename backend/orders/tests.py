from rest_framework.test import APITestCase

from accounts.models import Role, User
from core.models import AuditLog
from manufacturing.models import Operation

from .models import Order, OrderDetail, OrderStageProgress, Part, PartRoute
from .services import assign_route


class OrderApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="order-creator",
            phone="+998901113301",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.user)

    def test_order_create(self):
        response = self.client.post(
            "/api/orders/",
            {
                "customer_name": "Aziz",
                "customer_phone": "+998901112233",
                "product_name": "Shkaf",
                "notes": "Shoshilinch",
                "priority": "high",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(id=response.data["id"])
        self.assertTrue(order.order_no)
        self.assertEqual(order.customer_name, "Aziz")
        self.assertEqual(order.priority, "high")
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertEqual(order.created_by, self.user)

        self.assertTrue(AuditLog.objects.filter(action="order.create", entity_id=str(order.id)).exists())

    def test_approval_starts_first_stage_and_completion_advances_whole_order(self):
        first_stage, second_stage = list(Operation.objects.filter(is_active=True).order_by("order_index", "id")[:2])
        order = Order.objects.create(product_name="Workflow test", created_by=self.user)
        OrderDetail.objects.create(order=order, name="Yon panel", quantity=2, length_mm=1000, width_mm=500)
        OrderDetail.objects.create(order=order, name="Tokcha", quantity=3, length_mm=800, width_mm=400)

        response = self.client.post(f"/api/orders/{order.id}/approve/")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.APPROVED)
        self.assertEqual(order.current_stage, first_stage)
        self.assertEqual(order.stage_status, Order.StageStatus.IN_PROGRESS)
        self.assertEqual(
            OrderStageProgress.objects.filter(order=order, status=OrderStageProgress.Status.IN_PROGRESS).count(),
            1,
        )

        response = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.IN_PRODUCTION)
        self.assertEqual(order.current_stage, second_stage)
        self.assertEqual(order.stage_status, Order.StageStatus.IN_PROGRESS)
        self.assertEqual(
            OrderStageProgress.objects.get(order=order, stage=first_stage).status,
            OrderStageProgress.Status.COMPLETED,
        )
        self.assertEqual(
            OrderStageProgress.objects.filter(order=order, status=OrderStageProgress.Status.IN_PROGRESS).count(),
            1,
        )

    def test_workflow_skips_stages_none_of_the_orders_parts_route_through(self):
        # "faqat_kesish" only routes through ARRA, QADOQLASH, OMBOR — the
        # board must skip straight past KROMKA/PRISADKA/PAZ/ROVER/STOLYARKA/
        # YIGISH instead of getting stuck "in progress" on one of them.
        order = Order.objects.create(product_name="Route-aware test", created_by=self.user)
        part = Part.objects.create(order=order, code="RT-1", name="Panel", quantity=1)
        assign_route(part, "faqat_kesish")

        self.client.post(f"/api/orders/{order.id}/approve/")
        order.refresh_from_db()
        self.assertEqual(order.current_stage.code, "ARRA")

        response = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.current_stage.code, "QADOQLASH")

    def test_completing_last_stage_marks_order_completed_and_keeps_history(self):
        order = Order.objects.create(product_name="Final workflow test", created_by=self.user)
        OrderDetail.objects.create(order=order, name="Detal", quantity=4)
        self.client.post(f"/api/orders/{order.id}/approve/")
        stage_count = Operation.objects.filter(is_active=True).count()

        for _ in range(stage_count):
            response = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")
            self.assertEqual(response.status_code, 200, response.data)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertIsNone(order.current_stage)
        self.assertEqual(order.stage_status, Order.StageStatus.COMPLETED)
        self.assertEqual(order.stage_progress.count(), stage_count)
        self.assertFalse(order.stage_progress.exclude(status=OrderStageProgress.Status.COMPLETED).exists())
        self.assertEqual(order.stage_progress.exclude(completed_by=self.user).count(), 0)

        table_response = self.client.get("/api/production/table", {"mode": "soni"})
        row = next(item for item in table_response.data["rows"] if item["order_id"] == order.id)
        self.assertTrue(all(cell["status"] == "completed" for cell in row["cells"].values()))
        self.assertTrue(all(cell["value"] == 4 for cell in row["cells"].values()))

    def test_only_approved_workflow_orders_are_shown_and_totals_use_order_details(self):
        order = Order.objects.create(product_name="Board quantity test", created_by=self.user)
        OrderDetail.objects.create(order=order, name="A", quantity=2)
        OrderDetail.objects.create(order=order, name="B", quantity=5)

        draft_table = self.client.get("/api/production/table", {"mode": "soni"}).data
        self.assertFalse(any(item["order_id"] == order.id for item in draft_table["rows"]))

        self.client.post(f"/api/orders/{order.id}/approve/")
        active_table = self.client.get("/api/production/table", {"mode": "soni"}).data
        row = next(item for item in active_table["rows"] if item["order_id"] == order.id)
        statuses = [row["cells"][operation["code"]]["status"] for operation in active_table["operations"]]
        self.assertEqual(statuses[0], "in_progress")
        self.assertTrue(all(status == "pending" for status in statuses[1:]))
        self.assertTrue(all(cell["value"] == 7 for cell in row["cells"].values()))

    def test_status_patch_to_approved_also_starts_workflow(self):
        order = Order.objects.create(product_name="Patched approval", created_by=self.user)

        response = self.client.patch(f"/api/orders/{order.id}/", {"status": Order.Status.APPROVED}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertIsNotNone(order.current_stage)
        self.assertEqual(order.stage_status, Order.StageStatus.IN_PROGRESS)

    def test_approval_without_active_stage_is_rejected_atomically(self):
        Operation.objects.update(is_active=False)
        order = Order.objects.create(product_name="No stages", created_by=self.user)

        response = self.client.post(f"/api/orders/{order.id}/approve/")

        self.assertEqual(response.status_code, 400, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertIsNone(order.current_stage)

    def test_complete_current_stage_self_heals_when_progress_history_is_missing(self):
        # Simulates current_stage/stage_status having been set directly (e.g.
        # a raw Django admin edit) without ever creating an
        # OrderStageProgress row — the board would show the stage as
        # "in_progress" forever with the button unable to advance it.
        stage = Operation.objects.filter(is_active=True).order_by("order_index", "id").first()
        order = Order.objects.create(product_name="Desynced order", created_by=self.user)
        order.current_stage = stage
        order.stage_status = Order.StageStatus.IN_PROGRESS
        order.save(update_fields=["current_stage", "stage_status"])
        self.assertFalse(OrderStageProgress.objects.filter(order=order).exists())

        response = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")

        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertNotEqual(order.current_stage_id, stage.id)
        self.assertEqual(
            OrderStageProgress.objects.get(order=order, stage=stage).status,
            OrderStageProgress.Status.COMPLETED,
        )

    def test_completing_stage_bulk_finishes_unscanned_details_and_starts_next_stage_fresh(self):
        # "Bosqichni yakunlash" is a full-stage shortcut: any detail not
        # individually QR-scanned yet must be swept up too, and the stage
        # the order lands on next must start with none of its own details
        # marked done (each stage tracks completion independently).
        from orders.services import assign_route
        from terminalapp.services import process_scan

        first_stage, second_stage = list(Operation.objects.filter(is_active=True).order_by("order_index", "id")[:2])
        order = Order.objects.create(product_name="Bulk complete test", created_by=self.user)
        scanned_detail = OrderDetail.objects.create(order=order, name="Fasad", quantity=1, length_mm=1000, width_mm=1000)
        unscanned_details = [
            OrderDetail.objects.create(order=order, name=f"Detal {i}", quantity=1, length_mm=800, width_mm=400)
            for i in range(3)
        ]
        for detail in [scanned_detail, *unscanned_details]:
            part = Part.objects.create(
                order=order, code=f"{order.order_no}-{detail.id}", name=detail.name,
                length_mm=detail.length_mm, width_mm=detail.width_mm, quantity=detail.quantity,
            )
            assign_route(part, "oddiy_panel")
            detail.part = part
            detail.save(update_fields=["part"])

        self.client.post(f"/api/orders/{order.id}/approve/")
        order.refresh_from_db()
        self.assertEqual(order.current_stage, first_stage)

        process_scan(
            client_scan_id="bulk-scan-1", qr_token=scanned_detail.part.qr_token, operation_code=first_stage.code,
            employee=self.user, device_id="dev-1",
        )
        self.assertEqual(
            PartRoute.objects.filter(part__order=order, operation=first_stage, status=PartRoute.Status.PENDING).count(),
            3, "only the 3 unscanned details should still be pending",
        )

        response = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")
        self.assertEqual(response.status_code, 200, response.data)

        order.refresh_from_db()
        self.assertEqual(order.current_stage, second_stage)
        self.assertFalse(
            PartRoute.objects.filter(part__order=order, operation=first_stage)
            .exclude(status=PartRoute.Status.COMPLETED).exists(),
            "clicking the button must sweep up every remaining detail at the old stage",
        )
        self.assertFalse(
            PartRoute.objects.filter(part__order=order, operation=second_stage)
            .exclude(status=PartRoute.Status.PENDING).exists(),
            "the new stage must start with all details pending again, independent of the previous stage",
        )

    def test_production_manager_can_complete_but_operator_cannot(self):
        manager = User.objects.create_user(
            username="workflow-manager",
            phone="+998901113303",
            password="secret-pass",
            role=Role.MANAGER,
        )
        operator = User.objects.create_user(
            username="workflow-operator",
            phone="+998901113304",
            password="secret-pass",
            role=Role.OPERATOR,
        )
        order = Order.objects.create(product_name="Permissions", created_by=self.user)
        self.client.post(f"/api/orders/{order.id}/approve/")

        self.client.force_authenticate(user=operator)
        forbidden = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_authenticate(user=manager)
        allowed = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")
        self.assertEqual(allowed.status_code, 200, allowed.data)


class PartApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="superadmin",
            phone="+998901113302",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        Operation.objects.update_or_create(code="ARRA", defaults={"name": "Arra", "measure_unit": "m2", "order_index": 1})
        Operation.objects.update_or_create(code="QADOQLASH", defaults={"name": "Qadoqlash", "measure_unit": "package", "order_index": 2})
        Operation.objects.update_or_create(code="OMBOR", defaults={"name": "Ombor", "measure_unit": "package", "order_index": 3})
        self.order = Order.objects.create(order_no="T-001", product_name="Test", created_by=self.user)

    def test_manual_part_create_assigns_route(self):
        response = self.client.post(
            "/api/parts/",
            {
                "order": self.order.id,
                "code": "P-001",
                "name": "Panel",
                "quantity": 1,
                "route_key": "faqat_kesish",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        part = Part.objects.get(code="P-001")
        self.assertEqual(part.routes.count(), 3)
        self.assertEqual(part.current_operation.code, "ARRA")
