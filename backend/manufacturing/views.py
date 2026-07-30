from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import CanManageProduction
from .models import Device, Machine, Operation, Printer, Tsex
from .serializers import (
    DeviceSerializer, MachineSerializer, OperationSerializer,
    PrinterSerializer, TsexSerializer,
)


class OperationViewSet(viewsets.ReadOnlyModelViewSet):
    """Standard production stages are fixed by data migration and are
    read-only at runtime — no admin CRUD, see PROJECT spec on stage
    standardization. GET-only; POST/PUT/PATCH/DELETE are not routed, so DRF
    returns 405 for them automatically."""

    queryset = Operation.objects.all()
    serializer_class = OperationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_fields = ["is_active"]
    search_fields = ["name", "code"]
    ordering_fields = ["order_index", "name"]


class TsexViewSet(viewsets.ModelViewSet):
    queryset = Tsex.objects.all()
    serializer_class = TsexSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanManageProduction()]
        return [IsAuthenticated()]


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanManageProduction()]
        return [IsAuthenticated()]


class PrinterViewSet(viewsets.ModelViewSet):
    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanManageProduction()]
        return [IsAuthenticated()]


class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.select_related("operation", "tsex").all()
    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["tsex", "operation", "status"]

    def get_permissions(self):
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), CanManageProduction()]
        return [IsAuthenticated()]
