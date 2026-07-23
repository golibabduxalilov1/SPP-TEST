from django.utils import timezone

from core.audit import push_live_log
from orders.models import Order, Part, PartRoute
from orders.production_workflow import ProductionWorkflowError, complete_current_stage

from .models import Package, PackageItem

OMBOR_CODE = "OMBOR"


def packaging_scan(package: Package, qr_token: str, employee):
    part = Part.objects.filter(qr_token=qr_token).select_related("order").prefetch_related("routes__operation").first()
    if not part:
        return {"status": "error", "error_code": "invalid_qr", "message": "QR topilmadi"}

    if part.order_id != package.order_id:
        return {"status": "error", "error_code": "wrong_order", "message": "Xatolik: bu detal ushbu buyurtmaga tegishli emas"}

    if PackageItem.objects.filter(package=package, part=part).exists():
        return {"status": "error", "error_code": "duplicate", "message": "Bu detal qadoqlashda avval skanerlangan"}

    route_step = part.routes.filter(operation__code=OMBOR_CODE).first()
    if route_step:
        unfinished_previous = part.routes.filter(
            sequence_index__lt=route_step.sequence_index
        ).exclude(status__in=[PartRoute.Status.COMPLETED, PartRoute.Status.NOT_REQUIRED]).exists()
        if unfinished_previous:
            return {"status": "error", "error_code": "not_ready", "message": "Xatolik: detalning oldingi bosqichlari tugamagan"}

    PackageItem.objects.create(package=package, part=part, scanned_by=employee)

    if route_step and route_step.status != PartRoute.Status.COMPLETED:
        route_step.status = PartRoute.Status.COMPLETED
        route_step.completed_at = timezone.now()
        route_step.completed_by = employee
        route_step.save(update_fields=["status", "completed_at", "completed_by"])
        next_step = part.routes.filter(status=PartRoute.Status.PENDING).order_by("sequence_index").first()
        part.current_operation = next_step.operation if next_step else None
        part.status = Part.Status.COMPLETED if not next_step else Part.Status.IN_PROGRESS
        part.save(update_fields=["current_operation", "status"])
        order = part.order
        order.recalculate_status()

        # Same auto-advance as the terminal scan flow: if packaging this part
        # finished the board's current stage, move it to the next one.
        if route_step.operation_id == order.current_stage_id and order.stage_status == Order.StageStatus.IN_PROGRESS:
            stage_incomplete = PartRoute.objects.filter(
                part__order=order, operation=route_step.operation,
            ).exclude(status__in=[PartRoute.Status.COMPLETED, PartRoute.Status.NOT_REQUIRED]).exists()
            if not stage_incomplete:
                try:
                    complete_current_stage(order.id, completed_by=employee)
                except ProductionWorkflowError:
                    pass

    push_live_log("packaging", f"Qadoqlash: {part.code} -> {package.package_no}")
    return {"status": "ok", "part_id": part.id, "part_code": part.code}


def required_parts_qs(order):
    return Part.objects.filter(order=order, routes__operation__code=OMBOR_CODE).distinct()


def missing_parts_count(package: Package):
    required = set(required_parts_qs(package.order).values_list("id", flat=True))
    scanned = set(package.items.values_list("part_id", flat=True))
    return len(required - scanned)


def sync_order_into_warehouse(order, employee=None):
    """Make sure the order has exactly one `warehouse` Package once its OMBOR
    stage finishes, whichever path finished it (QR scan, "Bosqichni
    yakunlash", or any other caller of `complete_current_stage`).

    The whole-order "finish the stage" fast path never runs the packaging
    terminal flow, so it never creates a Package on its own — without this,
    an order can sail through OMBOR on the production board and simply never
    appear on the Tayyor ombor screen, which is the bug this closes.
    """
    package = (
        Package.objects.select_for_update()
        .filter(order=order, status__in=[Package.Status.OPEN, Package.Status.COMPLETED, Package.Status.WAREHOUSE])
        .order_by("created_at")
        .first()
    )
    if package is None:
        package = Package.objects.create(
            order=order, created_by=employee, status=Package.Status.WAREHOUSE, completed_at=timezone.now(),
        )
        PackageItem.objects.bulk_create(
            PackageItem(package=package, part=part, scanned_by=employee)
            for part in required_parts_qs(order)
        )
    elif package.status != Package.Status.WAREHOUSE:
        package.status = Package.Status.WAREHOUSE
        if not package.completed_at:
            package.completed_at = timezone.now()
        package.save(update_fields=["status", "completed_at"])

    if order.status != Order.Status.DELIVERED:
        order.status = Order.Status.WAREHOUSE
        order.save(update_fields=["status", "updated_at"])

    push_live_log("warehouse", f"Buyurtma tayyor omborga tushdi: #{order.order_no} -> {package.package_no}")
    return package
