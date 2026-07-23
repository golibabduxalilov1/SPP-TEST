from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Machine, Operation, Tsex
from orders.models import Order, OrderDetail, PartRoute
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
        self.assertEqual(row["cells"]["KROMKA"]["value"], 1.85, "Hajm mode shows m2 for every stage except PRISADKA")


class ProductionTableModeTests(TestCase):
    """Hajm/Soni/Foiz must each apply one consistent rule across every
    stage, per the board's Tablo mode spec: Hajm = m2 everywhere except
    PRISADKA (dona, since drilling is inherently per-piece), Soni = dona
    everywhere, Foiz = unchanged existing 0/100 status logic."""

    def setUp(self):
        self.employee = User.objects.create_user(
            username="tablo-mode-scanner", phone="+998901113602", password="secret-pass", role=Role.OPERATOR,
        )
        self.order = Order.objects.create(product_name="Tablo mode test")
        self.detail = OrderDetail.objects.create(
            order=self.order, name="Fasad", quantity=4, length_mm=1000, width_mm=500,
        )
        create_part_for_order_detail(self.detail)
        approve_order(self.order.id)

    def _row(self, mode):
        result = build_production_table(mode=mode)
        return next(item for item in result["rows"] if item["order_id"] == self.order.id)

    def test_hajm_mode_shows_area_everywhere_except_prisadka(self):
        row = self._row("hajm")
        # 1000mm x 500mm x 4 = 2.0 m2
        self.assertEqual(row["cells"]["ARRA"]["value"], 2.0)
        self.assertEqual(row["cells"]["KROMKA"]["value"], 2.0)
        self.assertEqual(row["cells"]["PRISADKA"]["value"], 4)
        self.assertEqual(row["cells"]["YIGISH"]["value"], 2.0)

    def test_soni_mode_shows_quantity_everywhere(self):
        row = self._row("soni")
        self.assertEqual(row["cells"]["ARRA"]["value"], 4)
        self.assertEqual(row["cells"]["KROMKA"]["value"], 4)
        self.assertEqual(row["cells"]["PRISADKA"]["value"], 4)
        self.assertEqual(row["cells"]["YIGISH"]["value"], 4)

    def test_foiz_mode_status_logic_is_unchanged(self):
        row = self._row("foiz")
        self.assertEqual(row["cells"]["ARRA"]["value"], 0, "not scanned yet at ARRA")

        process_scan(
            client_scan_id="scan-foiz-fasad", qr_token=self.detail.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )

        row = self._row("foiz")
        self.assertEqual(row["cells"]["ARRA"]["value"], 100, "sole detail scanned — stage completed")

    def test_hajm_mode_excludes_details_already_completed_at_in_progress_stage(self):
        second = OrderDetail.objects.create(
            order=self.order, name="Tokcha", quantity=2, length_mm=800, width_mm=400,
        )
        create_part_for_order_detail(second)

        # Whole-order total before any scans: 2.0 (fasad) + 0.64 (tokcha) = 2.64 m2
        row = self._row("hajm")
        self.assertEqual(row["cells"]["ARRA"]["value"], 2.64)

        process_scan(
            client_scan_id="scan-hajm-fasad", qr_token=self.detail.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )

        row = self._row("hajm")
        self.assertEqual(row["cells"]["ARRA"]["status"], "in_progress")
        self.assertEqual(
            row["cells"]["ARRA"]["value"], 0.64,
            "fasad's 2.0 m2 share already scanned at ARRA must drop out of the remaining total",
        )


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
        self.machine = Machine.objects.create(
            machine_id="TEST-ARRA-1", name="Test Arra", operation=self.arra, tsex=tsex,
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

    def test_two_machines_sharing_a_stage_report_independent_stats(self):
        """Two machines assigned to the same stage (e.g. Arra-1 and Arra-2)
        must each show only the work scanned on that specific machine — the
        core requirement behind PartRoute.machine."""
        second_machine = Machine.objects.create(
            machine_id="TEST-ARRA-2", name="Test Arra 2", operation=self.arra, tsex=self.machine.tsex,
            capacity_per_hour="2",
        )

        order = Order.objects.create(product_name="Two machines test", created_by=self.user)
        detail_a = OrderDetail.objects.create(order=order, name="Detal A", quantity=1, length_mm=1000, width_mm=1000)
        detail_b = OrderDetail.objects.create(order=order, name="Detal B", quantity=1, length_mm=2000, width_mm=1000)
        part_a = create_part_for_order_detail(detail_a)
        part_b = create_part_for_order_detail(detail_b)

        self.client.post(f"/api/orders/{order.id}/approve/")

        for part, machine in ((part_a, self.machine), (part_b, second_machine)):
            route = part.routes.get(operation=self.arra)
            route.status = PartRoute.Status.COMPLETED
            route.completed_at = timezone.now()
            route.completed_by = self.user
            route.machine = machine
            route.save(update_fields=["status", "completed_at", "completed_by", "machine"])

        machines_response = self.client.get("/api/dashboard/machines", self.window)
        card_1 = next(m for m in machines_response.data if m["id"] == self.machine.id)
        card_2 = next(m for m in machines_response.data if m["id"] == second_machine.id)
        self.assertEqual(card_1["period_volume"], 1.0, "machine 1 must only reflect its own 1000x1000 detail")
        self.assertEqual(card_2["period_volume"], 2.0, "machine 2 must only reflect its own 2000x1000 detail")

        series_1 = self.client.get(f"/api/dashboard/machines/{self.machine.id}/series", self.window)
        series_2 = self.client.get(f"/api/dashboard/machines/{second_machine.id}/series", self.window)
        self.assertEqual(series_1.data["period_volume"], 1.0)
        self.assertEqual(series_2.data["period_volume"], 2.0)
