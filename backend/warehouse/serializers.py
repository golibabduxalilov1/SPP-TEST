from rest_framework import serializers

from .models import WarehouseEvent


class WarehouseEventSerializer(serializers.ModelSerializer):
    package_no = serializers.CharField(source="package.package_no", read_only=True)
    order_no = serializers.CharField(source="package.order.order_no", read_only=True)

    class Meta:
        model = WarehouseEvent
        fields = "__all__"
