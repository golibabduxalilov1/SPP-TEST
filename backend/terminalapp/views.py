from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanScanOrderStatus, IsMasterOrAbove
from core.audit import log_action, push_live_log
from manufacturing.models import Machine, Operation, Workstation
from orders.models import Order, Part, PartRoute
from orders.production_workflow import ProductionWorkflowError, start_production_workflow
from orders.serializers import PartSerializer
from orders.status_flow import next_allowed_statuses

from .models import Conflict, OfflineSyncBatch, ScanEvent
from .serializers import ConflictSerializer, ScanEventSerializer, SingleScanSerializer, SyncBatchSerializer
from .services import process_scan


class TerminalWorkstationsView(APIView):
    """Public listing so the terminal login screen can show post names before authenticating."""

    permission_classes = []

    def get(self, request):
        workstations = Workstation.objects.filter(status="active", operation__is_active=True).select_related("tsex", "operation")
        return Response(
            [
                {
                    "id": w.id,
                    "name": w.name,
                    "operation_code": w.operation.code,
                    "operation_name": w.operation.name,
                    "tsex": w.tsex.name,
                }
                for w in workstations
            ]
        )


class TerminalBootstrapView(APIView):
    def get(self, request):
        workstation_id = request.query_params.get("workstation_id")
        workstation = Workstation.objects.filter(id=workstation_id).select_related("tsex", "operation").first()
        operations = list(
            Operation.objects.filter(is_active=True)
            .order_by("order_index", "id")
            .values("code", "name", "measure_unit", "qr_scan_required", "order_index")
        )

        parts_qs = Part.objects.none()
        if workstation:
            parts_qs = (
                Part.objects.filter(current_operation=workstation.operation, status__in=["pending", "in_progress"])
                .select_related("order")
                .prefetch_related("routes__operation")
                .order_by("order__priority", "order__deadline")[:200]
            )

        machines = list(
            Machine.objects.filter(workstation=workstation).values("id", "machine_id", "name", "status")
        ) if workstation else []

        return Response(
            {
                "server_time": timezone.now(),
                "workstation": {
                    "id": workstation.id,
                    "name": workstation.name,
                    "operation_code": workstation.operation.code,
                    "operation_name": workstation.operation.name,
                    "tsex": workstation.tsex.name,
                } if workstation else None,
                "operations": operations,
                "machines": machines,
                "parts": PartSerializer(parts_qs, many=True).data,
                "offline_ready": True,
            }
        )


class TerminalScanView(APIView):
    def post(self, request):
        serializer = SingleScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        workstation = Workstation.objects.filter(id=data.get("workstation_id")).first()
        machine = Machine.objects.filter(id=data.get("machine_id")).first()
        import uuid

        result = process_scan(
            client_scan_id=data.get("client_scan_id") or str(uuid.uuid4()),
            qr_token=data["qr_token"],
            operation_code=data["operation_code"],
            employee=request.user,
            device_id=request.headers.get("X-Device-Id", ""),
            workstation=workstation,
            machine=machine,
            scanned_at_client=data.get("scanned_at_client") or timezone.now(),
            source=ScanEvent.Source.ONLINE,
        )
        http_status = status.HTTP_200_OK if result["status"] == "synced" else status.HTTP_409_CONFLICT
        return Response(result, status=http_status)


class TerminalSyncView(APIView):
    def post(self, request):
        serializer = SyncBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if OfflineSyncBatch.objects.filter(client_batch_id=data["client_batch_id"]).exists():
            existing = OfflineSyncBatch.objects.get(client_batch_id=data["client_batch_id"])
            return Response(
                {
                    "batch_id": f"srv-batch-{existing.id}",
                    "accepted": existing.accepted_count,
                    "conflict": existing.conflict_count,
                    "failed": existing.failed_count,
                    "results": ScanEventSerializer(existing.scans.all(), many=True).data,
                }
            )

        workstation = Workstation.objects.filter(id=data.get("workstation_id")).first()
        batch = OfflineSyncBatch.objects.create(
            client_batch_id=data["client_batch_id"],
            device_id=data["device_id"],
            workstation=workstation,
            employee=request.user,
        )

        results = []
        accepted = conflict = failed = 0
        for scan in data["scans"]:
            result = process_scan(
                client_scan_id=scan["client_scan_id"],
                qr_token=scan["qr_token"],
                operation_code=scan["operation_code"],
                employee=request.user,
                device_id=data["device_id"],
                workstation=workstation,
                scanned_at_client=scan.get("scanned_at_client"),
                source=ScanEvent.Source.OFFLINE_SYNC,
                batch=batch,
            )
            results.append(result)
            if result["status"] == "synced":
                accepted += 1
            elif result["status"] == "conflict":
                conflict += 1
            else:
                failed += 1

        batch.accepted_count = accepted
        batch.conflict_count = conflict
        batch.failed_count = failed
        batch.save(update_fields=["accepted_count", "conflict_count", "failed_count"])
        log_action(request.user, "terminal.sync", "OfflineSyncBatch", batch.id,
                   {"accepted": accepted, "conflict": conflict, "failed": failed})

        return Response(
            {
                "batch_id": f"srv-batch-{batch.id}",
                "accepted": accepted,
                "conflict": conflict,
                "failed": failed,
                "results": results,
            }
        )


class SyncStatusView(APIView):
    def get(self, request, batch_id):
        batch = OfflineSyncBatch.objects.filter(client_batch_id=batch_id).first()
        if not batch:
            return Response({"detail": "Topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "batch_id": f"srv-batch-{batch.id}",
                "accepted": batch.accepted_count,
                "conflict": batch.conflict_count,
                "failed": batch.failed_count,
                "results": ScanEventSerializer(batch.scans.all(), many=True).data,
            }
        )


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Conflict.objects.select_related("scan_event__part", "scan_event__order", "scan_event__operation").all()
    serializer_class = ConflictSerializer
    permission_classes = [IsAuthenticated, IsMasterOrAbove]
    filterset_fields = ["status", "reason_code"]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        conflict = self.get_object()
        resolution = request.data.get("resolution")
        note = request.data.get("note", "")
        if resolution not in ("accepted", "rejected", "requeued"):
            return Response({"detail": "resolution noto'g'ri"}, status=status.HTTP_400_BAD_REQUEST)

        scan = conflict.scan_event
        if resolution == "accepted" and scan.part and scan.operation:
            route_step = scan.part.routes.filter(operation=scan.operation).first()
            if route_step and route_step.status != PartRoute.Status.COMPLETED:
                route_step.status = PartRoute.Status.COMPLETED
                route_step.completed_at = timezone.now()
                route_step.completed_by = request.user
                route_step.save(update_fields=["status", "completed_at", "completed_by"])
                next_step = scan.part.routes.filter(status=PartRoute.Status.PENDING).order_by("sequence_index").first()
                scan.part.current_operation = next_step.operation if next_step else None
                scan.part.status = Part.Status.COMPLETED if not next_step else Part.Status.IN_PROGRESS
                scan.part.save(update_fields=["current_operation", "status"])
                scan.order.recalculate_status()
            scan.status = ScanEvent.Status.ACCEPTED
            scan.save(update_fields=["status"])

        conflict.status = Conflict.Status.RESOLVED
        conflict.resolution = resolution
        conflict.resolution_note = note
        conflict.resolved_by = request.user
        conflict.resolved_at = timezone.now()
        conflict.save()
        log_action(request.user, "conflict.resolve", "Conflict", conflict.id, {"resolution": resolution})
        return Response(ConflictSerializer(conflict).data)


def _order_qr_summary(order):
    return {
        "id": order.id,
        "order_no": order.order_no,
        "product_name": order.product_name,
        "customer_name": order.customer_name,
        "status": order.status,
        "status_display": order.get_status_display(),
        "next_statuses": [
            {"value": value, "label": Order.Status(value).label}
            for value in next_allowed_statuses(order.status)
        ],
    }


class OrderQRLookupView(APIView):
    """Looks up an Order by its QR token and reports the status transitions a
    QR scan may perform next (see orders.status_flow.next_allowed_statuses)."""

    permission_classes = [IsAuthenticated, CanScanOrderStatus]

    def post(self, request):
        qr_token = request.data.get("qr_token", "").strip()
        order = Order.objects.filter(qr_token=qr_token).first()
        if not order:
            return Response({"detail": "Bu QR kodga mos buyurtma topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_order_qr_summary(order))


class OrderQRStatusUpdateView(APIView):
    """Applies a QR-scanned status transition to an Order and records it in
    the audit log, same as every other status-changing action in the app."""

    permission_classes = [IsAuthenticated, CanScanOrderStatus]

    def post(self, request):
        qr_token = request.data.get("qr_token", "").strip()
        new_status = request.data.get("new_status")
        order = Order.objects.filter(qr_token=qr_token).first()
        if not order:
            return Response({"detail": "Bu QR kodga mos buyurtma topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        allowed = {choice for choice in next_allowed_statuses(order.status)}
        if new_status not in allowed:
            return Response(
                {"detail": "Bu statusga o'tish mumkin emas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = order.status
        try:
            with transaction.atomic():
                order.status = new_status
                order.save(update_fields=["status", "updated_at"])
                if new_status == Order.Status.APPROVED:
                    order = start_production_workflow(order.id)
        except ProductionWorkflowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        log_action(
            request.user, "order.qr_status_update", "Order", order.id,
            {"from": old_status, "to": new_status, "method": "qr_scan"},
        )
        push_live_log(
            "order",
            f"QR skan: #{order.order_no} statusi {order.get_status_display()} ga o'tkazildi",
            {"order_id": order.id, "from": old_status, "to": new_status},
        )
        return Response(_order_qr_summary(order))
