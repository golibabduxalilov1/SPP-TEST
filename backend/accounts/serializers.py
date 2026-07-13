from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role, User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "phone", "role", "role_display",
            "pin_code", "is_active_employee", "is_active", "is_staff", "is_superuser",
            "date_joined", "password",
        ]
        read_only_fields = ["date_joined", "is_staff", "is_superuser"]

    def create(self, validated_data):
        password = validated_data.pop("password", None) or User.objects.make_random_password()
        user = User(**validated_data)
        if user.role == Role.SUPER_ADMIN:
            user.is_staff = True
            user.is_superuser = True
        user.password = make_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class AdminLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.can_use_admin:
            raise serializers.ValidationError("Bu foydalanuvchi admin panelga kira olmaydi.")
        data["user"] = UserSerializer(self.user).data
        return data


class TerminalLoginSerializer(serializers.Serializer):
    pin_code = serializers.CharField(max_length=8, required=False)
    badge_token = serializers.CharField(max_length=64, required=False)
    device_id = serializers.CharField(max_length=128)
    workstation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("pin_code") and not attrs.get("badge_token"):
            raise serializers.ValidationError("PIN yoki badge token kerak")
        return attrs
