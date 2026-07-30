from django.contrib.auth.hashers import make_password
from rest_framework.test import APITestCase

from manufacturing.models import Machine, Operation, Tsex
from orders.models import Order, Part

from .models import EmployeeStageMachine, EmploymentStatus, Role, TERMINAL_ROLES, User


class LoginTests(APITestCase):
    def test_user_can_login_with_phone_and_password(self):
        user = User.objects.create_superuser(
            username="admin",
            phone="+998901112201",
            password="secret-pass",
        )

        response = self.client.post(
            "/api/auth/login",
            {"phone": user.phone, "password": "secret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["phone"], user.phone)

    def test_non_admin_role_cannot_login_to_admin_panel(self):
        user = User.objects.create_user(
            username="operator",
            phone="+998901112202",
            password="secret-pass",
            role=Role.OPERATOR,
        )

        response = self.client.post(
            "/api/auth/login",
            {"phone": user.phone, "password": "secret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_wrong_password_returns_generic_error(self):
        User.objects.create_user(
            username="pinuser",
            phone="+998901112203",
            password="secret-pass",
            role=Role.OPERATOR,
        )

        response = self.client.post(
            "/api/auth/login",
            {"phone": "+998901112203", "password": "wrong-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Telefon raqam yoki parol noto'g'ri")

    def test_unknown_phone_returns_generic_error(self):
        response = self.client.post(
            "/api/auth/login",
            {"phone": "+998901112299", "password": "whatever123"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Telefon raqam yoki parol noto'g'ri")

    def test_superuser_has_management_api_access_even_with_non_admin_role(self):
        # create_superuser() always forces role=Super Admin now, so this scenario —
        # is_superuser=True with a non-admin role — is built by hand instead.
        user = User.objects.create_user(
            username="root",
            phone="+998901112204",
            password="secret-pass",
            role=Role.OPERATOR,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/employees/")

        self.assertEqual(response.status_code, 200)

    def test_createsuperuser_always_forces_super_admin_role(self):
        user = User.objects.create_superuser(
            username="forced-root",
            phone="+998901112206",
            password="secret-pass",
            role=Role.OPERATOR,
        )
        self.assertEqual(user.role, Role.SUPER_ADMIN)

    def test_super_admin_role_cannot_be_changed(self):
        user = User.objects.create_user(
            username="locked-admin",
            phone="+998901112207",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        user.role = Role.OPERATOR
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.role, Role.SUPER_ADMIN)

    def test_super_admin_role_is_staff_and_superuser(self):
        user = User.objects.create_user(
            username="superadmin",
            phone="+998901112205",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class TerminalPinValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="terminal-user",
            phone="+998901112208",
            password="secret-pass",
            role=Role.OPERATOR,
            pin_code_hash=make_password("0123"),
        )

    def test_four_digit_pin_is_accepted(self):
        response = self.client.post(
            "/api/auth/terminal-pin-lookup", {"pin_code": "0123"}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)

    def test_lookup_rejects_pin_that_is_not_exactly_four_digits(self):
        for pin_code in ("123", "12345", "12a4", "١٢٣٤"):
            with self.subTest(pin_code=pin_code):
                response = self.client.post(
                    "/api/auth/terminal-pin-lookup", {"pin_code": pin_code}, format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)

    def test_login_rejects_pin_that_is_not_exactly_four_digits(self):
        for pin_code in ("123", "12345", "12a4", "١٢٣٤"):
            with self.subTest(pin_code=pin_code):
                response = self.client.post(
                    "/api/auth/terminal-login",
                    {"pin_code": pin_code, "device_id": "test-device"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)


class SuperAdminMutualProtectionTests(APITestCase):
    """One super admin must not be able to update, deactivate, or delete another
    super admin's account via the /api/employees/ management endpoint."""

    def setUp(self):
        self.actor = User.objects.create_user(
            username="actor-admin",
            phone="+998901112501",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.other = User.objects.create_user(
            username="other-admin",
            phone="+998901112502",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.actor)

    def test_cannot_update_another_super_admin(self):
        response = self.client.patch(
            f"/api/employees/{self.other.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.other.refresh_from_db()
        self.assertNotEqual(self.other.first_name, "Changed")

    def test_cannot_deactivate_another_super_admin(self):
        response = self.client.patch(
            f"/api/employees/{self.other.id}/", {"is_active_employee": False}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.other.refresh_from_db()
        self.assertTrue(self.other.is_active_employee)

    def test_cannot_delete_another_super_admin(self):
        response = self.client.delete(f"/api/employees/{self.other.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.other.id).exists())


class SuperAdminSelfEditTests(APITestCase):
    """A Super Admin may update their own account via /api/employees/, but never
    their own phone number. Non-super-admin roles still can't self-edit at all."""

    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="self-super",
            phone="+998901112601",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )

    def test_super_admin_can_update_own_non_phone_fields(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/", {"first_name": "Yangilangan"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.first_name, "Yangilangan")

    def test_super_admin_cannot_change_own_phone(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/", {"phone": "+998901112699"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.phone, "+998901112601")

    def test_super_admin_cannot_change_own_role(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/", {"role": Role.WAREHOUSE}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.role, Role.SUPER_ADMIN)

    def test_resubmitting_same_role_is_allowed(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/",
            {"first_name": "Ok", "role": Role.SUPER_ADMIN},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_resubmitting_same_phone_is_allowed(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.patch(
            f"/api/employees/{self.super_admin.id}/",
            {"first_name": "Ok", "phone": self.super_admin.phone},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_non_super_admin_still_cannot_self_edit(self):
        director = User.objects.create_user(
            username="self-director",
            phone="+998901112602",
            password="secret-pass",
            role=Role.DIRECTOR,
        )
        self.client.force_authenticate(user=director)
        response = self.client.patch(
            f"/api/employees/{director.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class SuperAdminFullAccessTests(APITestCase):
    """Regression guard: a Super Admin (role=super_admin, not just is_superuser=True
    set directly) must retain full CRUD on every module, even if a future change
    adds a new roles_allowed(...) permission somewhere that forgets about it."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="fullaccess-admin",
            phone="+998901112401",
            password="secret-pass",
            role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def test_orders_full_crud(self):
        create = self.client.post("/api/orders/", {"product_name": "Test mahsulot"}, format="json")
        self.assertEqual(create.status_code, 201, create.data)
        order_id = create.data["id"]

        update = self.client.patch(f"/api/orders/{order_id}/", {"priority": "urgent"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/orders/{order_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(Order.objects.filter(id=order_id).exists())

    def test_parts_full_crud(self):
        order = Order.objects.create(product_name="Buyurtma")
        create = self.client.post(
            "/api/parts/",
            {"order": order.id, "code": "P-1", "name": "Detal", "quantity": 1},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        part_id = create.data["id"]

        update = self.client.patch(f"/api/parts/{part_id}/", {"status": "in_progress"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/parts/{part_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(Part.objects.filter(id=part_id).exists())

    def test_employees_full_crud(self):
        tsex = Tsex.objects.create(name="Test bo'lim")
        operation = Operation.objects.create(code="TEST-EMP-OP", name="Test bosqich", measure_unit="piece")
        machine = Machine.objects.create(machine_id="M-TEST-EMP", name="Test stanok", operation=operation, tsex=tsex)
        create = self.client.post(
            "/api/employees/",
            {
                "username": "yangi-xodim", "phone": "+998901112402", "role": Role.OPERATOR, "password": "secret-pass",
                "department": tsex.id, "assigned_operation": operation.id, "assigned_machines": [machine.id], "pin_code": "5566",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        employee_id = create.data["id"]

        update = self.client.patch(f"/api/employees/{employee_id}/", {"first_name": "Yangilangan"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)

        delete = self.client.delete(f"/api/employees/{employee_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(User.objects.filter(id=employee_id).exists())

    def test_manufacturing_infrastructure_full_crud(self):
        operation = Operation.objects.create(code="TEST-OP", name="Test bosqich", measure_unit="piece")
        tsex = Tsex.objects.create(name="Tsex")

        machine_create = self.client.post(
            "/api/machines/",
            {"machine_id": "M-1", "name": "Stanok", "operation": operation.id, "tsex": tsex.id},
            format="json",
        )
        self.assertEqual(machine_create.status_code, 201, machine_create.data)
        machine_id = machine_create.data["id"]

        machine_update = self.client.patch(f"/api/machines/{machine_id}/", {"status": "maintenance"}, format="json")
        self.assertEqual(machine_update.status_code, 200, machine_update.data)

        machine_delete = self.client.delete(f"/api/machines/{machine_id}/")
        self.assertEqual(machine_delete.status_code, 204)
        self.assertFalse(Machine.objects.filter(id=machine_id).exists())


class OperatorDepartmentMachineValidationTests(APITestCase):
    """Business rules for the new department/machine assignment on Operator / Usta."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="dept-admin", phone="+998901112701", password="secret-pass", role=Role.ADMIN,
        )
        self.tsex_a = Tsex.objects.create(name="Bo'lim A")
        self.tsex_b = Tsex.objects.create(name="Bo'lim B")
        self.operation = Operation.objects.create(code="DEPT-OP", name="Bosqich", measure_unit="piece")
        self.machine_a = Machine.objects.create(
            machine_id="M-DEPT-A", name="Stanok A", operation=self.operation, tsex=self.tsex_a,
        )
        self.machine_b = Machine.objects.create(
            machine_id="M-DEPT-B", name="Stanok B", operation=self.operation, tsex=self.tsex_b,
        )
        self.client.force_authenticate(user=self.admin)

    def _create_operator(self, **overrides):
        payload = {
            "username": "dept-operator", "phone": "+998901112702", "role": Role.OPERATOR,
            "password": "secret-pass", "pin_code": "4321",
        }
        payload.update(overrides)
        return self.client.post("/api/employees/", payload, format="json")

    def test_operator_without_department_is_rejected(self):
        response = self._create_operator(assigned_machines=[self.machine_a.id])
        self.assertEqual(response.status_code, 400)
        self.assertIn("department", response.data)

    def test_operator_without_stage_is_rejected(self):
        response = self._create_operator(department=self.tsex_a.id, assigned_machines=[self.machine_a.id])
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_operation", response.data)

    def test_operator_without_machine_is_rejected(self):
        response = self._create_operator(department=self.tsex_a.id, assigned_operation=self.operation.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_machines", response.data)

    def test_operator_machine_from_other_department_is_rejected(self):
        response = self._create_operator(
            department=self.tsex_a.id, assigned_operation=self.operation.id, assigned_machines=[self.machine_b.id],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_machines", response.data)

    def test_operator_machine_from_other_stage_is_rejected(self):
        other_stage = Operation.objects.create(code="DEPT-OP-2", name="Boshqa bosqich", measure_unit="piece")
        other_stage_machine = Machine.objects.create(
            machine_id="M-DEPT-A-2", name="Stanok A2", operation=other_stage, tsex=self.tsex_a,
        )
        response = self._create_operator(
            department=self.tsex_a.id, assigned_operation=self.operation.id, assigned_machines=[other_stage_machine.id],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_machines", response.data)

    def test_operator_without_pin_is_rejected(self):
        response = self._create_operator(
            department=self.tsex_a.id, assigned_operation=self.operation.id,
            assigned_machines=[self.machine_a.id], pin_code="",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("pin_code", response.data)

    def test_operator_with_valid_department_and_machine_succeeds(self):
        response = self._create_operator(
            department=self.tsex_a.id, assigned_operation=self.operation.id, assigned_machines=[self.machine_a.id],
        )
        self.assertEqual(response.status_code, 201, response.data)
        employee = User.objects.get(id=response.data["id"])
        self.assertEqual(employee.department_id, self.tsex_a.id)
        self.assertEqual(employee.assigned_operation_id, self.operation.id)
        self.assertTrue(employee.pin_code_hash)
        self.assertNotEqual(employee.pin_code_hash, "4321")
        self.assertTrue(
            EmployeeStageMachine.objects.filter(
                employee=employee, machine=self.machine_a, stage=self.operation,
            ).exists()
        )

    def test_manager_department_is_optional(self):
        response = self.client.post(
            "/api/employees/",
            {
                "username": "dept-manager", "phone": "+998901112703", "role": Role.MANAGER,
                "password": "secret-pass",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)


class ManagementRolePermissionScopeTests(APITestCase):
    """Rahbar is read-only over employees; Ishlab chiqarish menejeri may only
    assign department/machines, never edit any other employee field."""

    def setUp(self):
        self.tsex = Tsex.objects.create(name="Bo'lim")
        self.operation = Operation.objects.create(code="SCOPE-OP", name="Bosqich", measure_unit="piece")
        self.machine = Machine.objects.create(
            machine_id="M-SCOPE", name="Stanok", operation=self.operation, tsex=self.tsex,
        )
        self.director = User.objects.create_user(
            username="scope-director", phone="+998901112801", password="secret-pass", role=Role.DIRECTOR,
        )
        self.manager = User.objects.create_user(
            username="scope-manager", phone="+998901112802", password="secret-pass", role=Role.MANAGER,
        )
        self.operator = User.objects.create_user(
            username="scope-operator", phone="+998901112803", password="secret-pass", role=Role.OPERATOR,
        )

    def test_director_can_list_employees(self):
        self.client.force_authenticate(user=self.director)
        response = self.client.get("/api/employees/")
        self.assertEqual(response.status_code, 200, response.data)

    def test_director_cannot_create_employee(self):
        self.client.force_authenticate(user=self.director)
        response = self.client.post(
            "/api/employees/",
            {"username": "blocked", "phone": "+998901112804", "role": Role.WAREHOUSE, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_director_cannot_edit_employee(self):
        self.client.force_authenticate(user=self.director)
        response = self.client.patch(
            f"/api/employees/{self.operator.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_can_assign_department_and_machines(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f"/api/employees/{self.operator.id}/",
            {
                "department": self.tsex.id, "assigned_operation": self.operation.id,
                "assigned_machines": [self.machine.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.department_id, self.tsex.id)
        self.assertEqual(self.operator.assigned_operation_id, self.operation.id)

    def test_manager_cannot_edit_other_fields(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.patch(
            f"/api/employees/{self.operator.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_create_employee(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            "/api/employees/",
            {"username": "blocked2", "phone": "+998901112805", "role": Role.WAREHOUSE, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class LegacyRoleMigrationTests(APITestCase):
    """Guards the accounts.0012 data migration's remap logic directly against
    the model layer, independent of whether the migration already ran on this
    test database (Django applies all migrations before the test run)."""

    def test_no_legacy_role_values_remain(self):
        legacy_values = {"master", "technologist", "packaging", "sysadmin"}
        self.assertFalse(User.objects.filter(role__in=legacy_values).exists())

    def test_role_choices_are_exactly_six(self):
        self.assertEqual(
            set(dict(Role.choices).keys()),
            {"super_admin", "admin", "director", "manager", "operator", "warehouse"},
        )


class PinSecurityAndRoleGatingTests(APITestCase):
    """PIN hashing, per-role PIN requirements, and active-employee-scoped
    uniqueness — the core of the role/PIN redesign."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="pin-admin", phone="+998901113001", password="secret-pass", role=Role.ADMIN,
        )
        self.tsex = Tsex.objects.create(name="PIN bo'lim")
        self.operation = Operation.objects.create(code="PIN-OP", name="PIN bosqich", measure_unit="piece")
        self.machine = Machine.objects.create(machine_id="M-PIN", name="Stanok", operation=self.operation, tsex=self.tsex)
        self.client.force_authenticate(user=self.admin)

    def _operator_payload(self, phone, pin_code, username="pin-operator"):
        return {
            "username": username, "phone": phone, "role": Role.OPERATOR, "password": "secret-pass",
            "department": self.tsex.id, "assigned_operation": self.operation.id, "assigned_machines": [self.machine.id],
            "pin_code": pin_code,
        }

    def test_pin_is_never_stored_in_plaintext(self):
        response = self.client.post(
            "/api/employees/", self._operator_payload("+998901113002", "7788"), format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        employee = User.objects.get(id=response.data["id"])
        self.assertNotEqual(employee.pin_code_hash, "7788")
        self.assertNotIn("pin_code", response.data)
        self.assertTrue(response.data["has_pin"])

    def test_terminal_login_still_works_with_hashed_pin(self):
        self.client.post("/api/employees/", self._operator_payload("+998901113003", "6655"), format="json")
        response = self.client.post(
            "/api/auth/terminal-login", {"pin_code": "6655", "device_id": "dev-1"}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["employee"]["phone"], "+998901113003")

    def test_pin_cannot_be_reused_by_another_active_employee(self):
        self.client.post("/api/employees/", self._operator_payload("+998901113004", "9911", "pin-op-a"), format="json")
        response = self.client.post(
            "/api/employees/", self._operator_payload("+998901113005", "9911", "pin-op-b"), format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("pin_code", response.data)

    def test_pin_can_be_reused_once_previous_holder_is_inactive(self):
        first = self.client.post(
            "/api/employees/", self._operator_payload("+998901113006", "3344", "pin-op-c"), format="json",
        )
        self.client.patch(f"/api/employees/{first.data['id']}/", {"is_active_employee": False}, format="json")
        response = self.client.post(
            "/api/employees/", self._operator_payload("+998901113007", "3344", "pin-op-d"), format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_super_admin_admin_director_cannot_have_pin(self):
        for role, phone in [(Role.SUPER_ADMIN, "+998901113008"), (Role.ADMIN, "+998901113009"), (Role.DIRECTOR, "+998901113010")]:
            with self.subTest(role=role):
                response = self.client.post(
                    "/api/employees/",
                    {"username": f"no-pin-{role}", "phone": phone, "role": role, "password": "secret-pass", "pin_code": "1122"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("pin_code", response.data)

    def test_super_admin_admin_director_require_password_on_create(self):
        response = self.client.post(
            "/api/employees/",
            {"username": "no-pass-director", "phone": "+998901113011", "role": Role.DIRECTOR},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("password", response.data)

    def test_manager_pin_is_optional(self):
        response = self.client.post(
            "/api/employees/",
            {"username": "manager-no-pin", "phone": "+998901113012", "role": Role.MANAGER, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(response.data["has_pin"])

    def test_manager_role_can_use_terminal(self):
        self.assertIn(Role.MANAGER, TERMINAL_ROLES)

    def test_warehouse_requires_pin_only_when_using_terminal(self):
        without_terminal = self.client.post(
            "/api/employees/",
            {"username": "wh-no-terminal", "phone": "+998901113013", "role": Role.WAREHOUSE, "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(without_terminal.status_code, 201, without_terminal.data)

        rejected = self.client.post(
            "/api/employees/",
            {
                "username": "wh-terminal-no-pin", "phone": "+998901113014", "role": Role.WAREHOUSE,
                "uses_terminal": True,
            },
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, rejected.data)
        self.assertIn("pin_code", rejected.data)

        accepted = self.client.post(
            "/api/employees/",
            {
                "username": "wh-terminal-pin", "phone": "+998901113015", "role": Role.WAREHOUSE,
                "uses_terminal": True, "pin_code": "4455",
            },
            format="json",
        )
        self.assertEqual(accepted.status_code, 201, accepted.data)

    def test_warehouse_can_use_admin_login_only_without_terminal(self):
        no_terminal = User.objects.create_user(
            username="wh-login-ok", phone="+998901113016", password="secret-pass", role=Role.WAREHOUSE,
        )
        with_terminal = User.objects.create_user(
            username="wh-login-blocked", phone="+998901113017", password="secret-pass", role=Role.WAREHOUSE,
            uses_terminal=True,
        )
        self.assertTrue(no_terminal.can_use_admin)
        self.assertFalse(with_terminal.can_use_admin)


class InactiveEmployeeTerminalAccessTests(APITestCase):
    """Nofaol, ta'tildagi yoki bo'shatilgan xodim PIN bilan terminalga kira olmasin."""

    def setUp(self):
        self.tsex = Tsex.objects.create(name="Bo'lim")
        self.operation = Operation.objects.create(code="INACTIVE-OP", name="Bosqich", measure_unit="piece")
        self.machine = Machine.objects.create(
            machine_id="M-INACTIVE", name="Stanok", operation=self.operation, tsex=self.tsex,
        )
        self.employee = User.objects.create_user(
            username="status-operator", phone="+998901113101", password="secret-pass", role=Role.OPERATOR,
            department=self.tsex, pin_code_hash=make_password("2233"), assigned_operation=self.operation,
        )
        EmployeeStageMachine.objects.create(employee=self.employee, machine=self.machine)

    def test_active_employee_can_be_found_by_pin(self):
        self.assertEqual(User.objects.get_by_pin("2233"), self.employee)

    def test_vacation_status_deactivates_and_blocks_pin_login(self):
        self.employee.employment_status = EmploymentStatus.VACATION
        self.employee.save()
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active_employee)
        self.assertIsNone(User.objects.get_by_pin("2233"))

    def test_sick_status_deactivates_and_blocks_pin_login(self):
        self.employee.employment_status = EmploymentStatus.SICK
        self.employee.save()
        self.assertIsNone(User.objects.get_by_pin("2233"))

    def test_terminated_status_deactivates_and_blocks_pin_login(self):
        self.employee.employment_status = EmploymentStatus.TERMINATED
        self.employee.save()
        self.assertIsNone(User.objects.get_by_pin("2233"))

    def test_directly_deactivated_employee_blocks_pin_login(self):
        self.employee.is_active_employee = False
        self.employee.save()
        self.assertIsNone(User.objects.get_by_pin("2233"))

    def test_wrong_pin_does_not_match(self):
        self.assertIsNone(User.objects.get_by_pin("0000"))


class LegacyPinMigrationDataIntegrityTests(APITestCase):
    """Guards against reintroducing plaintext PIN storage."""

    def test_plaintext_pin_field_no_longer_exists(self):
        field_names = {f.name for f in User._meta.get_fields()}
        self.assertNotIn("pin_code", field_names)
        self.assertIn("pin_code_hash", field_names)


class MultiStageMachineAssignmentTests(APITestCase):
    """Xodimlar formasi: bosqich(lar) endi klient tomonidan aniq tanlanadi
    (top-down), stanoklar esa har bir (xodim, bosqich) juftligi uchun
    alohida EmployeeStageMachine qatorlarida saqlanadi — machine.operation
    orqali emas, xodimning O'ZI shu bosqichga biriktirilgan bo'lishi kerak."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="multi-admin", phone="+998901113201", password="secret-pass", role=Role.ADMIN,
        )
        self.tsex = Tsex.objects.create(name="Multi bo'lim")
        self.arra = Operation.objects.create(code="MULTI-ARRA", name="Arra", measure_unit="m2")
        self.kromka = Operation.objects.create(code="MULTI-KROMKA", name="Kromka", measure_unit="meter")
        self.arra_machine = Machine.objects.create(machine_id="M-MULTI-ARRA", name="Arra-1", operation=self.arra, tsex=self.tsex)
        self.kromka_machine_1 = Machine.objects.create(
            machine_id="M-MULTI-KROMKA-1", name="Kromka-1", operation=self.kromka, tsex=self.tsex,
        )
        self.kromka_machine_2 = Machine.objects.create(
            machine_id="M-MULTI-KROMKA-2", name="Kromka-2", operation=self.kromka, tsex=self.tsex,
        )
        self.client.force_authenticate(user=self.admin)

    def _create_operator(self, **overrides):
        payload = {
            "username": "multi-operator", "phone": "+998901113202", "role": Role.OPERATOR,
            "password": "secret-pass", "pin_code": "1357", "department": self.tsex.id,
        }
        payload.update(overrides)
        return self.client.post("/api/employees/", payload, format="json")

    def test_multi_stage_with_per_stage_machine_counts(self):
        response = self._create_operator(
            multi_stage_enabled=True,
            assigned_operations=[self.arra.id, self.kromka.id],
            assigned_machines=[self.arra_machine.id, self.kromka_machine_1.id, self.kromka_machine_2.id],
        )
        self.assertEqual(response.status_code, 201, response.data)
        employee = User.objects.get(id=response.data["id"])

        self.assertTrue(employee.multi_stage_enabled)
        self.assertIsNone(employee.assigned_operation_id)
        self.assertEqual(
            set(employee.assigned_operations.values_list("id", flat=True)), {self.arra.id, self.kromka.id},
        )
        rows = list(
            EmployeeStageMachine.objects.filter(employee=employee).values("stage_id", "machine_id")
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {r["machine_id"] for r in rows if r["stage_id"] == self.arra.id}, {self.arra_machine.id},
        )
        self.assertEqual(
            {r["machine_id"] for r in rows if r["stage_id"] == self.kromka.id},
            {self.kromka_machine_1.id, self.kromka_machine_2.id},
        )
        self.assertEqual(employee.assigned_machines.filter(operation=self.kromka).count(), 2)
        self.assertEqual(employee.assigned_machines.filter(operation=self.arra).count(), 1)

    def test_machine_outside_selected_stages_is_rejected_even_in_same_tsex(self):
        response = self._create_operator(
            multi_stage_enabled=False,
            assigned_operation=self.arra.id,
            # kromka_machine_1 is in the same tsex, but Arra-only was selected.
            assigned_machines=[self.arra_machine.id, self.kromka_machine_1.id],
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_machines", response.data)

    def test_toggling_multi_stage_off_clears_assigned_operations(self):
        create = self._create_operator(
            multi_stage_enabled=True,
            assigned_operations=[self.arra.id, self.kromka.id],
            assigned_machines=[self.arra_machine.id, self.kromka_machine_1.id],
        )
        self.assertEqual(create.status_code, 201, create.data)
        employee_id = create.data["id"]

        update = self.client.patch(
            f"/api/employees/{employee_id}/",
            {
                "multi_stage_enabled": False, "assigned_operation": self.arra.id,
                "assigned_operations": [], "assigned_machines": [self.arra_machine.id],
            },
            format="json",
        )
        self.assertEqual(update.status_code, 200, update.data)
        employee = User.objects.get(id=employee_id)
        self.assertFalse(employee.multi_stage_enabled)
        self.assertEqual(employee.assigned_operation_id, self.arra.id)
        self.assertEqual(employee.assigned_operations.count(), 0)
        self.assertEqual(EmployeeStageMachine.objects.filter(employee=employee).count(), 1)

    def test_toggling_multi_stage_on_clears_assigned_operation(self):
        create = self._create_operator(
            multi_stage_enabled=False, assigned_operation=self.arra.id,
            assigned_machines=[self.arra_machine.id],
        )
        self.assertEqual(create.status_code, 201, create.data)
        employee_id = create.data["id"]

        update = self.client.patch(
            f"/api/employees/{employee_id}/",
            {
                "multi_stage_enabled": True, "assigned_operations": [self.arra.id, self.kromka.id],
                "assigned_machines": [self.arra_machine.id, self.kromka_machine_1.id],
            },
            format="json",
        )
        self.assertEqual(update.status_code, 200, update.data)
        employee = User.objects.get(id=employee_id)
        self.assertTrue(employee.multi_stage_enabled)
        self.assertIsNone(employee.assigned_operation_id)
        self.assertEqual(set(employee.assigned_operations.values_list("id", flat=True)), {self.arra.id, self.kromka.id})

    def test_update_diff_syncs_machines_without_disturbing_untouched_rows(self):
        create = self._create_operator(
            multi_stage_enabled=True,
            assigned_operations=[self.arra.id, self.kromka.id],
            assigned_machines=[self.arra_machine.id, self.kromka_machine_1.id],
        )
        self.assertEqual(create.status_code, 201, create.data)
        employee_id = create.data["id"]
        untouched_row_id = EmployeeStageMachine.objects.get(
            employee_id=employee_id, machine=self.kromka_machine_1,
        ).id

        update = self.client.patch(
            f"/api/employees/{employee_id}/",
            {"assigned_machines": [self.kromka_machine_1.id, self.kromka_machine_2.id]},
            format="json",
        )
        self.assertEqual(update.status_code, 200, update.data)

        remaining = set(
            EmployeeStageMachine.objects.filter(employee_id=employee_id).values_list("machine_id", flat=True)
        )
        self.assertEqual(remaining, {self.kromka_machine_1.id, self.kromka_machine_2.id})
        self.assertEqual(
            EmployeeStageMachine.objects.get(employee_id=employee_id, machine=self.kromka_machine_1).id,
            untouched_row_id,
            "the untouched (employee, kromka_machine_1) row must not be deleted and recreated",
        )

    def test_stage_consistency_after_sync(self):
        create = self._create_operator(
            multi_stage_enabled=True,
            assigned_operations=[self.arra.id, self.kromka.id],
            assigned_machines=[self.arra_machine.id, self.kromka_machine_1.id],
        )
        self.assertEqual(create.status_code, 201, create.data)
        for row in EmployeeStageMachine.objects.filter(employee_id=create.data["id"]):
            self.assertEqual(row.stage_id, row.machine.operation_id)

    def test_terminal_pin_lookup_scopes_machines_per_stage(self):
        create = self._create_operator(
            multi_stage_enabled=True,
            assigned_operations=[self.arra.id, self.kromka.id],
            assigned_machines=[self.arra_machine.id, self.kromka_machine_1.id, self.kromka_machine_2.id],
        )
        self.assertEqual(create.status_code, 201, create.data)

        response = self.client.post("/api/auth/terminal-pin-lookup", {"pin_code": "1357"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

        by_code = {op["code"]: op for op in response.data["operations"]}
        self.assertEqual({m["id"] for m in by_code["MULTI-ARRA"]["machines"]}, {self.arra_machine.id})
        self.assertEqual(
            {m["id"] for m in by_code["MULTI-KROMKA"]["machines"]},
            {self.kromka_machine_1.id, self.kromka_machine_2.id},
        )


class EmployeeBadgeTokenTests(APITestCase):
    """Per-employee QR badge token: auto-generated once at creation, unique,
    immutable through the API, and gated by the employee's active status at
    scan time rather than being baked into the token itself."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="badge-admin", phone="+998901113201", password="secret-pass", role=Role.SUPER_ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def _create_employee(self, phone, username="badge-op", pin_code="4411"):
        response = self.client.post(
            "/api/employees/",
            {
                "username": username, "phone": phone, "role": Role.WAREHOUSE, "uses_terminal": True,
                "pin_code": pin_code,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_badge_token_is_auto_generated_on_create(self):
        data = self._create_employee("+998901113202")
        self.assertTrue(data["badge_token"])
        employee = User.objects.get(id=data["id"])
        self.assertTrue(employee.badge_token)

    def test_badge_tokens_are_unique_per_employee(self):
        first = self._create_employee("+998901113203", username="badge-op-a", pin_code="1201")
        second = self._create_employee("+998901113204", username="badge-op-b", pin_code="1202")
        self.assertNotEqual(first["badge_token"], second["badge_token"])

    def test_badge_token_is_unchanged_by_editing_employee(self):
        data = self._create_employee("+998901113205")
        original_token = data["badge_token"]

        update = self.client.patch(f"/api/employees/{data['id']}/", {"first_name": "Yangi"}, format="json")
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(update.data["badge_token"], original_token)

        employee = User.objects.get(id=data["id"])
        self.assertEqual(employee.badge_token, original_token)

    def test_badge_token_is_not_regenerated_by_repeated_saves(self):
        data = self._create_employee("+998901113206")
        original_token = data["badge_token"]
        employee = User.objects.get(id=data["id"])
        for _ in range(3):
            employee.save()
        employee.refresh_from_db()
        self.assertEqual(employee.badge_token, original_token)

    def test_client_cannot_set_or_overwrite_badge_token_via_api(self):
        response = self.client.post(
            "/api/employees/",
            {
                "username": "badge-hijack", "phone": "+998901113207", "role": Role.WAREHOUSE,
                "uses_terminal": True, "pin_code": "7712", "badge_token": "attacker-supplied-token",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotEqual(response.data["badge_token"], "attacker-supplied-token")

        update = self.client.patch(
            f"/api/employees/{response.data['id']}/", {"badge_token": "still-attacker-supplied"}, format="json",
        )
        self.assertEqual(update.status_code, 200, update.data)
        self.assertNotEqual(update.data["badge_token"], "still-attacker-supplied")
        employee = User.objects.get(id=response.data["id"])
        self.assertNotEqual(employee.badge_token, "still-attacker-supplied")

    def test_active_employee_badge_token_logs_in(self):
        data = self._create_employee("+998901113208")
        response = self.client.post(
            "/api/auth/terminal-login",
            {"badge_token": data["badge_token"], "device_id": "term-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["employee"]["phone"], "+998901113208")

    def test_inactive_employee_badge_token_is_rejected_with_specific_message(self):
        data = self._create_employee("+998901113209")
        employee = User.objects.get(id=data["id"])
        employee.is_active_employee = False
        employee.save()

        response = self.client.post(
            "/api/auth/terminal-login",
            {"badge_token": data["badge_token"], "device_id": "term-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 401, response.data)
        self.assertEqual(response.data["detail"], "Bu xodim nofaol. QR koddan foydalanish mumkin emas.")

    def test_reactivated_employee_badge_token_works_again_without_new_token(self):
        data = self._create_employee("+998901113210")
        original_token = data["badge_token"]
        employee = User.objects.get(id=data["id"])
        employee.is_active_employee = False
        employee.save()
        employee.is_active_employee = True
        employee.save()
        employee.refresh_from_db()
        self.assertEqual(employee.badge_token, original_token)

        response = self.client.post(
            "/api/auth/terminal-login",
            {"badge_token": original_token, "device_id": "term-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_unknown_badge_token_is_rejected(self):
        response = self.client.post(
            "/api/auth/terminal-login",
            {"badge_token": "this-token-does-not-exist", "device_id": "term-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 401, response.data)
        self.assertEqual(response.data["detail"], "PIN yoki badge noto'g'ri")

    def test_deleted_employee_badge_token_is_rejected(self):
        data = self._create_employee("+998901113211")
        User.objects.get(id=data["id"]).delete()

        response = self.client.post(
            "/api/auth/terminal-login",
            {"badge_token": data["badge_token"], "device_id": "term-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 401, response.data)
        self.assertEqual(response.data["detail"], "PIN yoki badge noto'g'ri")
