from django.http import FileResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import log_action, push_live_log
from orders.models import Order

from .labels import render_package_label_pdf
from .models import Package
from .serializers import PackageSerializer
from .services import missing_parts_count, packaging_scan


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Package.objects.select_related("order").prefetch_related("items__part").all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "order"]


class PackagingStartView(APIView):
    def post(self, request):
        order_id = request.data.get("order_id")
        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({"detail": "Buyurtma topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        package = Package.objects.filter(order=order, status=Package.Status.OPEN).first()
        if not package:
            package = Package.objects.create(order=order, created_by=request.user)
        return Response(PackageSerializer(package).data)


class PackagingScanView(APIView):
    def post(self, request):
        package = Package.objects.filter(id=request.data.get("package_id")).first()
        qr_token = request.data.get("qr_token")
        if not package:
            return Response({"detail": "Qadoq topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        result = packaging_scan(package, qr_token, request.user)
        http_status = status.HTTP_200_OK if result["status"] == "ok" else status.HTTP_409_CONFLICT
        return Response(result, status=http_status)


class PackagingCompleteView(APIView):
    def post(self, request):
        package = Package.objects.filter(id=request.data.get("package_id")).first()
        if not package:
            return Response({"detail": "Qadoq topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        missing = missing_parts_count(package)
        if missing > 0:
            return Response(
                {"status": "error", "message": f"Qadoqlash to'liq emas: {missing} ta detal yetishmayapti"},
                status=status.HTTP_409_CONFLICT,
            )
        package.status = Package.Status.COMPLETED
        package.completed_at = timezone.now()
        package.save(update_fields=["status", "completed_at"])
        push_live_log("packaging", f"Buyurtma #{package.order.order_no} qadoqlandi")
        log_action(request.user, "packaging.complete", "Package", package.id)
        return Response(PackageSerializer(package).data)


class PackageLabelPrintView(APIView):
    def post(self, request):
        package = Package.objects.filter(id=request.data.get("package_id")).first()
        if not package:
            return Response({"detail": "Qadoq topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        pdf = render_package_label_pdf(package)
        return FileResponse(pdf, as_attachment=True, filename=f"{package.package_no}.pdf", content_type="application/pdf")
