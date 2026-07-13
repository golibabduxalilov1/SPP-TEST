from django.db.models import Count, Q

from manufacturing.models import Machine, Operation
from orders.models import Order
from packaging.models import Package
from terminalapp.models import ScanEvent


def production_report():
    ops = Operation.objects.annotate(
        completed_routes=Count("part_routes", filter=Q(part_routes__status="completed")),
        total_routes=Count("part_routes"),
    ).order_by("order_index")
    return [
        {
            "operation": op.name,
            "code": op.code,
            "completed": op.completed_routes,
            "total": op.total_routes,
            "percent": round((op.completed_routes / op.total_routes) * 100, 1) if op.total_routes else 0,
        }
        for op in ops
    ]


def orders_report():
    return list(Order.objects.values("status").annotate(count=Count("id")).order_by("status"))


def machines_report():
    return list(
        Machine.objects.annotate(scan_count=Count("scanevent"))
        .values("machine_id", "name", "status", "scan_count")
        .order_by("-scan_count")
    )


def scans_report():
    return list(
        ScanEvent.objects.values("status").annotate(count=Count("id")).order_by("status")
    )


def warehouse_report():
    return list(Package.objects.values("status").annotate(count=Count("id")).order_by("status"))
