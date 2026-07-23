from decimal import Decimal

from manufacturing.models import Operation
from orders.models import Order, OrderStageProgress, PartRoute


TABLO_STATUSES = [
    Order.Status.APPROVED,
    Order.Status.IN_PRODUCTION,
    Order.Status.PARTIALLY_READY,
    Order.Status.WAREHOUSE,
    Order.Status.COMPLETED,
]


def detail_contribution(detail):
    """A single OrderDetail's (quantity, area_m2, edge_meter) share — the one
    formula every quantity shown on the board (and, via dashboard_metrics,
    every production stat) is derived from."""
    length = detail.length_mm or Decimal("0")
    width = detail.width_mm or Decimal("0")
    quantity = detail.quantity
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
        return _sum_contributions(items, detail_contribution, operation)

    # Imported/legacy orders may only have Parts. Keep them visible while all
    # newly-created orders use OrderDetail as the board's source of truth.
    parts = list(order.parts.all())
    items = [(part, part.routes.all()) for part in parts]
    return _sum_contributions(items, part_contribution, operation)


def _stage_value(totals, operation, mode, status):
    quantity, area, _edge = totals
    if mode == "foiz":
        return 100 if status == "completed" else 0
    if mode == "soni":
        return quantity
    # mode == "hajm": every stage is measured in m2 of material area, since
    # that's what the board is meant to answer ("how much still needs
    # cutting/edging/assembling") — except PRISADKA (drilling), which is
    # inherently per-piece and has no m2 meaning. This is independent of
    # Operation.measure_unit, which stays authoritative for dashboard/machine
    # capacity math elsewhere.
    if operation.code == "PRISADKA":
        return quantity
    return round(float(area), 2)


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

        if status == "in_progress":
            # Shrink as individual details/parts get scanned at this stage,
            # instead of showing the static whole-order total the whole time.
            cell_totals = _detail_totals(order, operation)
        else:
            cell_totals = totals

        cells[operation.code] = {
            "status": status,
            "value": None if status == "not_required" else cell_totals,
        }
    return cells


def build_production_table(mode="hajm"):
    if mode not in {"hajm", "soni", "foiz"}:
        mode = "hajm"

    operations = list(Operation.objects.filter(is_active=True).order_by("order_index", "id"))
    orders = (
        Order.objects.filter(status__in=TABLO_STATUSES)
        .select_related("current_stage")
        .prefetch_related("details__part__routes", "parts__routes", "stage_progress")
        .order_by("priority", "deadline", "id")
    )

    rows = []
    for index, order in enumerate(orders, start=1):
        cells = _cells(order, operations)
        for operation in operations:
            cell = cells[operation.code]
            if cell["value"] is not None:
                cell["value"] = _stage_value(cell["value"], operation, mode, cell["status"])

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
            {"code": operation.code, "name": operation.name, "measure_unit": operation.measure_unit}
            for operation in operations
        ],
        "rows": rows,
    }
