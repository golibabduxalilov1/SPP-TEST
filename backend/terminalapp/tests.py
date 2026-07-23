from rest_framework.test import APITestCase

from accounts.models import Role, User
from core.models import AuditLog
from manufacturing.models import Operation
from orders.models import Order, Part, PartRoute
from orders.production_workflow import approve_order


class OrderQRStatusTests(APITestCase):
    def setUp(self):
        self.warehouse_user = User.objects.create_user(
            username="omborchi", phone="+998901113401", password="secret-pass", role=Role.WAREHOUSE,
        )
        self.operator_user = User.objects.create_user(
            username="operator", phone="+998901113402", password="secret-pass", role=Role.OPERATOR,
        )
        self.order = Order.objects.create(product_name="Shkaf", status=Order.Status.DRAFT)

    def test_lookup_returns_current_status_and_next_options(self):
        self.client.force_authenticate(user=self.warehouse_user)
        response = self.client.post("/api/terminal/order-qr/lookup", {"qr_token": self.order.qr_token}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], Order.Status.DRAFT)
        next_values = [opt["value"] for opt in response.data["next_statuses"]]
        self.assertEqual(next_values, [Order.Status.APPROVED, Order.Status.CANCELLED])

    def test_lookup_unknown_token_returns_404(self):
        self.client.force_authenticate(user=self.warehouse_user)
        response = self.client.post("/api/terminal/order-qr/lookup", {"qr_token": "SPP-O-NOPE00"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_operator_role_allowed(self):
        # Operator / Usta absorbed the former Qadoqlash operatori's scanning duties
        # when the roles were merged, so it must be allowed here too.
        self.client.force_authenticate(user=self.operator_user)
        response = self.client.post("/api/terminal/order-qr/lookup", {"qr_token": self.order.qr_token}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_status_update_to_allowed_next_status_succeeds_and_logs(self):
        self.client.force_authenticate(user=self.warehouse_user)
        response = self.client.post(
            "/api/terminal/order-qr/update-status",
            {"qr_token": self.order.qr_token, "new_status": Order.Status.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.APPROVED)

        log = AuditLog.objects.get(action="order.qr_status_update", entity_id=str(self.order.id))
        self.assertEqual(log.details["from"], Order.Status.DRAFT)
        self.assertEqual(log.details["to"], Order.Status.APPROVED)
        self.assertEqual(log.details["method"], "qr_scan")
        self.assertEqual(log.actor, self.warehouse_user)

    def test_status_update_to_disallowed_status_is_rejected(self):
        self.client.force_authenticate(user=self.warehouse_user)
        response = self.client.post(
            "/api/terminal/order-qr/update-status",
            {"qr_token": self.order.qr_token, "new_status": Order.Status.DELIVERED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DRAFT)

    def test_delivered_order_has_no_next_statuses(self):
        self.order.status = Order.Status.DELIVERED
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(user=self.warehouse_user)

        response = self.client.post("/api/terminal/order-qr/lookup", {"qr_token": self.order.qr_token}, format="json")
        self.assertEqual(response.data["next_statuses"], [])

    def test_cancelled_order_is_always_a_next_option_from_in_production(self):
        self.order.status = Order.Status.IN_PRODUCTION
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(user=self.warehouse_user)

        response = self.client.post("/api/terminal/order-qr/lookup", {"qr_token": self.order.qr_token}, format="json")
        next_values = [opt["value"] for opt in response.data["next_statuses"]]
        self.assertIn(Order.Status.CANCELLED, next_values)
        self.assertIn(Order.Status.PARTIALLY_READY, next_values)


class ScanAdvancesBoardStageTests(APITestCase):
    """Scanning a part is per-detail; the production board tracks whole-order
    stages separately. A scan that finishes the last detail the board is
    waiting on for its current stage should push the board forward too —
    the same effect as clicking "Bosqichni yakunlash" in Tablo."""

    def setUp(self):
        Operation.objects.all().delete()
        self.stage1 = Operation.objects.create(code="ARRA", name="Arra", measure_unit="m2", order_index=1, is_active=True)
        self.stage2 = Operation.objects.create(code="QADOQLASH", name="Qadoqlash", measure_unit="package", order_index=2, is_active=True)
        self.employee = User.objects.create_user(
            username="usta-scan", phone="+998901113501", password="secret-pass", role=Role.OPERATOR,
        )
        self.order = Order.objects.create(order_no="T-200", product_name="Scan test", created_by=self.employee)
        self.client.force_authenticate(user=self.employee)

    def _make_part(self, code):
        part = Part.objects.create(order=self.order, code=code, name="Panel", quantity=1)
        PartRoute.objects.create(part=part, operation=self.stage1, sequence_index=1, status=PartRoute.Status.PENDING)
        PartRoute.objects.create(part=part, operation=self.stage2, sequence_index=2, status=PartRoute.Status.PENDING)
        part.current_operation = self.stage1
        part.save(update_fields=["current_operation"])
        return part

    def _scan(self, part, scan_id):
        return self.client.post(
            "/api/terminal/scan",
            {"client_scan_id": scan_id, "qr_token": part.qr_token, "operation_code": self.stage1.code},
            format="json",
        )

    def test_scanning_the_only_part_advances_order_to_next_stage(self):
        part = self._make_part("T-200-1")
        approve_order(self.order.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage1)

        response = self._scan(part, "scan-1")

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage2)
        self.assertEqual(self.order.stage_status, Order.StageStatus.IN_PROGRESS)

    def test_stage_only_advances_once_every_part_is_scanned(self):
        part_a = self._make_part("T-200-1")
        part_b = self._make_part("T-200-2")
        approve_order(self.order.id)

        self._scan(part_a, "scan-a")
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage1, "should still wait on part_b")

        response = self._scan(part_b, "scan-b")

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage2)

    def test_scanning_last_stage_completes_the_order(self):
        Operation.objects.filter(id=self.stage2.id).delete()
        part = Part.objects.create(order=self.order, code="T-200-1", name="Panel", quantity=1)
        PartRoute.objects.create(part=part, operation=self.stage1, sequence_index=1, status=PartRoute.Status.PENDING)
        part.current_operation = self.stage1
        part.save(update_fields=["current_operation"])
        approve_order(self.order.id)

        response = self._scan(part, "scan-1")

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.current_stage)
        self.assertEqual(self.order.status, Order.Status.COMPLETED)
