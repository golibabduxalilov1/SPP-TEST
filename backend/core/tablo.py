from decimal import Decimal

from django.db.models import Case, IntegerField, Value, When

from manufacturing.models import Operation
from manufacturing.units import MEASURE_UNIT_LABELS
from manufacturing.units import stage_value as _stage_value_for_unit
from orders.models import Order, OrderStageProgress, PartRoute
from terminalapp.models import ScanEvent


TABLO_STATUSES = [
    Order.Status.APPROVED,
    Order.Status.IN_PRODUCTION,
    Order.Status.PARTIALLY_READY,
    Order.Status.WAREHOUSE,
    Order.Status.COMPLETED,
]

# Hard priority ranking for the tablo: every Urgent order outranks every
# High order, which outranks every Normal order. Newest-first is only ever
# a tiebreaker *within* one of these groups, never across them.
PRIORITY_RANK = Case(
    When(priority=Order.Priority.URGENT, then=Value(0)),
    When(priority=Order.Priority.HIGH, then=Value(1)),
    When(priority=Order.Priority.NORMAL, then=Value(2)),
    default=Value(3),
    output_field=IntegerField(),
)


def detail_contribution(detail, product_quantity=1):
    """A single OrderDetail's (quantity, area_m2, edge_meter) share — the one
    formula every quantity shown on the board (and, via dashboard_metrics,
    every production stat) is derived from. `product_quantity` is the
    order's `product_quantity` (how many identical products were ordered);
    it must be passed in by the caller rather than read off `detail.order`
    so callers that already hold the order avoid an extra query."""
    length = detail.length_mm or Decimal("0")
    width = detail.width_mm or Decimal("0")
    quantity = detail.quantity * product_quantity
    area = length * width * quantity / Decimal("1000000")
    edge = (length + width) * Decimal("2") * quantity / Decimal("1000")
    return quantity, area, edge


def part_contribution(part):
    """Same as detail_contribution, for imported/legacy orders that only
    have Parts (no linked OrderDetail) to read geometry from."""
    return part.quantity, (part.area_m2 or Decimal("0")), (part.edge_meter or Decimal("0"))


def _route_status_for(routes, operation_id):
    return next((route.status for route in routes if route.operation_id == operation_id), None)


def _sum_contributions(items, contribution_fn, operation=None):
    """Sum each item's contribution, optionally skipping ones already
    COMPLETED at `operation` (via its linked Part's routes) — used to turn
    the whole-order total into "what's still left for this stage"."""
    quantity = Decimal("0")
    area = Decimal("0")
    edge = Decimal("0")
    for item, routes in items:
        if operation is not None and routes is not None:
            if _route_status_for(routes, operation.id) == PartRoute.Status.COMPLETED:
                continue
        q, a, e = contribution_fn(item)
        quantity += q
        area += a
        edge += e
    return quantity, area, edge


def _detail_totals(order, operation=None):
    """Whole-order totals when `operation` is None; remaining (not-yet-
    completed-at-that-stage) totals when it's given."""
    details = list(order.details.all())
    if details:
        items = [(detail, detail.part.routes.all() if detail.part_id and detail.part else None) for detail in details]
        contribution_fn = lambda detail: detail_contribution(detail, order.product_quantity)  # noqa: E731
        return _sum_contributions(items, contribution_fn, operation)

    # Imported/legacy orders may only have Parts. Keep them visible while all
    # newly-created orders use OrderDetail as the board's source of truth.
    parts = list(order.parts.all())
    items = [(part, part.routes.all()) for part in parts]
    return _sum_contributions(items, part_contribution, operation)


# A Package isn't tied to individual OrderDetails/Parts the way area/edge/
# quantity are — packaging.services.sync_order_into_warehouse creates
# exactly one Package for the whole order once QADOQLASH finishes, so a
# package-measured stage's "total" is always this one unit, not a per-detail
# sum. Only a successful QR scan (via PartRoute/OrderStageProgress status,
# never raw Package existence) can flip it from 0/1 to 1/0.
PACKAGE_TOTAL = Decimal("1")


def _round_if_needed(value, measure_unit):
    if measure_unit in ("m2", "meter"):
        return round(float(value), 2)
    return value


def _measure(operation, quantity, area, edge):
    return _stage_value_for_unit(
        operation.measure_unit, quantity=quantity, area=area, edge=edge, package_count=PACKAGE_TOTAL,
    )


def _stage_progress(operation, mode, status, order_totals, remaining_totals):
    """"Bajarilgan/Qolgan" (completed/remaining) figures for one cell, driven
    purely by the stage's status: a not-yet-reached stage is 0/total, a
    finished one is always total/0 (never regresses to the running total
    even if per-route bookkeeping is coarser than per-detail, e.g. legacy
    Parts or the order-level Package), and an in-progress stage shrinks
    `remaining` as individual details/parts get scanned at it."""
    quantity, area, edge = order_totals
    unit = operation.measure_unit if mode == "hajm" else "piece"

    total = quantity if mode == "soni" else _measure(operation, quantity, area, edge)

    if status == "completed":
        remaining = Decimal("0")
    elif status == "pending":
        remaining = total
    else:  # in_progress
        r_quantity, r_area, r_edge = remaining_totals
        remaining = r_quantity if mode == "soni" else _measure(operation, r_quantity, r_area, r_edge)

    completed = total - remaining
    return {
        "completed": _round_if_needed(completed, unit),
        "remaining": _round_if_needed(remaining, unit),
        "total": _round_if_needed(total, unit),
    }


def _cells(order, operations):
    progress_by_stage = {item.stage_id: item.status for item in order.stage_progress.all()}
    workflow_started = order.stage_status != Order.StageStatus.NOT_STARTED or bool(progress_by_stage)
    totals = _detail_totals(order)
    cells = {}

    has_parts = order.parts.exists()
    routed_operation_ids = (
        set(PartRoute.objects.filter(part__order=order).values_list("operation_id", flat=True)) if has_parts else None
    )

    for operation in operations:
        progress_status = progress_by_stage.get(operation.id)
        if progress_status == OrderStageProgress.Status.COMPLETED:
            status = "completed"
        elif order.current_stage_id == operation.id and order.stage_status == Order.StageStatus.IN_PROGRESS:
            status = "in_progress"
        elif routed_operation_ids is not None and operation.id not in routed_operation_ids:
            # None of this order's parts pass through this stage at all —
            # it'll never become current_stage, so don't show it as a
            # perpetually-"kutilmoqda" step the board is waiting on.
            status = "not_required"
        elif workflow_started:
            status = "pending"
        else:
            status = "not_required"

        # Only needed for the in-progress branch of _stage_progress — shrinks
        # as individual details/parts get scanned at this stage, instead of
        # showing the static whole-order total the whole time.
        remaining_totals = _detail_totals(order, operation) if status == "in_progress" else None

        cells[operation.code] = {
            "status": status,
            "_totals": totals,
            "_remaining_totals": remaining_totals,
        }
    return cells


def _employee_label(user):
    if not user:
        return None
    return user.get_full_name() or user.username


def _scan_payload(scan):
    return {
        "id": scan.id,
        "part_code": scan.part.code if scan.part else None,
        "part_name": scan.part.name if scan.part else None,
        "order_no": scan.order.order_no if scan.order else None,
        "employee_name": _employee_label(scan.employee),
        "status": scan.status,
        "error_code": scan.error_code,
        "received_at": scan.received_at_server,
    }


def build_stage_detail(operation, history_limit=100):
    """Per-Part drilldown for one operation column of the tablo — unlike
    build_production_table, which aggregates order-level totals, this works
    directly off Part/PartRoute since that's the granularity the tablo's
    "click a column" page (backlog list, last scan, scan history) needs."""

    routes = (
        PartRoute.objects.filter(
            operation=operation,
            status__in=[PartRoute.Status.PENDING, PartRoute.Status.IN_PROGRESS],
            part__order__status__in=TABLO_STATUSES,
        )
        .select_related("part", "part__order")
        .order_by("part__order__priority", "part__order__deadline", "part__code")
    )
    parts = [
        {
            "id": route.part.id,
            "code": route.part.code,
            "name": route.part.name,
            "length_mm": route.part.length_mm,
            "width_mm": route.part.width_mm,
            "quantity": route.part.quantity,
            "order_no": route.part.order.order_no,
            "route_status": route.status,
        }
        for route in routes
    ]

    scans = ScanEvent.objects.filter(operation=operation).select_related("part", "order", "employee")
    last_scan = scans.filter(status=ScanEvent.Status.ACCEPTED).order_by("-received_at_server").first()
    history = scans.order_by("-received_at_server")[:history_limit]

    return {
        "operation": {
            "code": operation.code,
            "name": operation.name,
            "measure_unit": operation.measure_unit,
            "unit_label": MEASURE_UNIT_LABELS.get(operation.measure_unit, operation.measure_unit),
        },
        "parts": parts,
        "last_scan": _scan_payload(last_scan) if last_scan else None,
        "history": [_scan_payload(scan) for scan in history],
    }


def build_production_table(mode="hajm"):
    if mode not in {"hajm", "soni", "foiz"}:
        mode = "hajm"

    operations = list(Operation.objects.filter(is_active=True).order_by("order_index", "id"))
    orders = (
        Order.objects.filter(status__in=TABLO_STATUSES)
        .select_related("current_stage")
        .prefetch_related("details__part__routes", "parts__routes", "stage_progress")
        .annotate(_priority_rank=PRIORITY_RANK)
        .order_by("_priority_rank", "-created_at", "-id")
    )

    rows = []
    for index, order in enumerate(orders, start=1):
        cells = _cells(order, operations)
        for operation in operations:
            cell = cells[operation.code]
            totals = cell.pop("_totals")
            remaining_totals = cell.pop("_remaining_totals")

            if cell["status"] == "not_required":
                if mode == "foiz":
                    cell["value"] = None
                else:
                    cell["completed"] = cell["remaining"] = cell["total"] = None
                continue

            if mode == "foiz":
                cell["value"] = 100 if cell["status"] == "completed" else 0
            else:
                cell.update(_stage_progress(operation, mode, cell["status"], totals, remaining_totals))

        rows.append({
            "index": index,
            "order_id": order.id,
            "order_no": order.order_no,
            "customer_name": order.customer_name,
            "product_name": order.product_name,
            "deadline": order.deadline,
            "priority": order.priority,
            "order_status": order.status,
            "current_stage": order.current_stage.code if order.current_stage else None,
            "stage_status": order.stage_status,
            "cells": cells,
        })

    return {
        "mode": mode,
        "operations": [
            {
                "code": operation.code,
                "name": operation.name,
                "measure_unit": operation.measure_unit,
                "unit_label": MEASURE_UNIT_LABELS.get(operation.measure_unit, operation.measure_unit),
            }
            for operation in operations
        ],
        "rows": rows,
    }
