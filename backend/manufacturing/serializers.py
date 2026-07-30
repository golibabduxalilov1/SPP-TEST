from rest_framework import serializers

from .models import Device, Machine, Operation, Printer, Tsex
from .units import MEASURE_UNIT_LABELS


class OperationSerializer(serializers.ModelSerializer):
    measure_unit_label = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = [
            "id", "code", "name", "measure_unit", "measure_unit_label",
            "qr_scan_required", "order_index", "is_active",
        ]
        read_only_fields = fields

    def get_measure_unit_label(self, obj):
        return MEASURE_UNIT_LABELS.get(obj.measure_unit, obj.measure_unit)


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
