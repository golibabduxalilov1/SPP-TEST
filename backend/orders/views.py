from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSuperAdmin, IsTechnologistOrAbove
from core.audit import log_action, push_live_log
from .export import render_orders_excel, render_orders_pdf
from .labels import render_labels_pdf
from .models import Label, Order, OrderDetail, Part
from .serializers import (
    LabelSerializer, OrderDetailItemSerializer, OrderDetailSerializer, OrderListSerializer, PartSerializer,
)
from .services import import_parts_from_file


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().prefetch_related("parts")
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority"]
    search_fields = ["order_no", "customer_name", "product_name"]

    def get_serializer_class(self):
        if self.action in ("retrieve", "update", "partial_update"):
            return OrderDetailSerializer
        return OrderListSerializer

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(self.request.user, "order.create", "Order", instance.id, {"order_no": instance.order_no})
        push_live_log("order", f"Yangi buyurtma qabul qilindi: #{instance.order_no}")

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, "order.update", "Order", instance.id, {"status": instance.status})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsSuperAdmin])
    def approve(self, request, pk=None):
        order = self.get_object()
        if order.status != Order.Status.DRAFT:
            return Response(
                {"detail": "Faqat yangi (tasdiqlanmagan) buyurtmalarni tasdiqlash mumkin"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = Order.Status.APPROVED
        order.save(update_fields=["status", "updated_at"])
        log_action(request.user, "order.approve", "Order", order.id, {"order_no": order.order_no})
        push_live_log("order", f"Buyurtma tasdiqlandi: #{order.order_no}", {"order_id": order.id})
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
