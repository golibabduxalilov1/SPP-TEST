from rest_framework import serializers

from .constants import DEFAULT_ROUTE_KEY, ROUTE_TEMPLATES
from .models import Label, Order, Part, PartRoute, Product
from .services import assign_route


class PartRouteSerializer(serializers.ModelSerializer):
    operation_code = serializers.CharField(source="operation.code", read_only=True)
    operation_name = serializers.CharField(source="operation.name", read_only=True)

    class Meta:
        model = PartRoute
        fields = ["id", "operation", "operation_code", "operation_name", "sequence_index", "status", "completed_at"]


class PartSerializer(serializers.ModelSerializer):
    routes = PartRouteSerializer(many=True, read_only=True)
    current_operation_code = serializers.CharField(source="current_operation.code", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    route_key = serializers.ChoiceField(
        choices=[(key, key) for key in ROUTE_TEMPLATES],
        write_only=True,
        required=False,
        default=DEFAULT_ROUTE_KEY,
    )

    class Meta:
        model = Part
        fields = [
            "id", "order", "order_no", "product", "code", "name", "material", "color",
            "length_mm", "width_mm", "thickness_mm", "quantity", "area_m2", "edge_meter",
            "drilling_count", "qr_token", "current_operation", "current_operation_code",
            "status", "created_at", "routes", "route_key",
        ]
        read_only_fields = ["qr_token", "created_at", "current_operation"]

    def create(self, validated_data):
        route_key = validated_data.pop("route_key", DEFAULT_ROUTE_KEY)
        part = super().create(validated_data)
        assign_route(part, route_key)
        return part


class ProductSerializer(serializers.ModelSerializer):
    parts = PartSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "order", "name", "notes", "parts"]


class OrderListSerializer(serializers.ModelSerializer):
    parts_total = serializers.SerializerMethodField()
    parts_completed = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_no", "customer_name", "customer_phone", "product_name", "deadline",
            "priority", "status", "created_at", "parts_total", "parts_completed",
        ]

    def get_parts_total(self, obj):
        return obj.parts.count()

    def get_parts_completed(self, obj):
        return obj.parts.filter(status="completed").count()


class OrderDetailSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    parts = PartSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_no", "customer_name", "customer_phone", "product_name", "notes",
            "deadline", "priority", "status", "external_system", "external_order_id",
            "external_customer_id", "approved_price", "approved_deadline", "customer_confirmed_at",
            "odoo_sync_status", "qr_token", "created_at", "updated_at", "products", "parts",
        ]
        read_only_fields = ["order_no", "qr_token", "created_at", "updated_at"]


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = "__all__"
