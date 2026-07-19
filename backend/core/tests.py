from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Machine, Operation, Tsex, Workstation
from orders.models import Order, OrderDetail
from orders.production_workflow import approve_order
from orders.services import create_part_for_order_detail
from terminalapp.models import ScanEvent
from terminalapp.services import process_scan

from .tablo import build_production_table


class ProductionTableStageTests(TestCase):
    def test_columns_are_active_database_stages_in_configured_order(self):
        later = Operation.objects.create(
            code="LATER_STAGE", name="Keyingi bosqich", measure_unit="piece", order_index=51,
        )
        earlier = Operation.objects.create(
            code="EARLIER_STAGE", name="Oldingi bosqich", measure_unit="piece", order_index=50,
        )
        Operation.objects.create(
            code="HIDDEN_STAGE", name="Yashirin bosqich", measure_unit="piece", order_index=49, is_active=False,
        )

        result = build_production_table()
        codes = [operation["code"] for operation in result["operations"]]

        self.assertNotIn("HIDDEN_STAGE", codes)
        self.assertLess(codes.index(earlier.code), codes.index(later.code))

    def test_renamed_stage_is_returned_without_changing_its_code(self):
        operation = Operation.objects.get(code="ARRA")
        operation.name = "Kesish"
        operation.save(update_fields=["name"])

        result = build_production_table()
        stage = next(item for item in result["operations"] if item["code"] == "ARRA")

        self.assertEqual(stage["name"], "Kesish")


class ProductionTableRemainingQuantityTests(TestCase):
    """Scanning a detail at its current stage should shrink that stage's
    board cell by the scanned detail's own share, not leave the static
    whole-order total in place — and once every detail is scanned the stage
    should flip to "completed" showing the full original total again."""

    def setUp(self):
        self.employee = User.objects.create_user(
            username="tablo-scanner", phone="+998901113601", password="secret-pass", role=Role.OPERATOR,
        )

    def _row_for(self, order_id, mode="hajm"):
        result = build_production_table(mode=mode)
        return next(item for item in result["rows"] if item["order_id"] == order_id)

    def test_scanning_details_one_by_one_reduces_then_completes_the_stage(self):
        order = Order.objects.create(product_name="Tablo qty test")
        fasad = OrderDetail.objects.create(order=order, name="Fasad", quantity=1, length_mm=1000, width_mm=1000)
        create_part_for_order_detail(fasad)
        tokcha = OrderDetail.objects.create(order=order, name="Tokcha", quantity=1, length_mm=1000, width_mm=850)
        create_part_for_order_detail(tokcha)
        approve_order(order.id)

        row = self._row_for(order.id)
        self.assertEqual(row["cells"]["ARRA"]["status"], "in_progress")
        self.assertEqual(row["cells"]["ARRA"]["value"], 1.85)  # 1.0 + 0.85 m2

        result = process_scan(
            client_scan_id="scan-fasad", qr_token=fasad.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        self.assertEqual(result["status"], "synced")

        row = self._row_for(order.id)
        self.assertEqual(row["cells"]["ARRA"]["status"], "in_progress", "order must not advance yet — tokcha unscanned")
        self.assertEqual(row["cells"]["ARRA"]["value"], 0.85, "fasad's 1.0 m2 share must be subtracted")

        result = process_scan(
            client_scan_id="scan-tokcha", qr_token=tokcha.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        self.assertEqual(result["status"], "synced")

        row = self._row_for(order.id)
        self.assertEqual(row["cells"]["ARRA"]["status"], "completed", "last detail scanned — stage must auto-advance")
        self.assertEqual(row["cells"]["ARRA"]["value"], 1.85, "completed cell must show the full original total")
        self.assertEqual(row["cells"]["KROMKA"]["status"], "in_progress")
        self.assertEqual(row["cells"]["KROMKA"]["value"], 7.7, "next stage starts at its own full total (edge meters)")


class DashboardMetricsFromPartRouteTests(APITestCase):
    """The Dashboard's per-machine cards and leaderboard used to read only
    ScanEvent, so any stage finished via "Bosqichni yakunlash" (which writes
    no ScanEvent at all) showed up as 0 there despite Tablo showing it
    correctly. They must now read PartRoute completions — the same ground
    truth Tablo uses — so both stay in sync no matter which action
    completed the stage."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="dash-admin", phone="+998901113701", password="secret-pass", role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        self.arra = Operation.objects.get(code="ARRA")
        tsex = Tsex.objects.create(name="Test tsex")
        workstation = Workstation.objects.create(tsex=tsex, operation=self.arra, name="Test Arra post")
        self.machine = Machine.objects.create(
            machine_id="TEST-ARRA-1", name="Test Arra", operation=self.arra, workstation=workstation,
            capacity_per_hour="2",
        )
        now = timezone.now()
        self.window = {"from": (now - timedelta(hours=1)).isoformat(), "to": (now + timedelta(hours=1)).isoformat()}

    def test_bulk_completed_stage_shows_up_on_the_machine_card_with_zero_scans(self):
        order = Order.objects.create(product_name="Dashboard test", created_by=self.user)
        detail = OrderDetail.objects.create(order=order, name="Fasad", quantity=1, length_mm=1000, width_mm=1000)
        create_part_for_order_detail(detail)

        self.client.post(f"/api/orders/{order.id}/approve/")
        response = self.client.post(f"/api/orders/{order.id}/complete-current-stage/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(ScanEvent.objects.exists(), "this scenario must produce zero scan events")

        machines_response = self.client.get("/api/dashboard/machines", self.window)
        card = next(m for m in machines_response.data if m["id"] == self.machine.id)
        self.assertEqual(card["period_volume"], 1.0, "1000mm x 1000mm x 1 = 1.0 m2, same formula Tablo uses")
        self.assertEqual(card["period_efficiency"], 25.0, "1.0 m2 / (2 m2/h * 2h window) * 100")

        series_response = self.client.get(f"/api/dashboard/machines/{self.machine.id}/series", self.window)
        self.assertEqual(series_response.data["period_volume"], 1.0)

        overview_response = self.client.get("/api/dashboard/overview", self.window)
        self.assertEqual(overview_response.data["output"]["m2"], 1.0)

        leaderboard_response = self.client.get("/api/dashboard/leaderboard", {"from": self.window["from"], "to": self.window["to"]})
        row = next(r for r in leaderboard_response.data if r["employee_id"] == self.user.id)
        self.assertEqual(row["output"], 1, "the admin who clicked the button gets credited, not left off entirely")
        self.assertEqual(row["efficiency"], 25.0)
