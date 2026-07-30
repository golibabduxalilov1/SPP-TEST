from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Machine, Operation, Tsex
from orders.constants import DEFAULT_ROUTE_KEY, OPERATION_SEEDS, ROUTE_TEMPLATES
from orders.models import Order, OrderDetail, PartRoute
from orders.production_workflow import approve_order, complete_current_stage
from packaging.models import Package
from orders.services import create_part_for_order_detail
from terminalapp.models import ScanEvent
from terminalapp.services import process_scan

from .tablo import build_production_table


def _ensure_stage_operations_seeded():
    """Guards against a known pre-existing gap (see project memory
    project-seed-data-gap): OPERATION_SEEDS in orders/constants.py has no
    seeding migration, so a fresh test DB has no ARRA/KROMKA/PRISADKA/...
    rows and route assignment (assign_route/approve_order) silently finds no
    operations. Keeps these Tablo tests self-sufficient regardless of
    whether that migration gap has been fixed elsewhere."""
    for seed in OPERATION_SEEDS:
        Operation.objects.get_or_create(code=seed["code"], defaults=seed)


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
        _ensure_stage_operations_seeded()
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
        _ensure_stage_operations_seeded()
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
        # KROMKA is meter-measured: (1000+1000)*2*1/1000 + (1000+850)*2*1/1000 = 4.0 + 3.7 = 7.7m
        self.assertEqual(row["cells"]["KROMKA"]["value"], 7.7, "meter-measured stage must show edge length, not area")


class ProductionTableModeTests(TestCase):
    """Hajm/Soni/Foiz must each apply one consistent rule across every
    stage, per the board's Tablo mode spec: Hajm shows each stage's own
    measure_unit figure (m2 -> area, meter -> edge, piece -> quantity,
    package -> existing package count), Soni = dona everywhere, Foiz =
    unchanged existing 0/100 status logic."""

    def setUp(self):
        _ensure_stage_operations_seeded()
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

    def test_hajm_mode_shows_each_stages_own_unit_figure(self):
        # Stage set is whatever the order's actual route is, not a hardcoded
        # list — stays correct even if OPERATION_SEEDS/ROUTE_TEMPLATES change.
        # Each stage's expected value is driven entirely by its own
        # measure_unit (m2/meter/piece/package), never by its code.
        route_codes = ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY]
        for code in ("ARRA", "KROMKA", "PRISADKA", "OMBOR"):
            self.assertIn(code, route_codes, f"this test needs {code} in the default route to be meaningful")

        row = self._row("hajm")
        # 1000mm x 500mm x 4: area = 2.0 m2, edge = (1000+500)*2*4/1000 = 12.0m
        self.assertEqual(row["cells"]["ARRA"]["value"], 2.0, "m2-measured stage must show area")
        self.assertEqual(row["cells"]["KROMKA"]["value"], 12.0, "meter-measured stage must show edge length")
        self.assertEqual(row["cells"]["PRISADKA"]["value"], 4, "piece-measured stage must show quantity")
        # OMBOR (package-measured): order hasn't reached it yet, so 0 real packages exist.
        self.assertEqual(row["cells"]["OMBOR"]["value"], 0, "package-measured stage must show existing package count, not area")

    def test_hajm_mode_piece_rule_is_measure_unit_driven(self):
        # Any user-created stage measured in "piece" gets the dona-instead-
        # of-m2 treatment, not just the specific code "PRISADKA" — the rule
        # is driven entirely by Operation.measure_unit.
        custom_piece_stage = Operation.objects.create(
            code="CUSTOM_PIECE", name="Maxsus dona bosqich", measure_unit="piece", order_index=4,
        )
        custom_area_stage = Operation.objects.create(
            code="CUSTOM_AREA", name="Maxsus m2 bosqich", measure_unit="m2", order_index=5,
        )
        for stage in (custom_piece_stage, custom_area_stage):
            PartRoute.objects.create(part=self.detail.part, operation=stage, sequence_index=99, status=PartRoute.Status.PENDING)

        row = self._row("hajm")
        self.assertEqual(row["cells"]["CUSTOM_PIECE"]["value"], 4, "piece-measured stage must show quantity, not area")
        self.assertEqual(row["cells"]["CUSTOM_AREA"]["value"], 2.0, "m2-measured stage must show area")

    def test_hajm_mode_package_shows_real_package_count_once_ombor_completes(self):
        # Completing every stage through OMBOR triggers
        # packaging.services.sync_order_into_warehouse, which creates exactly
        # one Package for the order — that real count, not a hidden m2/piece
        # figure, is what a package-measured stage must show.
        self.assertEqual(Package.objects.filter(order=self.order).count(), 0)
        for _ in range(len(ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY])):
            complete_current_stage(self.order.id, completed_by=self.employee)

        self.assertEqual(Package.objects.filter(order=self.order).count(), 1)
        row = self._row("hajm")
        self.assertEqual(row["cells"]["OMBOR"]["value"], 1, "package-measured stage must show the real package count")

    def test_soni_mode_shows_quantity_everywhere(self):
        route_codes = ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY]
        row = self._row("soni")
        for code in route_codes:
            self.assertEqual(row["cells"][code]["value"], 4, f"{code} must show quantity in Soni mode")

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


class ProductionTableProductQuantityTests(TestCase):
    """Tablo/Soni totals must fold in Order.product_quantity (how many
    identical cabinets were ordered) without double-multiplying — Part.quantity
    already carries detail.quantity x product_quantity, and OrderDetail-driven
    rows must land on the exact same number."""

    def setUp(self):
        _ensure_stage_operations_seeded()
        self.order = Order.objects.create(product_name="Multi-cabinet test", product_quantity=3)
        self.detail = OrderDetail.objects.create(order=self.order, name="Yon panel", quantity=4, length_mm=1000, width_mm=500)
        create_part_for_order_detail(self.detail)
        approve_order(self.order.id)

    def _row(self, mode="soni"):
        result = build_production_table(mode=mode)
        return next(item for item in result["rows"] if item["order_id"] == self.order.id)

    def test_soni_mode_multiplies_detail_quantity_by_product_quantity_once(self):
        row = self._row("soni")
        for code in ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY]:
            self.assertEqual(row["cells"][code]["value"], 12, f"{code} must show 4 x 3 = 12, not 4")

    def test_part_quantity_already_matches_detail_times_product_quantity(self):
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.part.quantity, 12)


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


class DashboardPackageMetricsTests(APITestCase):
    """Dashboard-wide totals must keep package counts in their own bucket —
    never folded into "piece" the way they used to be — and a package-
    measured machine card must reflect the real Package completion count,
    not a part-scan proxy, when it's the sole machine on its stage."""

    def setUp(self):
        _ensure_stage_operations_seeded()
        self.user = User.objects.create_user(
            username="dash-package-admin", phone="+998901113705", password="secret-pass", role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        self.ombor = Operation.objects.get(code="OMBOR")
        tsex = Tsex.objects.create(name="Ombor tsex")
        self.machine = Machine.objects.create(
            machine_id="TEST-OMBOR-1", name="Test Ombor", operation=self.ombor, tsex=tsex, capacity_per_hour="5",
        )
        self.order = Order.objects.create(product_name="Package dashboard test", created_by=self.user)
        detail = OrderDetail.objects.create(order=self.order, name="Fasad", quantity=2, length_mm=1000, width_mm=500)
        create_part_for_order_detail(detail)
        now = timezone.now()
        self.window = {"from": (now - timedelta(hours=1)).isoformat(), "to": (now + timedelta(hours=1)).isoformat()}

    def _finish_order(self):
        approve_order(self.order.id)
        for _ in range(len(ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY])):
            complete_current_stage(self.order.id, completed_by=self.user)

    def test_overview_keeps_package_separate_from_piece(self):
        self._finish_order()

        response = self.client.get("/api/dashboard/overview", self.window)

        self.assertEqual(response.data["output"]["package"], 1.0, "exactly one Package synced for this order")
        self.assertEqual(response.data["output"]["piece"], 2.0, "PRISADKA's own 2-piece total must stay separate")

    def test_sole_machine_on_package_stage_gets_credited_the_real_package_count(self):
        self._finish_order()

        response = self.client.get("/api/dashboard/machines", self.window)
        card = next(m for m in response.data if m["id"] == self.machine.id)

        self.assertEqual(card["unit"], "package")
        self.assertEqual(card["unit_label"], "qadoq")
        self.assertEqual(card["period_volume"], 1.0)
        self.assertEqual(card["period_efficiency"], 10.0, "1 package / (5 qadoq/h * 2h window) * 100")

        series_response = self.client.get(f"/api/dashboard/machines/{self.machine.id}/series", self.window)
        self.assertEqual(series_response.data["period_volume"], 1.0)
        self.assertEqual(series_response.data["unit_label"], "qadoq")
