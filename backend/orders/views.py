from django.http import FileResponse
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanCompleteProductionStage, IsSuperAdmin, IsTechnologistOrAbove
from core.audit import log_action, push_live_log
from .export import render_orders_excel, render_orders_pdf
from .labels import render_labels_pdf
from .models import Label, Order, OrderDetail, Part
from .production_workflow import (
    ProductionWorkflowError, approve_order, complete_current_stage, start_production_workflow,
)
from .serializers import (
    LabelSerializer, OrderDetailItemSerializer, OrderDetailSerializer, OrderListSerializer, PartSerializer,
)
from .services import import_parts_from_file


class OrderViewSet(viewsets.ModelViewSet):
    queryset = (
        Order.objects.select_related("current_stage")
        .prefetch_related("parts", "stage_progress__stage", "stage_progress__completed_by")
        .all()
    )
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority"]
    search_fields = ["order_no", "customer_name", "product_name"]

    def get_serializer_class(self):
        if self.action in ("retrieve", "update", "partial_update"):
            return OrderDetailSerializer
        return OrderListSerializer

    def get_permissions(self):
        if self.action == "approve":
            return [IsAuthenticated(), IsSuperAdmin()]
        if self.action == "complete_current_stage_action":
            return [IsAuthenticated(), CanCompleteProductionStage()]
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                instance = serializer.save(created_by=self.request.user)
                if instance.status == Order.Status.APPROVED:
                    instance = start_production_workflow(instance.id)
        except ProductionWorkflowError as exc:
            raise ValidationError({"status": str(exc)}) from exc
        log_action(self.request.user, "order.create", "Order", instance.id, {"order_no": instance.order_no})
        push_live_log("order", f"Yangi buyurtma qabul qilindi: #{instance.order_no}")

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        try:
            with transaction.atomic():
                instance = serializer.save()
                if previous_status != Order.Status.APPROVED and instance.status == Order.Status.APPROVED:
                    instance = start_production_workflow(instance.id)
        except ProductionWorkflowError as exc:
            raise ValidationError({"status": str(exc)}) from exc
        log_action(self.request.user, "order.update", "Order", instance.id, {"status": instance.status})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsSuperAdmin])
    def approve(self, request, pk=None):
        order = self.get_object()
        try:
            order = approve_order(order.id)
        except ProductionWorkflowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_action(request.user, "order.approve", "Order", order.id, {"order_no": order.order_no})
        push_live_log("order", f"Buyurtma tasdiqlandi: #{order.order_no}", {"order_id": order.id})
        return Response(OrderDetailSerializer(order).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="complete-current-stage",
        permission_classes=[IsAuthenticated, CanCompleteProductionStage],
    )
    def complete_current_stage_action(self, request, pk=None):
        order = self.get_object()
        previous_stage = order.current_stage
        try:
            order = complete_current_stage(order.id, completed_by=request.user)
        except ProductionWorkflowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        details = {
            "order_no": order.order_no,
            "completed_stage": previous_stage.code if previous_stage else None,
            "next_stage": order.current_stage.code if order.current_stage else None,
        }
        log_action(request.user, "order.complete_stage", "Order", order.id, details)
        if order.current_stage:
            message = f"#{order.order_no}: {previous_stage.name} yakunlandi, {order.current_stage.name} boshlandi"
        else:
            message = f"#{order.order_no}: ishlab chiqarish tugallandi"
        push_live_log("production", message, {"order_id": order.id, **details})
        return Response(OrderDetailSerializer(order).data)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def import_file(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Fayl topilmadi"}, status=status.HTTP_400_BAD_REQUEST)
        result = import_parts_from_file(uploaded, request.user)
        log_action(request.user, "order.import", details=result)
        return Response(result)

    @action(detail=False, methods=["get"])
    def export(self, request):
        orders = self.filter_queryset(self.get_queryset())
        # NOTE: query param is named "file_type", not "format" -- DRF reserves "format" for its
        # own content-negotiation (?format=json/api) and raises Http404 if that value doesn't
        # match a registered renderer, before this view ever runs.
        fmt = (request.query_params.get("file_type") or "pdf").lower()
        if fmt in ("excel", "xlsx"):
            buf = render_orders_excel(orders)
            response = FileResponse(
                buf, as_attachment=True, filename="buyurtmalar.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            buf = render_orders_pdf(orders)
            response = FileResponse(buf, as_attachment=True, filename="buyurtmalar.pdf", content_type="application/pdf")
        log_action(request.user, "order.export", details={"format": fmt, "count": orders.count()})
        return response


class PartViewSet(viewsets.ModelViewSet):
    queryset = Part.objects.select_related("order", "current_operation").prefetch_related("routes__operation").all()
    serializer_class = PartSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["order", "status", "current_operation"]
    search_fields = ["code", "name", "qr_token"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]


class OrderDetailItemViewSet(viewsets.ModelViewSet):
    queryset = OrderDetail.objects.select_related("order", "part").all()
    serializer_class = OrderDetailItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["order"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        part = instance.part
        instance.delete()
        if part:
            part.delete()


class LabelPreviewView(APIView):
    def post(self, request):
        part_ids = request.data.get("part_ids", [])
        parts = Part.objects.filter(id__in=part_ids).select_related("order")
        return Response(PartSerializer(parts, many=True).data)


class LabelPrintView(APIView):
    def post(self, request):
        part_ids = request.data.get("part_ids", [])
        width = int(request.data.get("width_mm", 70))
        height = int(request.data.get("height_mm", 50))
        parts = list(
            Part.objects.filter(id__in=part_ids)
            .select_related("order")
            .prefetch_related("routes__operation")
        )
        if not parts:
            return Response({"detail": "Detallar topilmadi"}, status=status.HTTP_400_BAD_REQUEST)
        for part in parts:
            Label.objects.create(part=part, printed_by=request.user, label_width_mm=width, label_height_mm=height)
        pdf_buffer = render_labels_pdf(parts, width, height)
        log_action(request.user, "label.print", details={"count": len(parts)})
        return FileResponse(pdf_buffer, as_attachment=True, filename="spp-labels.pdf", content_type="application/pdf")
