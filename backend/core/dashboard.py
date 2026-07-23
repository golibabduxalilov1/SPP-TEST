from django.db.models import Count
from django.utils import timezone

from accounts.models import TerminalSession
from manufacturing.models import Machine
from orders.models import Order, Part
from terminalapp.models import ScanEvent


def build_summary():
    today = timezone.localdate()
    today_scans = ScanEvent.objects.filter(received_at_server__date=today)
    accepted_today = today_scans.filter(status=ScanEvent.Status.ACCEPTED).count()
    conflict_today = today_scans.filter(status=ScanEvent.Status.CONFLICT).count()
    total_today = accepted_today + conflict_today
    oee = round((accepted_today / total_today) * 100, 1) if total_today else 100.0

    active_orders = Order.objects.exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
    late_orders = active_orders.filter(deadline__lt=today).count()

    bottlenecks = (
        Part.objects.filter(order__in=active_orders, current_operation__isnull=False)
        .exclude(status="completed")
        .values("current_operation__code", "current_operation__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    return {
        "today_scans_accepted": accepted_today,
        "today_production_events": total_today,
        "active_parts": Part.objects.filter(order__in=active_orders).exclude(status="completed").count(),
        "active_machines": Machine.objects.filter(status="active").count(),
        "active_employees_on_shift": TerminalSession.objects.filter(is_active=True).values("employee").distinct().count(),
        "oee": oee,
        "late_orders": late_orders,
        "bottlenecks": [
            {"operation_code": b["current_operation__code"], "operation_name": b["current_operation__name"], "count": b["count"]}
            for b in bottlenecks if b["count"] >= 3
        ],
    }
