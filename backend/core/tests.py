from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Machine, Operation, Tsex
from orders.constants import DEFAULT_ROUTE_KEY, OPERATION_SEEDS, ROUTE_TEMPLATES
from orders.models import Order, OrderDetail, Part, PartRoute
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

        # ARRA is meter-measured (standard spec): fasad edge = (1000+1000)*2*1/1000 = 4.0,
        # tokcha edge = (1000+850)*2*1/1000 = 3.7, total 7.7m
        row = self._row_for(order.id)
        self.assertEqual(row["cells"]["ARRA"]["status"], "in_progress")
        self.assertEqual(row["cells"]["ARRA"]["completed"], 0.0)
        self.assertEqual(row["cells"]["ARRA"]["remaining"], 7.7)
        self.assertEqual(row["cells"]["ARRA"]["total"], 7.7)

        result = process_scan(
            client_scan_id="scan-fasad", qr_token=fasad.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        self.assertEqual(result["status"], "synced")

        row = self._row_for(order.id)
        self.assertEqual(row["cells"]["ARRA"]["status"], "in_progress", "order must not advance yet — tokcha unscanned")
        self.assertEqual(row["cells"]["ARRA"]["completed"], 4.0, "fasad's 4.0m share must count as completed")
        self.assertEqual(row["cells"]["ARRA"]["remaining"], 3.7, "only tokcha's 3.7m share remains")
        self.assertEqual(row["cells"]["ARRA"]["total"], 7.7)

        result = process_scan(
            client_scan_id="scan-tokcha", qr_token=tokcha.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        self.assertEqual(result["status"], "synced")

        row = self._row_for(order.id)
        self.assertEqual(row["cells"]["ARRA"]["status"], "completed", "last detail scanned — stage must auto-advance")
        self.assertEqual(row["cells"]["ARRA"]["completed"], 7.7, "completed cell must show the full original total")
        self.assertEqual(row["cells"]["ARRA"]["remaining"], 0.0, "a finished stage must show total/0, never regress")
        self.assertEqual(row["cells"]["ARRA"]["total"], 7.7)
        # The next standard stage after ARRA (order_index 1) is ARRA_AVTOMAT
        # (order_index 2), not KROMKA (order_index 3) — the board advances to
        # the immediate next active stage in the route, one at a time.
        self.assertEqual(row["cells"]["ARRA_AVTOMAT"]["status"], "in_progress")
        # ARRA_AVTOMAT is also meter-measured: (1000+1000)*2*1/1000 + (1000+850)*2*1/1000 = 4.0 + 3.7 = 7.7m
        self.assertEqual(row["cells"]["ARRA_AVTOMAT"]["completed"], 0.0)
        self.assertEqual(row["cells"]["ARRA_AVTOMAT"]["remaining"], 7.7, "meter-measured stage must show edge length, not area")
        self.assertEqual(row["cells"]["ARRA_AVTOMAT"]["total"], 7.7)


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
        for code in ("ARRA", "KROMKA", "PRISADKA", "QADOQLASH"):
            self.assertIn(code, route_codes, f"this test needs {code} in the default route to be meaningful")

        row = self._row("hajm")
        # ARRA is meter-measured (standard spec): edge = (1000+500)*2*4/1000 = 12.0m.
        # Nothing scanned yet, so every stage is 0 completed / total remaining.
        self.assertEqual((row["cells"]["ARRA"]["completed"], row["cells"]["ARRA"]["remaining"], row["cells"]["ARRA"]["total"]), (0.0, 12.0, 12.0), "meter-measured stage must show edge length")
        self.assertEqual((row["cells"]["KROMKA"]["completed"], row["cells"]["KROMKA"]["remaining"], row["cells"]["KROMKA"]["total"]), (0.0, 12.0, 12.0), "meter-measured stage must show edge length")
        self.assertEqual((row["cells"]["PRISADKA"]["completed"], row["cells"]["PRISADKA"]["remaining"], row["cells"]["PRISADKA"]["total"]), (0, 4, 4), "piece-measured stage must show quantity")
        # QADOQLASH (package-measured): order hasn't reached it yet, so 0/1 package.
        self.assertEqual((row["cells"]["QADOQLASH"]["completed"], row["cells"]["QADOQLASH"]["remaining"], row["cells"]["QADOQLASH"]["total"]), (0, 1, 1), "package-measured stage must show 0/1, not an area figure")

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
        self.assertEqual((row["cells"]["CUSTOM_PIECE"]["completed"], row["cells"]["CUSTOM_PIECE"]["remaining"], row["cells"]["CUSTOM_PIECE"]["total"]), (0, 4, 4), "piece-measured stage must show quantity, not area")
        self.assertEqual((row["cells"]["CUSTOM_AREA"]["completed"], row["cells"]["CUSTOM_AREA"]["remaining"], row["cells"]["CUSTOM_AREA"]["total"]), (0.0, 2.0, 2.0), "m2-measured stage must show area")

    def test_hajm_mode_package_shows_total_zero_once_qadoqlash_completes(self):
        # Completing every stage through QADOQLASH triggers
        # packaging.services.sync_order_into_warehouse, which creates exactly
        # one Package for the order — a finished package-measured stage must
        # show 1/0 (total/0), driven by the stage's own completed status.
        self.assertEqual(Package.objects.filter(order=self.order).count(), 0)
        for _ in range(len(ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY])):
            complete_current_stage(self.order.id, completed_by=self.employee)

        self.assertEqual(Package.objects.filter(order=self.order).count(), 1)
        row = self._row("hajm")
        cell = row["cells"]["QADOQLASH"]
        self.assertEqual(cell["status"], "completed")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (1, 0, 1), "package-measured stage must show total/0 once finished")

    def test_soni_mode_shows_quantity_everywhere(self):
        route_codes = ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY]
        row = self._row("soni")
        for code in route_codes:
            cell = row["cells"][code]
            self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0, 4, 4), f"{code} must show 0/4 quantity in Soni mode")

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

        # ARRA is meter-measured: fasad edge = (1000+500)*2*4/1000 = 12.0,
        # tokcha edge = (800+400)*2*2/1000 = 4.8, whole-order total = 16.8m
        row = self._row("hajm")
        self.assertEqual((row["cells"]["ARRA"]["completed"], row["cells"]["ARRA"]["remaining"], row["cells"]["ARRA"]["total"]), (0.0, 16.8, 16.8))

        process_scan(
            client_scan_id="scan-hajm-fasad", qr_token=self.detail.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )

        row = self._row("hajm")
        self.assertEqual(row["cells"]["ARRA"]["status"], "in_progress")
        self.assertEqual(row["cells"]["ARRA"]["completed"], 12.0, "fasad's 12.0m share already scanned at ARRA must count as completed")
        self.assertEqual(
            row["cells"]["ARRA"]["remaining"], 4.8,
            "fasad's 12.0m share already scanned at ARRA must drop out of the remaining total",
        )
        self.assertEqual(row["cells"]["ARRA"]["total"], 16.8)


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
            cell = row["cells"][code]
            self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0, 12, 12), f"{code} must show 0/12 (4 x 3), not 0/4")

    def test_part_quantity_already_matches_detail_times_product_quantity(self):
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.part.quantity, 12)


class ProductionTableCompletedRemainingFormatTests(TestCase):
    """"Bajarilgan/Qolgan" (completed/remaining) cell format: 0/total before
    any scan, a partial split once some — but not all — details are scanned,
    and total/0 (never regressing to the running total) once the stage is
    fully done. Covered across Hajm's per-unit figures (m2/meter/piece) and
    Soni's always-dona figure, and verifying only a successful QR scan moves
    the needle."""

    def setUp(self):
        _ensure_stage_operations_seeded()
        self.employee = User.objects.create_user(
            username="tablo-format-scanner", phone="+998901113603", password="secret-pass", role=Role.OPERATOR,
        )
        self.order = Order.objects.create(product_name="Tablo format test")
        # 3 + 7 = 10 pieces total, split across two details so scanning just
        # one of them lands on an exact 3/7 split.
        self.small = OrderDetail.objects.create(order=self.order, name="Kichik", quantity=3, length_mm=1000, width_mm=500)
        create_part_for_order_detail(self.small)
        self.big = OrderDetail.objects.create(order=self.order, name="Katta", quantity=7, length_mm=1000, width_mm=500)
        create_part_for_order_detail(self.big)
        approve_order(self.order.id)

    def _row(self, mode="hajm"):
        result = build_production_table(mode=mode)
        return next(item for item in result["rows"] if item["order_id"] == self.order.id)

    def _advance_through(self, codes):
        for code in codes:
            row = self._row()
            self.assertEqual(row["current_stage"], code, f"expected {code} to be the current stage")
            complete_current_stage(self.order.id, completed_by=self.employee)

    def test_soni_mode_0_of_10_before_any_scan(self):
        cell = self._row("soni")["cells"]["ARRA"]
        self.assertEqual(cell["status"], "in_progress")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0, 10, 10))

    def test_soni_mode_3_of_10_after_partial_scan(self):
        process_scan(
            client_scan_id="fmt-soni-small", qr_token=self.small.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("soni")["cells"]["ARRA"]
        self.assertEqual(cell["status"], "in_progress")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (3, 7, 10))

    def test_soni_mode_10_of_10_once_stage_completed(self):
        process_scan(
            client_scan_id="fmt-soni-small-full", qr_token=self.small.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        process_scan(
            client_scan_id="fmt-soni-big-full", qr_token=self.big.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("soni")["cells"]["ARRA"]
        self.assertEqual(cell["status"], "completed")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (10, 0, 10), "finished stage must show total/0, not regress")

    def test_hajm_mode_meter_unit_0_3_10_split(self):
        # ARRA is meter-measured: small edge = (1000+500)*2*3/1000 = 9.0,
        # big edge = (1000+500)*2*7/1000 = 21.0, total 30.0m
        cell = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0.0, 30.0, 30.0))

        process_scan(
            client_scan_id="fmt-hajm-meter-small", qr_token=self.small.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual(cell["status"], "in_progress")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (9.0, 21.0, 30.0))

        process_scan(
            client_scan_id="fmt-hajm-meter-big", qr_token=self.big.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual(cell["status"], "completed")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (30.0, 0.0, 30.0))

    def test_hajm_mode_m2_unit_0_split_and_completed_split(self):
        self._advance_through(["ARRA", "ARRA_AVTOMAT", "KROMKA", "OVAL_KROMKA", "PRISADKA"])

        row = self._row("hajm")
        self.assertEqual(row["current_stage"], "NAQSH_ROVER")
        # small area = 1000*500*3/1e6 = 1.5, big area = 1000*500*7/1e6 = 3.5, total 5.0m2
        cell = row["cells"]["NAQSH_ROVER"]
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0.0, 5.0, 5.0))

        process_scan(
            client_scan_id="fmt-hajm-m2-small", qr_token=self.small.part.qr_token, operation_code="NAQSH_ROVER",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("hajm")["cells"]["NAQSH_ROVER"]
        self.assertEqual(cell["status"], "in_progress")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (1.5, 3.5, 5.0))

        process_scan(
            client_scan_id="fmt-hajm-m2-big", qr_token=self.big.part.qr_token, operation_code="NAQSH_ROVER",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("hajm")["cells"]["NAQSH_ROVER"]
        self.assertEqual(cell["status"], "completed")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (5.0, 0.0, 5.0))

    def test_hajm_mode_piece_dona_unit_0_3_10_split(self):
        self._advance_through(["ARRA", "ARRA_AVTOMAT", "KROMKA", "OVAL_KROMKA"])

        row = self._row("hajm")
        self.assertEqual(row["current_stage"], "PRISADKA")
        cell = row["cells"]["PRISADKA"]
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0, 10, 10))

        process_scan(
            client_scan_id="fmt-hajm-piece-small", qr_token=self.small.part.qr_token, operation_code="PRISADKA",
            employee=self.employee, device_id="dev-1",
        )
        cell = self._row("hajm")["cells"]["PRISADKA"]
        self.assertEqual(cell["status"], "in_progress")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (3, 7, 10))

    def test_pending_stage_shows_0_of_total_not_a_dash(self):
        cell = self._row("hajm")["cells"]["QADOQLASH"]
        self.assertEqual(cell["status"], "pending")
        self.assertEqual((cell["completed"], cell["remaining"], cell["total"]), (0, 1, 1))

    def test_not_required_stage_still_shows_a_dash(self):
        custom_stage = Operation.objects.create(
            code="FMT_NOT_REQUIRED", name="Yo'q bosqich", measure_unit="piece", order_index=100,
        )
        cell = self._row("hajm")["cells"]["FMT_NOT_REQUIRED"]
        self.assertEqual(cell["status"], "not_required")
        self.assertIsNone(cell["completed"])
        self.assertIsNone(cell["remaining"])
        self.assertIsNone(cell["total"])
        self.assertEqual(custom_stage.measure_unit, "piece")

    def test_only_a_successful_scan_moves_the_count_duplicate_scans_do_not(self):
        process_scan(
            client_scan_id="fmt-dup-first", qr_token=self.small.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        before = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual((before["completed"], before["remaining"], before["total"]), (9.0, 21.0, 30.0))

        duplicate = process_scan(
            client_scan_id="fmt-dup-second", qr_token=self.small.part.qr_token, operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        self.assertEqual(duplicate["status"], "conflict")
        self.assertEqual(duplicate["error_code"], "duplicate_scan")

        after = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual(
            (after["completed"], after["remaining"], after["total"]), (9.0, 21.0, 30.0),
            "a rejected duplicate scan must not change the count",
        )

    def test_invalid_scan_does_not_move_the_count(self):
        before = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual((before["completed"], before["remaining"], before["total"]), (0.0, 30.0, 30.0))

        invalid = process_scan(
            client_scan_id="fmt-invalid", qr_token="not-a-real-qr-token", operation_code="ARRA",
            employee=self.employee, device_id="dev-1",
        )
        self.assertEqual(invalid["status"], "conflict")

        after = self._row("hajm")["cells"]["ARRA"]
        self.assertEqual(
            (after["completed"], after["remaining"], after["total"]), (0.0, 30.0, 30.0),
            "a rejected/invalid scan must not change the count",
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
        self.assertEqual(card["period_volume"], 4.0, "1000mm x 1000mm x 1: edge = (1000+1000)*2*1/1000 = 4.0m, same formula Tablo uses")
        self.assertEqual(card["period_efficiency"], 100.0, "4.0m / (2 meter/h * 2h window) * 100")

        series_response = self.client.get(f"/api/dashboard/machines/{self.machine.id}/series", self.window)
        self.assertEqual(series_response.data["period_volume"], 4.0)

        overview_response = self.client.get("/api/dashboard/overview", self.window)
        self.assertEqual(overview_response.data["output"]["meter"], 4.0)

        leaderboard_response = self.client.get("/api/dashboard/leaderboard", {"from": self.window["from"], "to": self.window["to"]})
        row = next(r for r in leaderboard_response.data if r["employee_id"] == self.user.id)
        self.assertEqual(row["output"], 1, "the admin who clicked the button gets credited, not left off entirely")
        self.assertEqual(row["efficiency"], 100.0)

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

        # ARRA is meter-measured: detail_a edge = (1000+1000)*2*1/1000 = 4.0,
        # detail_b edge = (2000+1000)*2*1/1000 = 6.0
        machines_response = self.client.get("/api/dashboard/machines", self.window)
        card_1 = next(m for m in machines_response.data if m["id"] == self.machine.id)
        card_2 = next(m for m in machines_response.data if m["id"] == second_machine.id)
        self.assertEqual(card_1["period_volume"], 4.0, "machine 1 must only reflect its own 1000x1000 detail")
        self.assertEqual(card_2["period_volume"], 6.0, "machine 2 must only reflect its own 2000x1000 detail")

        series_1 = self.client.get(f"/api/dashboard/machines/{self.machine.id}/series", self.window)
        series_2 = self.client.get(f"/api/dashboard/machines/{second_machine.id}/series", self.window)
        self.assertEqual(series_1.data["period_volume"], 4.0)
        self.assertEqual(series_2.data["period_volume"], 6.0)


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
        self.qadoqlash = Operation.objects.get(code="QADOQLASH")
        tsex = Tsex.objects.create(name="Qadoqlash tsex")
        self.machine = Machine.objects.create(
            machine_id="TEST-QADOQLASH-1", name="Test Qadoqlash", operation=self.qadoqlash, tsex=tsex, capacity_per_hour="5",
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
        # Two standard stages are piece-measured (PRISADKA, YIGISH), each
        # contributing its own 2-piece total to the same "piece" bucket.
        self.assertEqual(response.data["output"]["piece"], 4.0, "PRISADKA + YIGISH's 2-piece totals must stay separate from package")

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


class ProductionStageDetailViewTests(APITestCase):
    """GET /api/production/table/<code> — the per-Part drilldown behind a
    tablo column click: backlog list, last accepted scan, scan history."""

    def setUp(self):
        Operation.objects.all().delete()
        self.stage1 = Operation.objects.create(code="ARRA", name="Arra", measure_unit="m2", order_index=1, is_active=True)
        self.stage2 = Operation.objects.create(code="QADOQLASH", name="Qadoqlash", measure_unit="package", order_index=2, is_active=True)
        self.user = User.objects.create_user(
            username="stage-detail-viewer", phone="+998901113801", password="secret-pass", role=Role.MANAGER,
        )
        self.client.force_authenticate(user=self.user)
        self.order = Order.objects.create(order_no="S-100", product_name="Stage detail test")

    def _make_part(self, code):
        part = Part.objects.create(order=self.order, code=code, name="Panel", quantity=2, length_mm=800, width_mm=400)
        PartRoute.objects.create(part=part, operation=self.stage1, sequence_index=1, status=PartRoute.Status.PENDING)
        PartRoute.objects.create(part=part, operation=self.stage2, sequence_index=2, status=PartRoute.Status.PENDING)
        part.current_operation = self.stage1
        part.save(update_fields=["current_operation"])
        return part

    def test_unknown_stage_code_returns_404(self):
        response = self.client.get("/api/production/table/NOPE")
        self.assertEqual(response.status_code, 404)

    def test_backlog_lists_only_parts_not_yet_completed_at_the_stage(self):
        part = self._make_part("S-100-1")
        approve_order(self.order.id)

        response = self.client.get(f"/api/production/table/{self.stage1.code}")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["operation"]["code"], self.stage1.code)
        codes = [row["code"] for row in response.data["parts"]]
        self.assertEqual(codes, [part.code])
        self.assertEqual(response.data["parts"][0]["quantity"], 2)
        self.assertEqual(Decimal(response.data["parts"][0]["length_mm"]), Decimal("800.0"))
        self.assertIsNone(response.data["last_scan"])
        self.assertEqual(response.data["history"], [])

    def test_scanned_part_drops_off_the_backlog_and_appears_as_last_scan(self):
        part = self._make_part("S-100-2")
        self._make_part("S-100-3")  # keeps stage1 in progress at the order level
        approve_order(self.order.id)
        process_scan(
            client_scan_id="stage-detail-scan-1", qr_token=part.qr_token, operation_code=self.stage1.code,
            employee=self.user, device_id="dev-1",
        )

        response = self.client.get(f"/api/production/table/{self.stage1.code}")

        self.assertEqual(response.status_code, 200, response.data)
        codes = [row["code"] for row in response.data["parts"]]
        self.assertNotIn(part.code, codes, "scanned part must have left the stage1 backlog")
        self.assertEqual(response.data["last_scan"]["part_code"], part.code)
        self.assertEqual(len(response.data["history"]), 1)
        self.assertEqual(response.data["history"][0]["status"], ScanEvent.Status.ACCEPTED)

    def test_history_includes_conflicts(self):
        part = self._make_part("S-100-4")
        approve_order(self.order.id)
        process_scan(
            client_scan_id="stage-detail-conflict-1", qr_token=part.qr_token, operation_code=self.stage2.code,
            employee=self.user, device_id="dev-1",
        )

        response = self.client.get(f"/api/production/table/{self.stage2.code}")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["last_scan"], "the rejected scan must not count as a last accepted scan")
        self.assertEqual(len(response.data["history"]), 1)
        self.assertEqual(response.data["history"][0]["status"], ScanEvent.Status.CONFLICT)
        self.assertEqual(response.data["history"][0]["error_code"], "previous_not_completed")
