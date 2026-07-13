from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import log_action, push_live_log
from orders.models import Order
from packaging.models import Package
from packaging.serializers import PackageSerializer

from .models import WarehouseEvent
from .serializers import WarehouseEventSerializer


class WarehousePackagesView(APIView):
    def get(self, request):
        packages = Package.objects.filter(status__in=[Package.Status.COMPLETED, Package.Status.WAREHOUSE]) \
            .select_related("order").prefetch_related("items").order_by("-created_at")
        return Response(PackageSerializer(packages, many=True).data)


class WarehouseReceiveView(APIView):
    def post(self, request):
        qr_token = request.data.get("qr_token")
        package_id = request.data.get("package_id")
        package = Package.objects.filter(qr_token=qr_token).first() if qr_token else Package.objects.filter(id=package_id).first()
        if not package:
            return Response({"detail": "Qadoq topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        if package.status == Package.Status.WAREHOUSE:
            return Response({"detail": "Bu qadoq allaqachon omborda"}, status=status.HTTP_409_CONFLICT)
        if package.status != Package.Status.COMPLETED:
            return Response({"detail": "Qadoq hali yakunlanmagan"}, status=status.HTTP_409_CONFLICT)

        package.status = Package.Status.WAREHOUSE
        package.save(update_fields=["status"])
        WarehouseEvent.objects.create(package=package, event_type=WarehouseEvent.EventType.RECEIVE, employee=request.user)
        order = package.order
        if order.status != Order.Status.DELIVERED:
            order.status = Order.Status.WAREHOUSE
            order.save(update_fields=["status"])
        push_live_log("warehouse", f"Qadoq omborga qabul qilindi: {package.package_no}")
        log_action(request.user, "warehouse.receive", "Package", package.id)
        return Response(PackageSerializer(package).data)


class WarehouseDeliverView(APIView):
    def post(self, request):
        package = Package.objects.filter(id=request.data.get("package_id")).first()
        if not package:
            return Response({"detail": "Qadoq topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        if package.status != Package.Status.WAREHOUSE:
            return Response({"detail": "Qadoq omborda emas"}, status=status.HTTP_409_CONFLICT)

        package.status = Package.Status.DELIVERED
        package.save(update_fields=["status"])
        WarehouseEvent.objects.create(package=package, event_type=WarehouseEvent.EventType.DELIVER, employee=request.user)

        order = package.order
        if not order.packages.exclude(status=Package.Status.DELIVERED).exists():
            order.status = Order.Status.DELIVERED
            order.save(update_fields=["status"])
        push_live_log("warehouse", f"Buyurtma mijozga topshirildi: #{order.order_no}")
        log_action(request.user, "warehouse.deliver", "Package", package.id)
        return Response(PackageSerializer(package).data)
