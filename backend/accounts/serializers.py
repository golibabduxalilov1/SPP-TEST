from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import SUPER_ADMIN_LEVEL_ROLES, Role, User, pin_code_validator


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    department_name = serializers.SerializerMethodField()
    assigned_operation_name = serializers.SerializerMethodField()
    assigned_operations_detail = serializers.SerializerMethodField()
    assigned_machines_detail = serializers.SerializerMethodField()
    needs_assignment_warning = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "phone", "role", "role_display",
            "pin_code", "is_active_employee", "is_active", "is_staff", "is_superuser",
            "date_joined", "password", "department", "department_name",
            "multi_stage_enabled", "assigned_operation",
            "assigned_operation_name", "assigned_operations", "assigned_operations_detail",
            "assigned_machines", "assigned_machines_detail", "needs_assignment_warning",
        ]
        read_only_fields = ["date_joined", "is_staff", "is_superuser"]
        extra_kwargs = {
            "username": {"required": False, "allow_blank": True},
            "pin_code": {"allow_null": True},
            "department": {"required": False, "allow_null": True},
        }

    def get_department_name(self, obj):
        return obj.department.name if obj.department_id else None

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

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", None))
        if role != Role.OPERATOR:
            return attrs

        # Only enforce the department/machine requirement when a new Operator
        # is being created, an existing employee is being promoted to
        # Operator, or the workplace fields themselves are being touched.
        # This keeps legacy "unassigned" operators (backfilled by the
        # accounts.0012 migration) editable on unrelated fields without
        # forcing them to be fixed up first.
        touching_workplace = "department" in attrs or "assigned_machines" in attrs
        becoming_operator = self.instance is None or (
            "role" in attrs and getattr(self.instance, "role", None) != Role.OPERATOR
        )
        if not touching_workplace and not becoming_operator:
            return attrs

        department = attrs.get("department", getattr(self.instance, "department", None))
        if department is None:
            raise serializers.ValidationError(
                {"department": "Operator/Usta uchun ishlab chiqarish bo'limi majburiy."}
            )

        if "assigned_machines" in attrs:
            assigned_machines = attrs["assigned_machines"]
        elif self.instance is not None:
            assigned_machines = list(self.instance.assigned_machines.all())
        else:
            assigned_machines = []

        if not assigned_machines:
            raise serializers.ValidationError(
                {"assigned_machines": "Kamida bitta stanok tanlanishi kerak."}
            )

        for machine in assigned_machines:
            if machine.tsex_id != department.id:
                raise serializers.ValidationError(
                    {"assigned_machines": "Tanlangan stanok(lar) belgilangan bo'limga tegishli emas."}
                )

        return attrs

    def _sync_operations_from_machines(self, user, assigned_machines):
        if user.role != Role.OPERATOR or assigned_machines is None:
            return
        operation_ids = sorted({m.operation_id for m in assigned_machines if m.operation_id})
        if len(operation_ids) > 1:
            user.multi_stage_enabled = True
            user.assigned_operation = None
            user.save(update_fields=["multi_stage_enabled", "assigned_operation"])
            user.assigned_operations.set(operation_ids)
        elif len(operation_ids) == 1:
            user.multi_stage_enabled = False
            user.assigned_operation_id = operation_ids[0]
            user.save(update_fields=["multi_stage_enabled", "assigned_operation"])
            user.assigned_operations.clear()
        else:
            user.multi_stage_enabled = False
            user.assigned_operation = None
            user.save(update_fields=["multi_stage_enabled", "assigned_operation"])
            user.assigned_operations.clear()

    def create(self, validated_data):
        password = validated_data.pop("password", None) or get_random_string(12)
        assigned_operations = validated_data.pop("assigned_operations", None)
        assigned_machines = validated_data.pop("assigned_machines", None)
        user = User(**validated_data)
        if user.role in SUPER_ADMIN_LEVEL_ROLES:
            user.is_staff = True
            user.is_superuser = True
        user.password = make_password(password)
        user.save()
        if assigned_operations is not None:
            user.assigned_operations.set(assigned_operations)
        if assigned_machines is not None:
            user.assigned_machines.set(assigned_machines)
            self._sync_operations_from_machines(user, assigned_machines)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        assigned_machines = validated_data.get("assigned_machines")
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        if assigned_machines is not None:
            self._sync_operations_from_machines(user, list(user.assigned_machines.all()))
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
