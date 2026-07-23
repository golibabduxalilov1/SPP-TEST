from rest_framework import serializers
from django.utils.text import slugify

from .models import Device, Machine, Operation, Printer, Tsex


class OperationSerializer(serializers.ModelSerializer):
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = [
            "id", "code", "name", "measure_unit", "qr_scan_required",
            "order_index", "is_active", "can_delete",
        ]
        read_only_fields = ["code", "can_delete"]
        extra_kwargs = {
            "measure_unit": {"required": False},
            "qr_scan_required": {"required": False},
        }

    def get_can_delete(self, obj):
        return not (
            obj.part_routes.exists()
            or obj.current_parts.exists()
            or obj.current_orders.exists()
            or obj.order_stage_progress.exists()
            or obj.machines.exists()
        )

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Bosqich nomini kiriting.")
        return value

    def validate_order_index(self, value):
        if value < 1:
            raise serializers.ValidationError("Tartib raqami 1 yoki undan katta bo'lishi kerak.")
        return value

    @staticmethod
    def _unique_code(name):
        base = slugify(name).replace("-", "_").upper()[:24] or "BOSQICH"
        code = base
        suffix = 2
        while Operation.objects.filter(code=code).exists():
            tail = f"_{suffix}"
            code = f"{base[:32 - len(tail)]}{tail}"
            suffix += 1
        return code

    def create(self, validated_data):
        validated_data.setdefault("measure_unit", "piece")
        validated_data["code"] = self._unique_code(validated_data["name"])
        return super().create(validated_data)


class TsexSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tsex
        fields = "__all__"


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"


class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = "__all__"


class MachineSerializer(serializers.ModelSerializer):
    operation_name = serializers.CharField(source="operation.name", read_only=True)
    tsex_name = serializers.CharField(source="tsex.name", read_only=True)

    class Meta:
        model = Machine
        fields = "__all__"
