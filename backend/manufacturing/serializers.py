from rest_framework import serializers

from .models import Device, Machine, Operation, Printer, Tsex, Workstation


class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operation
        fields = "__all__"


class TsexSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tsex
        fields = "__all__"


class WorkstationSerializer(serializers.ModelSerializer):
    tsex_name = serializers.CharField(source="tsex.name", read_only=True)
    operation_name = serializers.CharField(source="operation.name", read_only=True)
    operation_code = serializers.CharField(source="operation.code", read_only=True)

    class Meta:
        model = Workstation
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
    workstation_name = serializers.CharField(source="workstation.name", read_only=True)

    class Meta:
        model = Machine
        fields = "__all__"
