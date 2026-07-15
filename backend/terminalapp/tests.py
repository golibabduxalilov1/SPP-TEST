from rest_framework.test import APITestCase

from accounts.models import Role, User
from core.models import AuditLog
from orders.models import Order


class OrderQRStatusTests(APITestCase):
    def setUp(self):
        self.warehouse_user = User.objects.create_user(
            username="omborchi", password="secret-pass", role=Role.WAREHOUSE,
        )
        self.operator_user = User.objects.create_user(
            username="operator", password="secret-pass", role=Role.OPERATOR,
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

    def test_operator_role_forbidden(self):
        self.client.force_authenticate(user=self.operator_user)
        response = self.client.post("/api/terminal/order-qr/lookup", {"qr_token": self.order.qr_token}, format="json")
        self.assertEqual(response.status_code, 403)

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
