from rest_framework.test import APITestCase

from accounts.models import Role, User
from orders.constants import OPERATION_SEEDS, STANDARD_OPERATION_CODES

from .models import Operation


class StandardOperationSeedTests(APITestCase):
    """After a fresh migration, the database must contain exactly the 13
    standard production stages, active, with the codes/order/measure units
    fixed by spec — this is what makes the stage list "standard" instead of
    admin-editable."""

    def test_all_thirteen_standard_stages_exist_and_are_active(self):
        self.assertEqual(len(OPERATION_SEEDS), 13)
        for seed in OPERATION_SEEDS:
            operation = Operation.objects.get(code=seed["code"])
            self.assertEqual(operation.name, seed["name"])
            self.assertEqual(operation.measure_unit, seed["measure_unit"])
            self.assertEqual(operation.order_index, seed["order_index"])
            self.assertTrue(operation.is_active)

    def test_order_index_is_1_to_13_in_spec_order(self):
        codes_by_index = list(
            Operation.objects.filter(code__in=STANDARD_OPERATION_CODES)
            .order_by("order_index")
            .values_list("code", flat=True)
        )
        self.assertEqual(codes_by_index, STANDARD_OPERATION_CODES)
        indexes = list(
            Operation.objects.filter(code__in=STANDARD_OPERATION_CODES)
            .order_by("order_index")
            .values_list("order_index", flat=True)
        )
        self.assertEqual(indexes, list(range(1, 14)))

    def test_measure_units_match_spec(self):
        expected = {seed["code"]: seed["measure_unit"] for seed in OPERATION_SEEDS}
        actual = dict(
            Operation.objects.filter(code__in=STANDARD_OPERATION_CODES).values_list("code", "measure_unit")
        )
        self.assertEqual(actual, expected)


class OperationApiIsReadOnlyTests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="stage-admin",
            phone="+998901119001",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.super_admin)

    def test_list_endpoint_returns_thirteen_active_stages_in_order(self):
        response = self.client.get("/api/operations/")

        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        codes = [row["code"] for row in rows if row["code"] in STANDARD_OPERATION_CODES]
        self.assertEqual(codes, STANDARD_OPERATION_CODES)

    def test_retrieve_endpoint_works(self):
        operation = Operation.objects.get(code="ARRA")

        response = self.client.get(f"/api/operations/{operation.id}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["code"], "ARRA")

    def test_create_is_not_allowed(self):
        response = self.client.post(
            "/api/operations/", {"name": "Yangi bosqich", "order_index": 20}, format="json",
        )
        self.assertEqual(response.status_code, 405, response.data)

    def test_update_is_not_allowed(self):
        operation = Operation.objects.get(code="ARRA")

        response = self.client.patch(
            f"/api/operations/{operation.id}/", {"name": "Boshqa nom"}, format="json",
        )

        self.assertEqual(response.status_code, 405, response.data)
        operation.refresh_from_db()
        self.assertEqual(operation.name, "Arra")

    def test_full_update_is_not_allowed(self):
        operation = Operation.objects.get(code="ARRA")

        response = self.client.put(
            f"/api/operations/{operation.id}/",
            {"name": "Boshqa nom", "code": "ARRA", "measure_unit": "meter", "order_index": 1, "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 405, response.data)

    def test_delete_is_not_allowed(self):
        operation = Operation.objects.get(code="ARRA")

        response = self.client.delete(f"/api/operations/{operation.id}/")

        self.assertEqual(response.status_code, 405, response.data)
        self.assertTrue(Operation.objects.filter(pk=operation.pk).exists())
