from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q

from manufacturing.models import Machine, Operation
from orders.models import Order, OrderStageProgress
from packaging.models import Package
from terminalapp.models import ScanEvent


def production_report():
    ops = Operation.objects.annotate(
        completed_routes=Count("part_routes", filter=Q(part_routes__status="completed")),
        in_progress_routes=Count("part_routes", filter=Q(part_routes__status="in_progress")),
        total_routes=Count("part_routes"),
    ).order_by("order_index")

    duration_expr = ExpressionWrapper(
        F("completed_at") - F("started_at"), output_field=DurationField()
    )
    avg_durations = {
        row["stage"]: row["avg_duration"]
        for row in (
            OrderStageProgress.objects.filter(
                status=OrderStageProgress.Status.COMPLETED, completed_at__isnull=False
            )
            .annotate(duration=duration_expr)
            .values("stage")
            .annotate(avg_duration=Avg("duration"))
        )
    }

    result = []
    for op in ops:
        avg_duration = avg_durations.get(op.id)
        result.append({
            "operation": op.name,
            "code": op.code,
            "completed": op.completed_routes,
            "in_progress": op.in_progress_routes,
            "total": op.total_routes,
            "percent": round((op.completed_routes / op.total_routes) * 100, 1) if op.total_routes else 0,
            "avg_duration_minutes": round(avg_duration.total_seconds() / 60, 1) if avg_duration else None,
        })
    return result


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
