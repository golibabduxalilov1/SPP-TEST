from rest_framework.test import APITestCase

from accounts.models import EmployeeStageMachine, Role, User
from core.models import AuditLog
from manufacturing.models import Machine, Operation, Tsex
from orders.models import Order, Part, PartRoute
from orders.production_workflow import approve_order
from terminalapp.models import ScanEvent


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


class TerminalBootstrapMachineScopingTests(APITestCase):
    """/api/terminal/bootstrap must only surface the machines this specific
    employee is assigned to *at this stage* (via EmployeeStageMachine) —
    not every active machine at the stage, and not machines assigned to
    them at a different stage."""

    def setUp(self):
        tsex = Tsex.objects.create(name="Bootstrap tsex")
        self.arra = Operation.objects.create(code="BOOT-ARRA", name="Arra", measure_unit="m2", order_index=1)
        self.kromka = Operation.objects.create(code="BOOT-KROMKA", name="Kromka", measure_unit="meter", order_index=2)
        self.arra_1 = Machine.objects.create(machine_id="BOOT-ARRA-1", name="Arra-1", operation=self.arra, tsex=tsex)
        self.arra_2 = Machine.objects.create(machine_id="BOOT-ARRA-2", name="Arra-2", operation=self.arra, tsex=tsex)
        self.kromka_1 = Machine.objects.create(machine_id="BOOT-KROMKA-1", name="Kromka-1", operation=self.kromka, tsex=tsex)

        self.employee = User.objects.create_user(
            username="bootstrap-op", phone="+998901113601", password="secret-pass", role=Role.OPERATOR,
            department=tsex, multi_stage_enabled=True,
        )
        self.employee.assigned_operations.set([self.arra, self.kromka])
        EmployeeStageMachine.objects.create(employee=self.employee, machine=self.arra_1)
        EmployeeStageMachine.objects.create(employee=self.employee, machine=self.kromka_1)
        self.client.force_authenticate(user=self.employee)

    def test_bootstrap_scopes_machines_to_the_requested_stage(self):
        response = self.client.get("/api/terminal/bootstrap", {"operation_id": self.arra.id})
        self.assertEqual(response.status_code, 200, response.data)
        machine_ids = {m["id"] for m in response.data["machines"]}
        self.assertEqual(machine_ids, {self.arra_1.id}, "must not include arra_2 (unassigned) or kromka_1 (other stage)")

        response = self.client.get("/api/terminal/bootstrap", {"operation_id": self.kromka.id})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({m["id"] for m in response.data["machines"]}, {self.kromka_1.id})

    def test_unassigned_employee_sees_every_active_machine_at_the_stage(self):
        fallback_employee = User.objects.create_user(
            username="bootstrap-fallback", phone="+998901113602", password="secret-pass", role=Role.OPERATOR,
        )
        self.client.force_authenticate(user=fallback_employee)

        response = self.client.get("/api/terminal/bootstrap", {"operation_id": self.arra.id})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({m["id"] for m in response.data["machines"]}, {self.arra_1.id, self.arra_2.id})


class ScanUndoTests(APITestCase):
    """POST /api/terminal/scan/<id>/undo — the tablo stage page's "Bekor
    qilish" action. Symmetric inverse of process_scan's accept branch."""

    def setUp(self):
        Operation.objects.all().delete()
        self.stage1 = Operation.objects.create(code="ARRA", name="Arra", measure_unit="m2", order_index=1, is_active=True)
        self.stage2 = Operation.objects.create(code="QADOQLASH", name="Qadoqlash", measure_unit="package", order_index=2, is_active=True)
        self.operator = User.objects.create_user(
            username="undo-operator", phone="+998901113701", password="secret-pass", role=Role.OPERATOR,
        )
        self.manager = User.objects.create_user(
            username="undo-manager", phone="+998901113702", password="secret-pass", role=Role.MANAGER,
        )
        self.order = Order.objects.create(order_no="U-100", product_name="Undo test", created_by=self.operator)

    def _make_part(self, code, order=None):
        order = order or self.order
        part = Part.objects.create(order=order, code=code, name="Panel", quantity=3)
        PartRoute.objects.create(part=part, operation=self.stage1, sequence_index=1, status=PartRoute.Status.PENDING)
        PartRoute.objects.create(part=part, operation=self.stage2, sequence_index=2, status=PartRoute.Status.PENDING)
        part.current_operation = self.stage1
        part.save(update_fields=["current_operation"])
        return part

    def _scan(self, part, scan_id, operation=None):
        self.client.force_authenticate(user=self.operator)
        return self.client.post(
            "/api/terminal/scan",
            {"client_scan_id": scan_id, "qr_token": part.qr_token, "operation_code": (operation or self.stage1).code},
            format="json",
        )

    def test_undo_reverts_route_part_and_scan_state(self):
        part = self._make_part("U-100-1")
        self._make_part("U-100-2")  # keeps the order-level stage in progress so undo stays legal
        approve_order(self.order.id)
        response = self._scan(part, "undo-scan-1")
        self.assertEqual(response.status_code, 200, response.data)
        scan = ScanEvent.objects.get(client_scan_id="undo-scan-1")

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(f"/api/terminal/scan/{scan.id}/undo")

        self.assertEqual(response.status_code, 200, response.data)
        route = PartRoute.objects.get(part=part, operation=self.stage1)
        self.assertEqual(route.status, PartRoute.Status.PENDING)
        self.assertIsNone(route.completed_at)
        self.assertIsNone(route.completed_by)

        part.refresh_from_db()
        self.assertEqual(part.current_operation, self.stage1)
        self.assertEqual(part.status, Part.Status.PENDING, "no other route was ever completed, so it reverts to PENDING")

        scan.refresh_from_db()
        self.assertEqual(scan.status, ScanEvent.Status.UNDONE)
        self.assertTrue(AuditLog.objects.filter(action="scan.undo", entity_id=str(scan.id)).exists())

    def test_operator_role_cannot_undo(self):
        part = self._make_part("U-100-3")
        approve_order(self.order.id)
        response = self._scan(part, "undo-scan-2")
        self.assertEqual(response.status_code, 200, response.data)
        scan = ScanEvent.objects.get(client_scan_id="undo-scan-2")

        self.client.force_authenticate(user=self.operator)
        response = self.client.post(f"/api/terminal/scan/{scan.id}/undo")
        self.assertEqual(response.status_code, 403)

    def test_cannot_undo_a_scan_twice(self):
        part = self._make_part("U-100-4")
        self._make_part("U-100-5")
        approve_order(self.order.id)
        response = self._scan(part, "undo-scan-3")
        self.assertEqual(response.status_code, 200, response.data)
        scan = ScanEvent.objects.get(client_scan_id="undo-scan-3")

        self.client.force_authenticate(user=self.manager)
        first = self.client.post(f"/api/terminal/scan/{scan.id}/undo")
        self.assertEqual(first.status_code, 200, first.data)
        second = self.client.post(f"/api/terminal/scan/{scan.id}/undo")
        self.assertEqual(second.status_code, 400)

    def test_cannot_undo_once_order_level_stage_is_completed(self):
        # A single-part order: scanning it finishes everyone the board is
        # waiting on for stage1, so process_scan auto-advances the order
        # (see ScanAdvancesBoardStageTests) — that scan must no longer be
        # undoable, since reverting the route alone would leave
        # OrderStageProgress out of sync with it.
        part = self._make_part("U-100-6")
        approve_order(self.order.id)
        response = self._scan(part, "undo-scan-4")
        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage2, "stage1 must have auto-completed at the order level")
        scan = ScanEvent.objects.get(client_scan_id="undo-scan-4")

        self.client.force_authenticate(user=self.manager)
        response = self.client.post(f"/api/terminal/scan/{scan.id}/undo")

        self.assertEqual(response.status_code, 400, response.data)
        route = PartRoute.objects.get(part=part, operation=self.stage1)
        self.assertEqual(route.status, PartRoute.Status.COMPLETED, "must be left untouched")
