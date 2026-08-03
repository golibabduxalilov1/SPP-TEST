from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.audit import log_action, push_live_log
from manufacturing.models import Operation
from orders.models import Order, OrderStageProgress, Part, PartRoute
from orders.production_workflow import ProductionWorkflowError, complete_current_stage

from .models import Conflict, ScanEvent


class UndoScanError(Exception):
    """A user-facing error when a scan can't be undone."""


def _reject(client_scan_id, qr_token, error_code, source, employee, device_id, machine, operation=None,
            part=None, order=None, batch=None):
    scan = ScanEvent.objects.create(
        client_scan_id=client_scan_id,
        qr_token=qr_token,
        part=part,
        order=order,
        operation=operation,
        machine=machine,
        employee=employee,
        device_id=device_id,
        source=source,
        status=ScanEvent.Status.CONFLICT,
        error_code=error_code,
        batch=batch,
    )
    Conflict.objects.create(scan_event=scan, reason_code=error_code)
    push_live_log("conflict", f"Muammoli holat: {qr_token} — {error_code}", {"scan_id": scan.id})
    return {"client_scan_id": client_scan_id, "status": "conflict", "error_code": error_code}


def process_scan(*, client_scan_id, qr_token, operation_code, employee, device_id,
                  machine=None, scanned_at_client=None, source=ScanEvent.Source.ONLINE, batch=None):
    existing = ScanEvent.objects.filter(client_scan_id=client_scan_id).first()
    if existing:
        return {"client_scan_id": client_scan_id, "status": "synced" if existing.status == "accepted" else existing.status,
                "error_code": existing.error_code}

    operation = Operation.objects.filter(code=operation_code).first()
    part = Part.objects.filter(qr_token=qr_token).first()

    if not part:
        return _reject(client_scan_id, qr_token, "invalid_qr", source, employee, device_id, machine, operation, batch=batch)

    order = part.order
    if not operation:
        return _reject(client_scan_id, qr_token, "invalid_qr", source, employee, device_id, machine, operation, part, order, batch)

    if order.status in (Order.Status.CANCELLED, Order.Status.DELIVERED):
        return _reject(client_scan_id, qr_token, "order_closed", source, employee, device_id, machine, operation, part, order, batch)

    if machine and machine.operation_id != operation.id:
        return _reject(client_scan_id, qr_token, "device_not_allowed", source, employee, device_id, machine, operation, part, order, batch)

    route_step = part.routes.filter(operation=operation).first()
    if not route_step:
        return _reject(client_scan_id, qr_token, "wrong_operation", source, employee, device_id, machine, operation, part, order, batch)

    if route_step.status == PartRoute.Status.COMPLETED:
        return _reject(client_scan_id, qr_token, "duplicate_scan", source, employee, device_id, machine, operation, part, order, batch)

    unfinished_previous = part.routes.filter(
        sequence_index__lt=route_step.sequence_index
    ).exclude(status__in=[PartRoute.Status.COMPLETED, PartRoute.Status.NOT_REQUIRED]).exists()
    if unfinished_previous:
        return _reject(client_scan_id, qr_token, "previous_not_completed", source, employee, device_id, machine, operation, part, order, batch)

    if scanned_at_client:
        now = timezone.now()
        if scanned_at_client > now + timedelta(hours=1) or scanned_at_client < now - timedelta(days=7):
            return _reject(client_scan_id, qr_token, "review_required", source, employee, device_id, machine, operation, part, order, batch)

    # All checks passed — accept the scan and advance the part along its route.
    route_step.status = PartRoute.Status.COMPLETED
    route_step.completed_at = timezone.now()
    route_step.completed_by = employee
    route_step.machine = machine
    route_step.save(update_fields=["status", "completed_at", "completed_by", "machine"])

    next_step = part.routes.filter(status=PartRoute.Status.PENDING).order_by("sequence_index").first()
    part.current_operation = next_step.operation if next_step else None
    part.status = Part.Status.COMPLETED if not next_step else Part.Status.IN_PROGRESS
    part.save(update_fields=["current_operation", "status"])
    order.recalculate_status()

    # If this scan finished the last detail the whole-order board is waiting
    # on for its current stage, advance the board the same way the manual
    # "Bosqichni yakunlash" action does — same underlying operation, so it
    # can't leave stage_progress in an inconsistent state.
    if operation.id == order.current_stage_id and order.stage_status == Order.StageStatus.IN_PROGRESS:
        stage_incomplete = PartRoute.objects.filter(
            part__order=order, operation=operation,
        ).exclude(status__in=[PartRoute.Status.COMPLETED, PartRoute.Status.NOT_REQUIRED]).exists()
        if not stage_incomplete:
            try:
                complete_current_stage(order.id, completed_by=employee)
            except ProductionWorkflowError:
                pass  # leave it for the manual admin action if something's off

    scan = ScanEvent.objects.create(
        client_scan_id=client_scan_id,
        qr_token=qr_token,
        part=part,
        order=order,
        operation=operation,
        machine=machine,
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


@transaction.atomic
def undo_scan(scan_event_id, *, actor):
    """Reverses the effect of one accepted scan — the symmetric inverse of
    the "accept" branch of process_scan(). Only the part's own most recent
    accepted scan at that operation may be undone (so undo always walks the
    route back one step at a time, never out of order), and only while the
    order-level board hasn't already completed that stage (OrderStageProgress),
    since that coarser, whole-order tracking has no per-route undo of its own."""

    scan = ScanEvent.objects.select_related("part", "order", "operation").filter(pk=scan_event_id).first()
    if not scan:
        raise UndoScanError("Skan topilmadi")
    if scan.status != ScanEvent.Status.ACCEPTED:
        raise UndoScanError("Faqat qabul qilingan skanni bekor qilish mumkin")
    if not scan.part or not scan.operation:
        raise UndoScanError("Bu skanni bekor qilib bo'lmaydi")

    part = scan.part
    operation = scan.operation
    order = scan.order or part.order

    latest = ScanEvent.objects.filter(
        part=part, operation=operation, status=ScanEvent.Status.ACCEPTED,
    ).order_by("-received_at_server", "-id").first()
    if not latest or latest.id != scan.id:
        raise UndoScanError("Faqat shu detalning ushbu bosqichdagi oxirgi skanini bekor qilish mumkin")

    stage_progress = OrderStageProgress.objects.filter(order=order, stage=operation).first()
    if stage_progress and stage_progress.status == OrderStageProgress.Status.COMPLETED:
        raise UndoScanError("Bu bosqich buyurtma darajasida allaqachon yakunlangan, uni bekor qilib bo'lmaydi")

    route_step = part.routes.filter(operation=operation).first()
    if not route_step or route_step.status != PartRoute.Status.COMPLETED:
        raise UndoScanError("Bu bosqich holati mos kelmadi")

    route_step.status = PartRoute.Status.PENDING
    route_step.completed_at = None
    route_step.completed_by = None
    route_step.machine = None
    route_step.save(update_fields=["status", "completed_at", "completed_by", "machine"])

    has_other_completed = part.routes.exclude(pk=route_step.pk).filter(status=PartRoute.Status.COMPLETED).exists()
    part.current_operation = operation
    part.status = Part.Status.IN_PROGRESS if has_other_completed else Part.Status.PENDING
    part.save(update_fields=["current_operation", "status"])
    order.recalculate_status()

    scan.status = ScanEvent.Status.UNDONE
    scan.save(update_fields=["status"])

    employee_label = actor.get_full_name() if hasattr(actor, "get_full_name") else str(actor)
    log_action(actor, "scan.undo", "ScanEvent", scan.id, {"part_id": part.id, "operation": operation.code})
    push_live_log(
        "scan",
        f"Skan bekor qilindi: Detal {part.code} | {operation.name} | {employee_label or actor}",
        {"part_id": part.id, "operation": operation.code},
    )
    return scan


def parse_client_datetime(value):
    if not value:
        return None
    return parse_datetime(value)
