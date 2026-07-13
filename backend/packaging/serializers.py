from rest_framework import serializers

from .models import Package, PackageItem


class PackageItemSerializer(serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    part_name = serializers.CharField(source="part.name", read_only=True)

    class Meta:
        model = PackageItem
        fields = ["id", "package", "part", "part_code", "part_name", "scanned_by", "scanned_at"]


class PackageSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    items = PackageItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Package
        fields = [
            "id", "package_no", "order", "order_no", "status", "qr_token",
            "created_by", "created_at", "completed_at", "items", "items_count",
        ]
