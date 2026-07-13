from decimal import Decimal

from manufacturing.models import Operation
from orders.models import Order, PartRoute

TABLO_ACTIVE_STATUSES = [
    Order.Status.APPROVED, Order.Status.IN_PRODUCTION, Order.Status.PARTIALLY_READY,
    Order.Status.READY_FOR_PACKAGING, Order.Status.PACKAGING,
]


def _cell(order, operation, mode):
    routes = PartRoute.objects.filter(part__order=order, operation=operation).select_related("part")
    total = routes.count()
    if total == 0:
        return {"status": "not_required", "value": None}

    completed = routes.filter(status=PartRoute.Status.COMPLETED).count()
    if completed == total:
        cell_status = "completed"
    elif completed > 0:
        cell_status = "in_progress"
    else:
        ready = routes.filter(part__current_operation=operation).exists()
        cell_status = "in_progress" if ready else "blocked"

    if mode == "foiz":
        value = round((completed / total) * 100, 2) if total else 0
    elif mode == "soni":
        value = sum(r.part.quantity for r in routes)
    else:  # hajm
        if operation.measure_unit == "m2":
            value = float(sum((r.part.area_m2 or Decimal("0")) for r in routes))
        elif operation.measure_unit == "meter":
            value = float(sum((r.part.edge_meter or Decimal("0")) for r in routes))
        else:
            value = sum(r.part.quantity for r in routes)
        value = round(value, 2)

    return {"status": cell_status, "value": value}


def build_production_table(mode="hajm"):
    operations = list(Operation.objects.order_by("order_index"))
    orders = (
        Order.objects.filter(status__in=TABLO_ACTIVE_STATUSES)
        .order_by("priority", "deadline")
        .prefetch_related("parts__routes")
    )
    rows = []
    for index, order in enumerate(orders, start=1):
        row = {
            "index": index,
            "order_id": order.id,
            "order_no": order.order_no,
            "customer_name": order.customer_name,
            "product_name": order.product_name,
            "deadline": order.deadline,
            "priority": order.priority,
            "cells": {op.code: _cell(order, op, mode) for op in operations},
        }
        rows.append(row)
    return {
        "mode": mode,
        "operations": [{"code": op.code, "name": op.name, "measure_unit": op.measure_unit} for op in operations],
        "rows": rows,
    }
