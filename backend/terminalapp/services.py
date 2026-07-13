from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.audit import push_live_log
from manufacturing.models import Operation
from orders.models import Order, Part, PartRoute

from .models import Conflict, ScanEvent


def _reject(client_scan_id, qr_token, error_code, source, employee, device_id, workstation, operation=None,
            part=None, order=None, batch=None):
    scan = ScanEvent.objects.create(
        client_scan_id=client_scan_id,
        qr_token=qr_token,
        part=part,
        order=order,
        operation=operation,
        workstation=workstation,
        employee=employee,
        device_id=device_id,
        source=source,
        status=ScanEvent.Status.CONFLICT,
        error_code=error_code,
        batch=batch,
    )
    Conflict.objects.create(scan_event=scan, reason_code=error_code)
    push_live_log("conflict", f"Konflikt: {qr_token} — {error_code}", {"scan_id": scan.id})
    return {"client_scan_id": client_scan_id, "status": "conflict", "error_code": error_code}


def process_scan(*, client_scan_id, qr_token, operation_code, employee, device_id, workstation=None,
                  machine=None, scanned_at_client=None, source=ScanEvent.Source.ONLINE, batch=None):
    existing = ScanEvent.objects.filter(client_scan_id=client_scan_id).first()
    if existing:
        return {"client_scan_id": client_scan_id, "status": "synced" if existing.status == "accepted" else existing.status,
                "error_code": existing.error_code}

    operation = Operation.objects.filter(code=operation_code).first()
    part = Part.objects.filter(qr_token=qr_token).first()

    if not part:
        return _reject(client_scan_id, qr_token, "invalid_qr", source, employee, device_id, workstation, operation, batch=batch)

    order = part.order
    if not operation:
        return _reject(client_scan_id, qr_token, "invalid_qr", source, employee, device_id, workstation, operation, part, order, batch)

    if order.status in (Order.Status.CANCELLED, Order.Status.DELIVERED):
        return _reject(client_scan_id, qr_token, "order_closed", source, employee, device_id, workstation, operation, part, order, batch)

    if workstation and workstation.operation_id != operation.id:
        return _reject(client_scan_id, qr_token, "device_not_allowed", source, employee, device_id, workstation, operation, part, order, batch)

    route_step = part.routes.filter(operation=operation).first()
    if not route_step:
        return _reject(client_scan_id, qr_token, "wrong_operation", source, employee, device_id, workstation, operation, part, order, batch)

    if route_step.status == PartRoute.Status.COMPLETED:
        return _reject(client_scan_id, qr_token, "duplicate_scan", source, employee, device_id, workstation, operation, part, order, batch)

    unfinished_previous = part.routes.filter(
        sequence_index__lt=route_step.sequence_index
    ).exclude(status__in=[PartRoute.Status.COMPLETED, PartRoute.Status.NOT_REQUIRED]).exists()
    if unfinished_previous:
        return _reject(client_scan_id, qr_token, "previous_not_completed", source, employee, device_id, workstation, operation, part, order, batch)

    if scanned_at_client:
        now = timezone.now()
        if scanned_at_client > now + timedelta(hours=1) or scanned_at_client < now - timedelta(days=7):
            return _reject(client_scan_id, qr_token, "review_required", source, employee, device_id, workstation, operation, part, order, batch)

    # All checks passed — accept the scan and advance the part along its route.
    route_step.status = PartRoute.Status.COMPLETED
    route_step.completed_at = timezone.now()
    route_step.completed_by = employee
    route_step.save(update_fields=["status", "completed_at", "completed_by"])

    next_step = part.routes.filter(status=PartRoute.Status.PENDING).order_by("sequence_index").first()
    part.current_operation = next_step.operation if next_step else None
    part.status = Part.Status.COMPLETED if not next_step else Part.Status.IN_PROGRESS
    part.save(update_fields=["current_operation", "status"])
    order.recalculate_status()

    scan = ScanEvent.objects.create(
        client_scan_id=client_scan_id,
        qr_token=qr_token,
        part=part,
        order=order,
        operation=operation,
        machine=machine,
        workstation=workstation,
        employee=employee,
        device_id=device_id,
        scanned_at_client=scanned_at_client,
        source=source,
        status=ScanEvent.Status.ACCEPTED,
        batch=batch,
    )
    employee_label = employee.get_full_name() if hasattr(employee, "get_full_name") else str(employee)
    push_live_log(
        "scan",
        f"Skan: Detal {part.code} | Usta: {employee_label or employee} | {operation.name}",
        {"part_id": part.id, "operation": operation.code},
    )
    return {"client_scan_id": client_scan_id, "status": "synced"}


def parse_client_datetime(value):
    if not value:
        return None
    return parse_datetime(value)
