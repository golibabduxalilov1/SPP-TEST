from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Operation
from orders.models import Order, Part, PartRoute
from orders.production_workflow import approve_order, complete_current_stage

from .models import Package


class PackagingScanAdvancesBoardStageTests(APITestCase):
    """Packaging scans complete a part's route the same way terminal scans
    do, so they should trigger the same board-stage auto-advance."""

    def setUp(self):
        Operation.objects.all().delete()
        self.stage1 = Operation.objects.create(code="ARRA", name="Arra", measure_unit="m2", order_index=1, is_active=True)
        self.stage2 = Operation.objects.create(
            code="QADOQLASH", name="Qadoqlash", measure_unit="package", order_index=2, is_active=True,
        )
        self.employee = User.objects.create_user(
            username="qadoqchi-scan", phone="+998901113601", password="secret-pass", role=Role.PACKAGING,
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
        complete_current_stage(self.order.id)  # moves the board past stage1, onto stage2 (packaging)
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
        self.assertEqual(self.order.status, Order.Status.COMPLETED)

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
