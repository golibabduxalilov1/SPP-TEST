from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from rest_framework.exceptions import ValidationError

from accounts.permissions import IsSuperAdmin, IsTechnologistOrAbove
from orders.constants import OPERATION_SEEDS
from orders.models import Order
from orders.production_workflow import advance_orders_past_deactivated_stage
from .models import Device, Machine, Operation, Printer, Tsex, Workstation
from .serializers import (
    DeviceSerializer, MachineSerializer, OperationSerializer,
    PrinterSerializer, TsexSerializer, WorkstationSerializer,
)


class OperationViewSet(viewsets.ModelViewSet):
    queryset = Operation.objects.all()
    serializer_class = OperationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_fields = ["is_active"]
    search_fields = ["name", "code"]
    ordering_fields = ["order_index", "name"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        was_active = serializer.instance.is_active
        instance = serializer.save()
        if was_active and not instance.is_active:
            advance_orders_past_deactivated_stage(instance)

    def perform_destroy(self, instance):
        default_codes = {seed["code"] for seed in OPERATION_SEEDS}
        if instance.code in default_codes:
            raise ValidationError({
                "detail": "Default ishlab chiqarish bosqichini o'chirib bo'lmaydi. Uni nofaol qilib belgilang."
            })

        active_statuses = [
            Order.Status.APPROVED,
            Order.Status.IN_PRODUCTION,
            Order.Status.PARTIALLY_READY,
            Order.Status.READY_FOR_PACKAGING,
            Order.Status.PACKAGING,
        ]
        if instance.part_routes.filter(part__order__status__in=active_statuses).exists():
            raise ValidationError({
                "detail": "Bu bosqichga faol buyurtma yoki detallar bog'langan. O'chirish o'rniga uni nofaol qilib belgilang."
            })

        if (
            instance.part_routes.exists()
            or instance.current_parts.exists()
            or instance.current_orders.exists()
            or instance.order_stage_progress.exists()
            or instance.workstations.exists()
            or instance.machines.exists()
        ):
            raise ValidationError({
                "detail": "Bu bosqichga tarixiy yoki sozlama ma'lumotlari bog'langan. O'chirish o'rniga uni nofaol qilib belgilang."
            })

        instance.delete()


class TsexViewSet(viewsets.ModelViewSet):
    queryset = Tsex.objects.all()
    serializer_class = TsexSerializer
    permission_classes = [IsAuthenticated]


class WorkstationViewSet(viewsets.ModelViewSet):
    queryset = Workstation.objects.select_related("tsex", "operation").all()
    serializer_class = WorkstationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["tsex", "operation", "status"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]


class PrinterViewSet(viewsets.ModelViewSet):
    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    permission_classes = [IsAuthenticated]


class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.select_related("operation", "workstation").all()
    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["workstation", "operation", "status"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), IsTechnologistOrAbove()]
        return [IsAuthenticated()]
