from rest_framework.test import APITestCase

from accounts.models import Role, User
from manufacturing.models import Operation

from .models import Order, Part


class PartApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="superadmin",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        Operation.objects.create(code="ARRA", name="Arra", measure_unit="m2", order_index=1)
        Operation.objects.create(code="QADOQLASH", name="Qadoqlash", measure_unit="package", order_index=2)
        Operation.objects.create(code="OMBOR", name="Ombor", measure_unit="package", order_index=3)
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
