from rest_framework import serializers

from customers.models import Customer

from .constants import DEFAULT_ROUTE_KEY, ROUTE_TEMPLATES
from .models import Label, Order, OrderDetail, OrderStageProgress, Part, PartRoute, Product
from .services import assign_route, create_part_for_order_detail, sync_part_from_order_detail


ORDER_SPECIAL_STATUS_LABELS = {
    Order.Status.DRAFT: "Yangi",
    Order.Status.APPROVED: "Tasdiqlangan",
    Order.Status.CANCELLED: "Bekor qilingan",
}


def order_display_status(obj):
    """Status shown in the Orders UI: three lifecycle states or a real stage."""
    if obj.status in ORDER_SPECIAL_STATUS_LABELS:
        return {
            "type": "status",
            "value": obj.status,
            "label": ORDER_SPECIAL_STATUS_LABELS[obj.status],
            "stage_id": None,
        }

    if obj.current_stage_id:
        return {
            "type": "stage",
            "value": f"stage:{obj.current_stage_id}",
            "label": obj.current_stage.name,
            "stage_id": obj.current_stage_id,
        }

    stage_id = getattr(obj, "last_completed_stage_id", None)
    stage_name = getattr(obj, "last_completed_stage_name", None)
    if stage_id and stage_name:
        return {
            "type": "stage",
            "value": f"stage:{stage_id}",
            "label": stage_name,
            "stage_id": stage_id,
        }

    return {"type": "stage", "value": None, "label": "—", "stage_id": None}


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


class OrderDetailItemSerializer(serializers.ModelSerializer):
    qr_token = serializers.SerializerMethodField()
    part_code = serializers.SerializerMethodField()

    def get_qr_token(self, obj):
        return obj.part.qr_token if obj.part_id else None

    def get_part_code(self, obj):
        return obj.part.code if obj.part_id else None

    class Meta:
        model = OrderDetail
        fields = [
            "id", "order", "name", "length_mm", "width_mm", "thickness_mm", "quantity", "material_type",
            "part", "part_code", "qr_token",
        ]
        read_only_fields = ["part"]

    def create(self, validated_data):
        detail = super().create(validated_data)
        create_part_for_order_detail(detail)
        return detail

    def update(self, instance, validated_data):
        detail = super().update(instance, validated_data)
        sync_part_from_order_detail(detail)
        return detail


class OrderDetailItemCreateSerializer(serializers.ModelSerializer):
    """Nested input-only shape for details passed alongside order creation (no `order` yet)."""

    class Meta:
        model = OrderDetail
        fields = ["name", "length_mm", "width_mm", "thickness_mm", "quantity", "material_type"]


class OrderStageProgressSerializer(serializers.ModelSerializer):
    stage_code = serializers.CharField(source="stage.code", read_only=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    completed_by_name = serializers.SerializerMethodField()

    def get_completed_by_name(self, obj):
        if not obj.completed_by:
            return None
        return obj.completed_by.get_full_name() or obj.completed_by.phone

    class Meta:
        model = OrderStageProgress
        fields = [
            "id", "stage", "stage_code", "stage_name", "status",
            "started_at", "completed_at", "completed_by", "completed_by_name",
        ]


class OrderListSerializer(serializers.ModelSerializer):
    parts_total = serializers.SerializerMethodField()
    parts_completed = serializers.SerializerMethodField()
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True)
    details = OrderDetailItemCreateSerializer(many=True, write_only=True, required=False)
    display_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_no", "customer_name", "customer_phone", "product_name", "product_type",
            "product_type_name", "deadline", "priority", "status", "created_at",
            "parts_total", "parts_completed", "details", "current_stage", "current_stage_name", "stage_status",
            "display_status",
        ]
        read_only_fields = ["current_stage", "stage_status"]

    def get_parts_total(self, obj):
        return obj.parts.count()

    def get_parts_completed(self, obj):
        return obj.parts.filter(status="completed").count()

    def get_display_status(self, obj):
        return order_display_status(obj)

    def create(self, validated_data):
        details_data = validated_data.pop("details", [])
        order = super().create(validated_data)
        for detail_data in details_data:
            detail = OrderDetail.objects.create(order=order, **detail_data)
            create_part_for_order_detail(detail)
        phone = (order.customer_phone or "").strip()
        if phone:
            Customer.objects.get_or_create(phone=phone, defaults={"name": order.customer_name or ""})
        return order


class OrderDetailSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    parts = PartSerializer(many=True, read_only=True)
    details = OrderDetailItemSerializer(many=True, read_only=True)
    product_type_name = serializers.CharField(source="product_type.name", read_only=True)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True)
    stage_progress = OrderStageProgressSerializer(many=True, read_only=True)
    display_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_no", "customer_name", "customer_phone", "product_name", "notes",
            "product_type", "product_type_name", "deadline", "priority", "status", "qr_token",
            "created_at", "updated_at", "products", "parts", "details",
            "current_stage", "current_stage_name", "stage_status", "stage_progress",
            "display_status",
        ]
        read_only_fields = [
            "order_no", "qr_token", "created_at", "updated_at", "current_stage", "stage_status",
        ]

    def get_display_status(self, obj):
        return order_display_status(obj)


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = "__all__"
