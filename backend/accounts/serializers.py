from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import SUPER_ADMIN_LEVEL_ROLES, User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    assigned_workstation_name = serializers.SerializerMethodField()
    assigned_workstations_detail = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "phone", "role", "role_display",
            "pin_code", "is_active_employee", "is_active", "is_staff", "is_superuser",
            "date_joined", "password", "multi_stage_enabled", "assigned_workstation",
            "assigned_workstation_name", "assigned_workstations", "assigned_workstations_detail",
        ]
        read_only_fields = ["date_joined", "is_staff", "is_superuser"]
        extra_kwargs = {
            "username": {"required": False, "allow_blank": True},
            "pin_code": {"allow_null": True},
        }

    def get_assigned_workstation_name(self, obj):
        return obj.assigned_workstation.name if obj.assigned_workstation_id else None

    def get_assigned_workstations_detail(self, obj):
        return [{"id": w.id, "name": w.name} for w in obj.assigned_workstations.all()]

    def create(self, validated_data):
        password = validated_data.pop("password", None) or get_random_string(12)
        assigned_workstations = validated_data.pop("assigned_workstations", None)
        user = User(**validated_data)
        if user.role in SUPER_ADMIN_LEVEL_ROLES:
            user.is_staff = True
            user.is_superuser = True
        user.password = make_password(password)
        user.save()
        if assigned_workstations is not None:
            user.assigned_workstations.set(assigned_workstations)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
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
    pin_code = serializers.CharField(max_length=8)


class TerminalLoginSerializer(serializers.Serializer):
    pin_code = serializers.CharField(max_length=8, required=False)
    badge_token = serializers.CharField(max_length=64, required=False)
    device_id = serializers.CharField(max_length=128)
    workstation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("pin_code") and not attrs.get("badge_token"):
            raise serializers.ValidationError("PIN yoki badge token kerak")
        return attrs
