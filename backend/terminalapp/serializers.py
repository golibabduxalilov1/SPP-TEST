from rest_framework import serializers

from .models import Conflict, OfflineSyncBatch, ScanEvent


class ScanEventSerializer(serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    operation_name = serializers.CharField(source="operation.name", read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ScanEvent
        fields = "__all__"

    def get_employee_name(self, obj):
        return obj.employee.get_full_name() or obj.employee.username if obj.employee else None


class SingleScanSerializer(serializers.Serializer):
    client_scan_id = serializers.CharField(required=False)
    qr_token = serializers.CharField()
    operation_code = serializers.CharField()
    workstation_id = serializers.IntegerField(required=False, allow_null=True)
    machine_id = serializers.IntegerField(required=False, allow_null=True)
    scanned_at_client = serializers.DateTimeField(required=False, allow_null=True)


class SyncScanItemSerializer(serializers.Serializer):
    client_scan_id = serializers.CharField()
    qr_token = serializers.CharField()
    operation_code = serializers.CharField()
    scanned_at_client = serializers.DateTimeField(required=False, allow_null=True)


class SyncBatchSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    workstation_id = serializers.IntegerField(required=False, allow_null=True)
    employee_id = serializers.IntegerField(required=False, allow_null=True)
    client_batch_id = serializers.CharField()
    scans = SyncScanItemSerializer(many=True)


class ConflictSerializer(serializers.ModelSerializer):
    scan = ScanEventSerializer(source="scan_event", read_only=True)

    class Meta:
        model = Conflict
        fields = "__all__"


class OfflineSyncBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineSyncBatch
        fields = "__all__"
