"""Orders + workforce report (no financial data — see spec in Reports.jsx).

Order lifecycle has 7 raw statuses (draft/approved/in_production/partially_ready/
warehouse/completed/delivered/cancelled) but the report UI only exposes the four
buckets a manager actually cares about: new / in_progress / completed / cancelled.
STATUS_GROUP is that mapping, reused by every aggregate below.
"""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone

from accounts.models import Role, User
from orders.models import Order, OrderStageProgress

STATUS_GROUP = {
    Order.Status.DRAFT: "new",
    Order.Status.APPROVED: "in_progress",
    Order.Status.IN_PRODUCTION: "in_progress",
    Order.Status.PARTIALLY_READY: "in_progress",
    Order.Status.WAREHOUSE: "in_progress",
    Order.Status.COMPLETED: "completed",
    Order.Status.DELIVERED: "completed",
    Order.Status.CANCELLED: "cancelled",
}
GROUP_LABELS = {"new": "Yangi", "in_progress": "Jarayonda", "completed": "Tugallangan", "cancelled": "Bekor qilingan"}
GROUP_ORDER = ["new", "in_progress", "completed", "cancelled"]
WORKER_ROLES = [Role.OPERATOR, Role.WAREHOUSE]
FINISHED_STATUSES = [Order.Status.COMPLETED, Order.Status.DELIVERED]
OPEN_STATUSES_EXCLUDING_CANCELLED = [
    s for s in Order.Status.values if s not in (Order.Status.CANCELLED,) + tuple(FINISHED_STATUSES)
]


def _annotate_last_stage(queryset):
    """Attach who finished this order's last completed stage, and when.

    complete_current_stage() (orders/production_workflow.py) sets order.status
    to COMPLETED on the exact same OrderStageProgress row that becomes this
    order's most recent COMPLETED entry — so this subquery's completed_by/
    completed_at is precisely "who finished the order, and when", with no
    separate order-level timestamp needed.
    """
    last_progress = OrderStageProgress.objects.filter(
        order=OuterRef("pk"), status=OrderStageProgress.Status.COMPLETED
    ).order_by("-completed_at")
    return queryset.annotate(
        last_completed_at=Subquery(last_progress.values("completed_at")[:1]),
        last_completed_by_id=Subquery(last_progress.values("completed_by_id")[:1]),
    )


def _base_queryset(date_from, date_to, status=None, worker_id=None, department_id=None):
    qs = Order.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    if status:
        qs = qs.filter(status__in=[code for code, group in STATUS_GROUP.items() if group == status])
    if worker_id:
        qs = qs.filter(stage_progress__completed_by_id=worker_id).distinct()
    if department_id:
        qs = qs.filter(stage_progress__completed_by__department_id=department_id).distinct()
    return qs


def _overdue_queryset(worker_id=None, department_id=None):
    today = timezone.localdate()
    qs = Order.objects.filter(deadline__lt=today, status__in=OPEN_STATUSES_EXCLUDING_CANCELLED)
    if worker_id:
        qs = qs.filter(stage_progress__completed_by_id=worker_id).distinct()
    if department_id:
        qs = qs.filter(stage_progress__completed_by__department_id=department_id).distinct()
    return qs


def summary(date_from, date_to, status=None, worker_id=None, department_id=None):
    qs = _base_queryset(date_from, date_to, status, worker_id, department_id)
    group_counts = defaultdict(int)
    total = 0
    for row in qs.values("status").annotate(count=Count("id")):
        group_counts[STATUS_GROUP.get(row["status"], "new")] += row["count"]
        total += row["count"]

    # "Kechikkan" is a live state (deadline already passed), not scoped to the
    # selected date range — an order created last month is still late today.
    overdue = _overdue_queryset(worker_id, department_id).count()

    return {
        "total": total,
        "completed": group_counts["completed"],
        "in_progress": group_counts["in_progress"],
        "new": group_counts["new"],
        "cancelled": group_counts["cancelled"],
        "overdue": overdue,
    }


def status_distribution(date_from, date_to, worker_id=None, department_id=None):
    qs = _base_queryset(date_from, date_to, None, worker_id, department_id)
    group_counts = defaultdict(int)
    for row in qs.values("status").annotate(count=Count("id")):
        group_counts[STATUS_GROUP.get(row["status"], "new")] += row["count"]
    return [{"status": g, "label": GROUP_LABELS[g], "count": group_counts.get(g, 0)} for g in GROUP_ORDER]


def _bucket_key(day, granularity):
    if granularity == "week":
        return (day - timedelta(days=day.weekday())).isoformat()
    if granularity == "month":
        return day.strftime("%Y-%m")
    return day.isoformat()


def completion_series(date_from, date_to, granularity="day", worker_id=None, department_id=None):
    qs = _annotate_last_stage(Order.objects.filter(status__in=FINISHED_STATUSES)).filter(
        last_completed_at__date__gte=date_from, last_completed_at__date__lte=date_to,
    )
    if worker_id:
        qs = qs.filter(last_completed_by_id=worker_id)
    if department_id:
        qs = qs.filter(last_completed_by__department_id=department_id)

    buckets = defaultdict(int)
    for completed_at in qs.values_list("last_completed_at", flat=True):
        buckets[_bucket_key(timezone.localtime(completed_at).date(), granularity)] += 1
    return [{"period": key, "count": buckets[key]} for key in sorted(buckets)]


def worker_performance(date_from, date_to, department_id=None):
    workers = User.objects.filter(role__in=WORKER_ROLES, is_active_employee=True)
    if department_id:
        workers = workers.filter(department_id=department_id)
    workers = list(workers)

    orders = _annotate_last_stage(Order.objects.exclude(status=Order.Status.CANCELLED)).filter(
        last_completed_by_id__isnull=False,
    )

    completions_by_worker = defaultdict(list)
    in_progress_by_worker = defaultdict(int)
    for row in orders.values("last_completed_by_id", "last_completed_at", "status"):
        group = STATUS_GROUP.get(row["status"], "new")
        if group == "completed":
            completions_by_worker[row["last_completed_by_id"]].append(row["last_completed_at"])
        elif group == "in_progress":
            in_progress_by_worker[row["last_completed_by_id"]] += 1

    rows = []
    for worker in workers:
        completions = completions_by_worker.get(worker.id, [])
        # "Tugatgan buyurtmalar soni" respects the selected date range; "Oxirgi
        # tugatgan buyurtma" always shows the true most-recent completion so it
        # doesn't go blank just because the filter window doesn't cover it.
        windowed = [c for c in completions if date_from <= timezone.localtime(c).date() <= date_to]
        rows.append({
            "id": worker.id,
            "name": worker.get_full_name() or worker.username,
            "role": worker.get_role_display(),
            "completed_count": len(windowed),
            "in_progress_count": in_progress_by_worker.get(worker.id, 0),
            "last_completed_at": max(completions).isoformat() if completions else None,
        })
    rows.sort(key=lambda r: r["completed_count"], reverse=True)
    return rows


def worker_completed_orders(worker_id, date_from=None, date_to=None):
    qs = _annotate_last_stage(Order.objects.filter(status__in=FINISHED_STATUSES)).filter(
        last_completed_by_id=worker_id,
    )
    if date_from and date_to:
        qs = qs.filter(last_completed_at__date__gte=date_from, last_completed_at__date__lte=date_to)
    qs = qs.select_related("product_type").order_by("-last_completed_at")
    return [
        {
            "id": order.id,
            "order_no": order.order_no,
            "customer_name": order.customer_name or "-",
            "work_type": order.product_type.name if order.product_type_id else (order.product_name or "-"),
            "created_at": order.created_at.isoformat(),
            "completed_at": order.last_completed_at.isoformat() if order.last_completed_at else None,
            "status": order.status,
            "status_label": order.get_status_display(),
        }
        for order in qs
    ]


def overdue_orders(worker_id=None, department_id=None):
    today = timezone.localdate()
    qs = _overdue_queryset(worker_id, department_id).order_by("deadline")
    return [
        {
            "id": order.id,
            "order_no": order.order_no,
            "customer_name": order.customer_name or "-",
            "product_name": order.product_name or "-",
            "deadline": order.deadline.isoformat(),
            "days_overdue": (today - order.deadline).days,
            "status": order.status,
            "status_label": order.get_status_display(),
        }
        for order in qs
    ]


def overview(date_from, date_to, status=None, worker_id=None, department_id=None, granularity="day"):
    return {
        "summary": summary(date_from, date_to, status, worker_id, department_id),
        "status_distribution": status_distribution(date_from, date_to, worker_id, department_id),
        "completion_series": completion_series(date_from, date_to, granularity, worker_id, department_id),
        "worker_performance": worker_performance(date_from, date_to, department_id),
        "overdue_orders": overdue_orders(worker_id, department_id),
    }
