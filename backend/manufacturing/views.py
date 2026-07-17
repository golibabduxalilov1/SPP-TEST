from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsTechnologistOrAbove
from .models import Device, Machine, Operation, Printer, Tsex, Workstation
from .serializers import (
    DeviceSerializer, MachineSerializer, OperationSerializer,
    PrinterSerializer, TsexSerializer, WorkstationSerializer,
)


class OperationViewSet(viewsets.ModelViewSet):
    queryset = Operation.objects.all()
    serializer_class = OperationSerializer
    permission_classes = [IsAuthenticated]


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
