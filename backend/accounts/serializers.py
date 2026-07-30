from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from manufacturing.models import Machine
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import NO_PIN_ROLES, SUPER_ADMIN_LEVEL_ROLES, EmployeeStageMachine, Role, User, pin_code_validator


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    employment_status_display = serializers.CharField(source="get_employment_status_display", read_only=True)
    specialization_display = serializers.CharField(source="get_specialization_display", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pin_code = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True, validators=[pin_code_validator],
    )
    # DRF's ModelSerializer auto-detects assigned_machines as M2M-through-a-
    # custom-model and would otherwise force it read_only=True (its default
    # guard against callers reaching for the now-broken .set()/.add()) — it
    # must be declared explicitly to stay writable. Writes never touch the
    # M2M manager directly; see UserSerializer._sync_stage_machines.
    assigned_machines = serializers.PrimaryKeyRelatedField(many=True, queryset=Machine.objects.all(), required=False)
    has_pin = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    managed_departments_detail = serializers.SerializerMethodField()
    assigned_operation_name = serializers.SerializerMethodField()
    assigned_operations_detail = serializers.SerializerMethodField()
    assigned_machines_detail = serializers.SerializerMethodField()
    needs_assignment_warning = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "phone", "role", "role_display",
            "pin_code", "has_pin", "is_active_employee", "is_active", "is_staff", "is_superuser",
            "employment_status", "employment_status_display",
            "date_joined", "password", "department", "department_name",
            "managed_departments", "managed_departments_detail",
            "multi_stage_enabled", "assigned_operation",
            "assigned_operation_name", "assigned_operations", "assigned_operations_detail",
            "assigned_machines", "assigned_machines_detail", "needs_assignment_warning",
            "specialization", "specialization_display", "uses_terminal", "badge_token",
        ]
        # badge_token is also editable=False on the model (belt-and-braces —
        # it must never be settable through this API, only auto-generated once
        # at creation).
        read_only_fields = ["date_joined", "is_staff", "is_superuser", "badge_token"]
        extra_kwargs = {
            "username": {"required": False, "allow_blank": True},
            "department": {"required": False, "allow_null": True},
        }

    def get_has_pin(self, obj):
        return bool(obj.pin_code_hash)

    def get_department_name(self, obj):
        return obj.department.name if obj.department_id else None

    def get_managed_departments_detail(self, obj):
        return [{"id": t.id, "name": t.name} for t in obj.managed_departments.all()]

    def get_assigned_operation_name(self, obj):
        return obj.assigned_operation.name if obj.assigned_operation_id else None

    def get_assigned_operations_detail(self, obj):
        return [{"id": op.id, "name": op.name} for op in obj.assigned_operations.all()]

    def get_assigned_machines_detail(self, obj):
        return [
            {"id": m.id, "name": m.name, "machine_id": m.machine_id, "operation_id": m.operation_id}
            for m in obj.assigned_machines.all()
        ]

    def get_needs_assignment_warning(self, obj):
        if obj.role != Role.OPERATOR:
            return False
        return not obj.department_id or not obj.assigned_machines.exists()

    def validate_pin_code(self, value):
        if not value:
            return value
        existing = User.objects.get_by_pin(value)
        exclude_id = self.instance.id if self.instance is not None else None
        if existing is not None and existing.id != exclude_id:
            raise serializers.ValidationError("Ushbu PIN kod boshqa faol xodimda mavjud.")
        return value

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", None))

        if role in NO_PIN_ROLES:
            if attrs.get("pin_code"):
                raise serializers.ValidationError({"pin_code": "Bu rol uchun PIN kod kerak emas."})
            if self.instance is None and not attrs.get("password"):
                raise serializers.ValidationError({"password": "Ushbu rol uchun parol majburiy."})

        if role == Role.WAREHOUSE:
            uses_terminal = attrs.get("uses_terminal", getattr(self.instance, "uses_terminal", False))
            touching_pin = "pin_code" in attrs
            becoming_warehouse = self.instance is None or (
                "role" in attrs and getattr(self.instance, "role", None) != Role.WAREHOUSE
            )
            has_existing_pin = self.instance is not None and bool(self.instance.pin_code_hash)
            has_pin = bool(attrs.get("pin_code")) or (has_existing_pin and not touching_pin)
            if uses_terminal and (touching_pin or becoming_warehouse) and not has_pin:
                raise serializers.ValidationError(
                    {"pin_code": "Terminaldan foydalanadigan omborchi uchun PIN kod majburiy."}
                )
            if not uses_terminal and attrs.get("pin_code"):
                raise serializers.ValidationError(
                    {"pin_code": "Terminaldan foydalanmaydigan omborchi uchun PIN kod kerak emas."}
                )

        if role != Role.OPERATOR:
            return attrs

        # Only enforce the department/stage/machine/PIN requirement when a new
        # Operator is being created, an existing employee is being promoted to
        # Operator, or the workplace fields themselves are being touched. This
        # keeps legacy "unassigned" operators (backfilled before this feature,
        # or migrated from the old plaintext-PIN system) editable on unrelated
        # fields without forcing them to be fixed up first.
        touching_workplace = bool(
            {"department", "assigned_machines", "multi_stage_enabled", "assigned_operation", "assigned_operations"}
            & set(attrs)
        )
        touching_pin = "pin_code" in attrs
        becoming_operator = self.instance is None or (
            "role" in attrs and getattr(self.instance, "role", None) != Role.OPERATOR
        )

        if touching_workplace or becoming_operator:
            department = attrs.get("department", getattr(self.instance, "department", None))
            if department is None:
                raise serializers.ValidationError(
                    {"department": "Operator/Usta uchun ishlab chiqarish bo'limi majburiy."}
                )

            # Stage(s) are now chosen explicitly by the client (top-down),
            # not derived from which machines get picked (bottom-up) — see
            # _sync_stage_machines. This raises if none is selected.
            stage_ids = self._required_stage_ids(attrs)

            if "assigned_machines" in attrs:
                assigned_machines = attrs["assigned_machines"]
            elif self.instance is not None:
                assigned_machines = list(self.instance.assigned_machines.all())
            else:
                assigned_machines = []

            if not assigned_machines:
                raise serializers.ValidationError(
                    {"assigned_machines": "Kamida bitta dastgoh tanlanishi kerak."}
                )

            for machine in assigned_machines:
                if machine.tsex_id != department.id:
                    raise serializers.ValidationError(
                        {"assigned_machines": "Tanlangan dastgoh(lar) belgilangan bo'limga tegishli emas."}
                    )
                if machine.operation_id not in stage_ids:
                    raise serializers.ValidationError(
                        {"assigned_machines": "Tanlangan dastgoh(lar) tanlangan bosqich(lar)ga tegishli emas."}
                    )

        if touching_pin or becoming_operator:
            has_existing_pin = self.instance is not None and bool(self.instance.pin_code_hash)
            will_have_pin = bool(attrs.get("pin_code")) or (has_existing_pin and not touching_pin)
            if not will_have_pin:
                raise serializers.ValidationError({"pin_code": "Operator/Usta uchun PIN kod majburiy."})

        return attrs

    def _required_stage_ids(self, attrs):
        """Resolves which stage(s) the client selected — top-down, from the
        client's own `multi_stage_enabled`/`assigned_operation(s)` choice,
        never derived from which machines happen to be picked. Raises if
        none is selected."""
        multi_stage_enabled = attrs.get("multi_stage_enabled", getattr(self.instance, "multi_stage_enabled", False))
        if multi_stage_enabled:
            if "assigned_operations" in attrs:
                stages = attrs["assigned_operations"]
            elif self.instance is not None:
                stages = list(self.instance.assigned_operations.all())
            else:
                stages = []
            if not stages:
                raise serializers.ValidationError({"assigned_operations": "Kamida bitta bosqich tanlanishi kerak."})
            return {stage.id for stage in stages}

        if "assigned_operation" in attrs:
            stage = attrs["assigned_operation"]
        elif self.instance is not None:
            stage = self.instance.assigned_operation
        else:
            stage = None
        if stage is None:
            raise serializers.ValidationError({"assigned_operation": "Ishlab chiqarish bosqichi tanlanishi kerak."})
        return {stage.id}

    def _enforce_stage_exclusivity(self, user):
        """Defensive server-side guarantee that assigned_operation/assigned_operations
        never both hold data at once, regardless of what the client sent —
        mirrors the invariant the old bottom-up sync used to guarantee."""
        if user.multi_stage_enabled:
            if user.assigned_operation_id is not None:
                user.assigned_operation = None
                user.save(update_fields=["assigned_operation"])
        else:
            user.assigned_operations.clear()

    def _sync_stage_machines(self, user, assigned_machines):
        """Diffs `user`'s EmployeeStageMachine rows against the desired flat
        machine list — each row's `stage` is always the machine's own
        operation (see EmployeeStageMachine.save()), so this is what makes
        machine assignment per-stage without the client having to submit
        machines grouped by stage."""
        desired = {machine.id: machine for machine in assigned_machines}
        existing_ids = set(
            EmployeeStageMachine.objects.filter(employee=user).values_list("machine_id", flat=True)
        )
        to_remove = existing_ids - desired.keys()
        to_add = desired.keys() - existing_ids
        if to_remove:
            EmployeeStageMachine.objects.filter(employee=user, machine_id__in=to_remove).delete()
        if to_add:
            EmployeeStageMachine.objects.bulk_create([
                EmployeeStageMachine(employee=user, machine=desired[machine_id], stage_id=desired[machine_id].operation_id)
                for machine_id in to_add
            ])

    def create(self, validated_data):
        password = validated_data.pop("password", None) or get_random_string(12)
        pin_code = validated_data.pop("pin_code", None)
        assigned_operations = validated_data.pop("assigned_operations", None)
        assigned_machines = validated_data.pop("assigned_machines", None)
        managed_departments = validated_data.pop("managed_departments", None)
        user = User(**validated_data)
        if user.role in SUPER_ADMIN_LEVEL_ROLES:
            user.is_staff = True
            user.is_superuser = True
        user.password = make_password(password)
        if pin_code:
            user.pin_code_hash = make_password(pin_code)
        user.save()
        if assigned_operations is not None:
            user.assigned_operations.set(assigned_operations)
        self._enforce_stage_exclusivity(user)
        if managed_departments is not None:
            user.managed_departments.set(managed_departments)
        if assigned_machines is not None:
            self._sync_stage_machines(user, assigned_machines)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        pin_code = validated_data.pop("pin_code", None)
        # Popped (not left in validated_data) because assigned_machines is now
        # M2M-through-EmployeeStageMachine — DRF's default ModelSerializer.update()
        # would otherwise call .set() on it, which raises against a through
        # model with a required extra field (`stage`). _sync_stage_machines
        # below is the only sanctioned write path for this relation.
        assigned_machines = validated_data.pop("assigned_machines", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        if pin_code:
            user.pin_code_hash = make_password(pin_code)
            user.save(update_fields=["pin_code_hash"])
        self._enforce_stage_exclusivity(user)
        if assigned_machines is not None:
            self._sync_stage_machines(user, assigned_machines)
        return user


class AdminLoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "Telefon raqam yoki parol noto'g'ri",
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.can_use_admin:
            raise serializers.ValidationError("Bu foydalanuvchi admin panelga kira olmaydi.")
        data["user"] = UserSerializer(self.user).data
        return data


class TerminalPinLookupSerializer(serializers.Serializer):
    pin_code = serializers.CharField(max_length=4, validators=[pin_code_validator])


class TerminalLoginSerializer(serializers.Serializer):
    pin_code = serializers.CharField(max_length=4, required=False, validators=[pin_code_validator])
    badge_token = serializers.CharField(max_length=64, required=False)
    device_id = serializers.CharField(max_length=128)
    operation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("pin_code") and not attrs.get("badge_token"):
            raise serializers.ValidationError("PIN yoki badge token kerak")
        return attrs
