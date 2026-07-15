import logging

from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTechnologistOrAbove
from core.audit import log_action, push_live_log
from .adapters import ManualOrderSource
from .labels import render_labels_pdf
from .models import Label, Order, Part
from .serializers import LabelSerializer, OrderDetailSerializer, OrderListSerializer, PartSerializer
from .services import create_order, import_parts_from_file

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().prefetch_related("parts")
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority"]
    search_fields = ["order_no", "customer_name", "product_name"]

    def get_serializer_class(self):
        if self.action in ("retrieve",):
            return OrderDetailSerializer
        return OrderListSerializer

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        order_input = ManualOrderSource().parse(serializer.validated_data)
        instance = create_order(order_input, created_by=self.request.user)
        serializer.instance = instance
        log_action(self.request.user, "order.create", "Order", instance.id, {"order_no": instance.order_no})
        push_live_log("order", f"Yangi buyurtma qabul qilindi: #{instance.order_no}")

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, "order.update", "Order", instance.id, {"status": instance.status})

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def import_file(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Fayl topilmadi"}, status=status.HTTP_400_BAD_REQUEST)
        result = import_parts_from_file(uploaded, request.user)
        log_action(request.user, "order.import", details=result)
        return Response(result)


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


class OdooWebhookView(APIView):
    """Stub receiver for a future Odoo integration — not wired to anything yet.

    Real Odoo order ingestion will implement OrderSource.parse() and call
    services.create_order(), the same path ManualOrderSource already uses.
    """

    permission_classes = []

    def post(self, request):
        logger.info("Odoo webhook stub received payload: %s", request.data)
        return Response(
            {"detail": "Odoo integratsiyasi hali faollashtirilmagan"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
