from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Operation
from orders.models import Order, Part, PartRoute
from orders.production_workflow import ProductionWorkflowError, approve_order, complete_current_stage

from .models import Package, PackageItem
from .services import sync_order_into_warehouse


class PackagingScanAdvancesBoardStageTests(APITestCase):
    """Packaging scans complete a part's route the same way terminal scans
    do, so they should trigger the same board-stage auto-advance."""

    def setUp(self):
        Operation.objects.all().delete()
        self.stage1 = Operation.objects.create(code="ARRA", name="Arra", measure_unit="m2", order_index=1, is_active=True)
        self.stage2 = Operation.objects.create(
            code="OMBOR", name="Tayyor ombor", measure_unit="package", order_index=2, is_active=True,
        )
        self.employee = User.objects.create_user(
            username="qadoqchi-scan", phone="+998901113601", password="secret-pass", role=Role.OPERATOR,
        )
        self.order = Order.objects.create(order_no="T-300", product_name="Packaging test", created_by=self.employee)
        self.client.force_authenticate(user=self.employee)

    def _make_part(self, code):
        part = Part.objects.create(order=self.order, code=code, name="Panel", quantity=1)
        PartRoute.objects.create(
            part=part, operation=self.stage1, sequence_index=1,
            status=PartRoute.Status.COMPLETED, completed_at=timezone.now(),
        )
        PartRoute.objects.create(part=part, operation=self.stage2, sequence_index=2, status=PartRoute.Status.PENDING)
        part.current_operation = self.stage2
        part.save(update_fields=["current_operation"])
        return part

    def test_packaging_scan_of_last_part_completes_the_order(self):
        part = self._make_part("T-300-1")
        approve_order(self.order.id)
        complete_current_stage(self.order.id)  # moves the board past stage1, onto stage2 (OMBOR/packaging)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage2)

        package = Package.objects.create(order=self.order, created_by=self.employee)
        response = self.client.post(
            "/api/packaging/scan",
            {"package_id": package.id, "qr_token": part.qr_token},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.current_stage)
        self.assertEqual(self.order.status, Order.Status.WAREHOUSE)

    def test_stage_waits_for_every_part_to_be_packaged(self):
        part_a = self._make_part("T-300-1")
        part_b = self._make_part("T-300-2")
        approve_order(self.order.id)
        complete_current_stage(self.order.id)

        package = Package.objects.create(order=self.order, created_by=self.employee)
        response = self.client.post(
            "/api/packaging/scan",
            {"package_id": package.id, "qr_token": part_a.qr_token},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.stage2, "should still wait on part_b")


class OmborStageWarehouseSyncTests(APITestCase):
    """Finishing the OMBOR board stage must make the order show up on the
    Tayyor ombor screen — a Package is the only thing that screen reads from,
    but the whole-order "Bosqichni yakunlash" fast path (and any QR scan that
    triggers it) never runs the packaging terminal flow that normally
    creates one."""

    def setUp(self):
        Operation.objects.all().delete()
        self.qadoqlash = Operation.objects.create(
            code="QADOQLASH", name="Qadoqlash", measure_unit="package", order_index=1, is_active=True,
        )
        self.ombor = Operation.objects.create(
            code="OMBOR", name="Tayyor ombor", measure_unit="package", order_index=2, is_active=True,
        )
        self.employee = User.objects.create_user(
            username="omborchi-sync", phone="+998901113701", password="secret-pass", role=Role.WAREHOUSE,
        )
        self.order = Order.objects.create(order_no="T-400", product_name="Ombor sync test", created_by=self.employee)
        self.client.force_authenticate(user=self.employee)

    def _make_part(self, code):
        part = Part.objects.create(order=self.order, code=code, name="Panel", quantity=1)
        PartRoute.objects.create(
            part=part, operation=self.qadoqlash, sequence_index=1,
            status=PartRoute.Status.COMPLETED, completed_at=timezone.now(),
        )
        PartRoute.objects.create(part=part, operation=self.ombor, sequence_index=2, status=PartRoute.Status.PENDING)
        part.current_operation = self.ombor
        part.save(update_fields=["current_operation"])
        return part

    def _advance_to_ombor(self):
        approve_order(self.order.id)
        complete_current_stage(self.order.id, completed_by=self.employee)  # finishes QADOQLASH, lands on OMBOR
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.ombor)

    def test_ombor_completion_creates_package_when_missing(self):
        self._make_part("T-400-1")
        self._advance_to_ombor()

        complete_current_stage(self.order.id, completed_by=self.employee)

        self.assertEqual(Package.objects.filter(order=self.order).count(), 1)

    def test_created_package_status_is_warehouse(self):
        self._make_part("T-400-1")
        self._advance_to_ombor()

        complete_current_stage(self.order.id, completed_by=self.employee)

        package = Package.objects.get(order=self.order)
        self.assertEqual(package.status, Package.Status.WAREHOUSE)

    def test_order_status_is_warehouse(self):
        self._make_part("T-400-1")
        self._advance_to_ombor()

        complete_current_stage(self.order.id, completed_by=self.employee)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.WAREHOUSE)

    def test_warehouse_packages_endpoint_returns_synced_package(self):
        self._make_part("T-400-1")
        self._advance_to_ombor()
        complete_current_stage(self.order.id, completed_by=self.employee)

        response = self.client.get("/api/warehouse/packages")

        self.assertEqual(response.status_code, 200, response.data)
        order_nos = [row["order_no"] for row in response.data]
        self.assertIn(self.order.order_no, order_nos)

    def test_existing_package_reused_instead_of_creating_new_one(self):
        self._make_part("T-400-1")
        self._advance_to_ombor()
        existing = Package.objects.create(order=self.order, created_by=self.employee, status=Package.Status.COMPLETED)

        complete_current_stage(self.order.id, completed_by=self.employee)

        self.assertEqual(Package.objects.filter(order=self.order).count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.status, Package.Status.WAREHOUSE)

    def test_repeating_ombor_completion_does_not_duplicate_package(self):
        self._make_part("T-400-1")
        self._advance_to_ombor()
        complete_current_stage(self.order.id, completed_by=self.employee)

        # The board can no longer "complete" a stage that no longer exists on
        # the order (current_stage is now None) — this is the same guard
        # that already stops any other stage from being re-completed.
        with self.assertRaises(ProductionWorkflowError):
            complete_current_stage(self.order.id, completed_by=self.employee)

        self.assertEqual(Package.objects.filter(order=self.order).count(), 1)

        # The sync helper itself must also be idempotent in isolation, since
        # more than one caller (terminal scan, admin button, cascading
        # packaging completion) can reach it.
        self.order.refresh_from_db()
        sync_order_into_warehouse(self.order, employee=self.employee)
        sync_order_into_warehouse(self.order, employee=self.employee)
        self.assertEqual(Package.objects.filter(order=self.order).count(), 1)

    def test_existing_package_items_are_preserved(self):
        part = self._make_part("T-400-1")
        self._advance_to_ombor()
        existing = Package.objects.create(order=self.order, created_by=self.employee, status=Package.Status.COMPLETED)
        item = PackageItem.objects.create(package=existing, part=part, scanned_by=self.employee)

        complete_current_stage(self.order.id, completed_by=self.employee)

        self.assertTrue(PackageItem.objects.filter(id=item.id).exists())
        self.assertEqual(PackageItem.objects.filter(package=existing).count(), 1)

    def test_other_stage_completion_does_not_move_package_to_warehouse(self):
        self._make_part("T-400-1")
        approve_order(self.order.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.current_stage, self.qadoqlash)

        complete_current_stage(self.order.id, completed_by=self.employee)  # finishes QADOQLASH, not OMBOR

        self.assertFalse(Package.objects.filter(order=self.order).exists())
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, Order.Status.WAREHOUSE)


class WarehouseDeliveryAfterOmborSyncTests(APITestCase):
    """Once a package auto-created by the OMBOR sync reaches the warehouse,
    the existing "Mijozga topshirish" flow must still close the order out
    exactly as it does for manually-packaged orders."""

    def setUp(self):
        self.employee = User.objects.create_user(
            username="omborchi-deliver", phone="+998901113702", password="secret-pass", role=Role.WAREHOUSE,
        )
        self.order = Order.objects.create(order_no="T-401", product_name="Deliver test", created_by=self.employee)
        self.client.force_authenticate(user=self.employee)

    def test_delivering_the_only_package_marks_order_delivered(self):
        package = sync_order_into_warehouse(self.order, employee=self.employee)
        self.assertEqual(package.status, Package.Status.WAREHOUSE)

        response = self.client.post("/api/warehouse/deliver", {"package_id": package.id}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        package.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(package.status, Package.Status.DELIVERED)
        self.assertEqual(self.order.status, Order.Status.DELIVERED)
