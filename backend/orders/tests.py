from rest_framework.test import APITestCase

from accounts.models import Role, User
from core.models import AuditLog
from manufacturing.models import Operation

from .models import Order, Part


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


class PartApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="superadmin",
            phone="+998901113302",
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
