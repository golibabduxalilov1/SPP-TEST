from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from manufacturing.models import Machine
from orders.models import PartRoute
from terminalapp.models import ScanEvent

from .tablo import detail_contribution, part_contribution

UNIT_LABEL = {"m2": "kv.m", "meter": "metr", "piece": "dona", "package": "dona"}


def _parse_dt(value, default):
    if not value:
        return default
    dt = parse_datetime(value)
    if dt is None:
        return default
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def parse_window(request):
    now = timezone.now()
    date_from = _parse_dt(request.query_params.get("from"), now - timedelta(hours=8))
    date_to = _parse_dt(request.query_params.get("to"), now)
    try:
        interval_minutes = max(1, int(request.query_params.get("interval", 15)))
    except (TypeError, ValueError):
        interval_minutes = 15
    return date_from, date_to, interval_minutes


def _window_hours(date_from, date_to):
    hours = (date_to - date_from).total_seconds() / 3600
    return hours if hours > 0 else 1.0


def _completed_routes(date_from, date_to):
    """Every detail/part finished at any stage in the window — via an
    individual QR scan or a bulk "Bosqichni yakunlash" click, both of which
    mark PartRoute COMPLETED with a completed_at/completed_by. This is the
    same ground truth Tablo reads (core.tablo), so board and stats can never
    drift apart the way a separate ScanEvent-only read did."""
    return (
        PartRoute.objects.filter(
            status=PartRoute.Status.COMPLETED,
            completed_at__gte=date_from,
            completed_at__lte=date_to,
        )
        .select_related("operation", "part", "part__order_detail", "completed_by")
    )


def _route_value(route, unit):
    part = route.part
    detail = getattr(part, "order_detail", None)
    quantity, area, edge = detail_contribution(detail) if detail is not None else part_contribution(part)
    if unit == "m2":
        return area
    if unit == "meter":
        return edge
    return quantity


def overview(date_from, date_to):
    scans = ScanEvent.objects.filter(received_at_server__gte=date_from, received_at_server__lte=date_to)
    accepted_count = scans.filter(status=ScanEvent.Status.ACCEPTED).count()
    conflict_count = scans.filter(status=ScanEvent.Status.CONFLICT).count()
    total = accepted_count + conflict_count
    # Scan-quality ratio (accepted vs rejected QR scans) — distinct from the
    # capacity-based efficiency below, kept as-is since bulk stage
    # completions have no scan attempt to accept/reject in the first place.
    oee = round((accepted_count / total) * 100, 1) if total else 100.0

    routes = list(_completed_routes(date_from, date_to))
    m2_total = sum((_route_value(r, "m2") for r in routes if r.operation.measure_unit == "m2"), Decimal("0"))
    meter_total = sum((_route_value(r, "meter") for r in routes if r.operation.measure_unit == "meter"), Decimal("0"))
    piece_total = sum(
        (_route_value(r, "piece") for r in routes if r.operation.measure_unit in ("piece", "package")), Decimal("0")
    )

    return {
        "oee": oee,
        "output": {"m2": float(m2_total), "meter": float(meter_total), "piece": float(piece_total)},
        "active_machines": Machine.objects.filter(status="active").count(),
        "total_machines": Machine.objects.count(),
    }


def machines_summary(date_from, date_to):
    window_hours = _window_hours(date_from, date_to)
    machines = Machine.objects.select_related("operation", "tsex").filter(status="active").order_by("machine_id")

    machines_by_operation = defaultdict(list)
    for m in machines:
        machines_by_operation[m.operation_id].append(m)

    routes_by_machine = defaultdict(list)
    unassigned_routes_by_operation = defaultdict(list)
    for route in _completed_routes(date_from, date_to):
        if route.machine_id:
            routes_by_machine[route.machine_id].append(route)
        else:
            unassigned_routes_by_operation[route.operation_id].append(route)

    results = []
    for machine in machines:
        unit = machine.operation.measure_unit
        routes = list(routes_by_machine.get(machine.id, []))
        # A completion with no machine recorded (e.g. a bulk "Bosqichni
        # yakunlash" click, which isn't tied to any physical equipment) can
        # only be credited to a specific machine when its stage has exactly
        # one active machine — otherwise there's no way to know which one
        # actually did the work, so it's left off every machine card (it
        # still counts in the window-wide overview totals).
        if len(machines_by_operation[machine.operation_id]) == 1:
            routes += unassigned_routes_by_operation.get(machine.operation_id, [])
        volume = sum((_route_value(r, unit) for r in routes), Decimal("0"))
        efficiency = None
        if machine.capacity_per_hour:
            capacity_total = machine.capacity_per_hour * Decimal(str(window_hours))
            if capacity_total:
                efficiency = round(float(volume) / float(capacity_total) * 100, 1)

        results.append(
            {
                "id": machine.id,
                "machine_id": machine.machine_id,
                "name": machine.name,
                "operation_code": machine.operation.code,
                "operation_name": machine.operation.name,
                "status": machine.status,
                "unit": unit,
                "unit_label": UNIT_LABEL.get(unit, unit),
                "capacity_per_hour": float(machine.capacity_per_hour) if machine.capacity_per_hour is not None else None,
                "period_volume": float(volume),
                "period_efficiency": efficiency,
            }
        )
    return results


def machine_series(machine, date_from, date_to, interval_minutes):
    unit = machine.operation.measure_unit
    interval = timedelta(minutes=interval_minutes)

    buckets = []
    cursor = date_from
    while cursor < date_to:
        buckets.append(cursor)
        cursor += interval
    if not buckets:
        buckets = [date_from]

    bucket_values = [Decimal("0") for _ in buckets]
    routes_qs = _completed_routes(date_from, date_to).filter(operation=machine.operation)
    sibling_count = Machine.objects.filter(operation=machine.operation, status="active").count()
    # Same fallback rule as machines_summary: only fold in machine-less
    # completions when this machine is the sole one for its stage.
    routes = routes_qs if sibling_count == 1 else routes_qs.filter(machine=machine)

    interval_seconds = interval_minutes * 60
    for route in routes:
        value = _route_value(route, unit)
        idx = int((route.completed_at - date_from).total_seconds() // interval_seconds)
        idx = min(max(idx, 0), len(buckets) - 1)
        bucket_values[idx] += value

    period_volume = sum(bucket_values, Decimal("0"))
    max_value = max(bucket_values) if bucket_values else Decimal("0")
    window_hours = _window_hours(date_from, date_to)
    efficiency = None
    if machine.capacity_per_hour:
        capacity_total = machine.capacity_per_hour * Decimal(str(window_hours))
        if capacity_total:
            efficiency = round(float(period_volume) / float(capacity_total) * 100, 1)

    return {
        "machine_id": machine.id,
        "name": machine.name,
        "operation_code": machine.operation.code,
        "operation_name": machine.operation.name,
        "unit": unit,
        "unit_label": UNIT_LABEL.get(unit, unit),
        "capacity_per_hour": float(machine.capacity_per_hour) if machine.capacity_per_hour is not None else None,
        "interval_minutes": interval_minutes,
        "series": [{"t": b.isoformat(), "value": float(v)} for b, v in zip(buckets, bucket_values)],
        "max_value": float(max_value),
        "period_volume": float(period_volume),
        "period_efficiency": efficiency,
    }


def leaderboard(date_from, date_to, limit=10):
    window_hours = _window_hours(date_from, date_to)
    routes = (
        _completed_routes(date_from, date_to)
        .filter(completed_by__isnull=False)
        .order_by("id")
    )

    machine_by_operation = {
        machine.operation_id: machine
        for machine in Machine.objects.select_related("operation").filter(status="active")
    }

    agg = defaultdict(lambda: {
        "employee": None, "output": 0, "machine_ids": set(),
        "operation_volumes": defaultdict(Decimal), "operation_caps": {},
    })
    for route in routes.iterator():
        entry = agg[route.completed_by_id]
        entry["employee"] = route.completed_by
        entry["output"] += 1
        if route.machine_id:
            entry["machine_ids"].add(route.machine_id)
        machine = machine_by_operation.get(route.operation_id)
        if machine:
            value = _route_value(route, machine.operation.measure_unit)
            entry["operation_volumes"][route.operation_id] += value
            entry["operation_caps"][route.operation_id] = machine.capacity_per_hour

    rows = []
    for entry in agg.values():
        machine_effs = []
        for operation_id, volume in entry["operation_volumes"].items():
            capacity = entry["operation_caps"].get(operation_id)
            if capacity:
                capacity_total = float(capacity) * window_hours
                if capacity_total:
                    machine_effs.append(float(volume) / capacity_total * 100)
        efficiency = round(sum(machine_effs) / len(machine_effs), 1) if machine_effs else None
        employee = entry["employee"]
        rows.append(
            {
                "employee_id": employee.id,
                "name": employee.get_full_name() or employee.username,
                "role": employee.role,
                "output": entry["output"],
                # Real distinct machine count when scans carried one; falls
                # back to a per-stage estimate for legacy/bulk completions
                # that have no machine attached.
                "machines": len(entry["machine_ids"]) or len(entry["operation_volumes"]),
                "efficiency": efficiency,
            }
        )

    rows.sort(key=lambda r: r["output"], reverse=True)
    return rows[:limit]
