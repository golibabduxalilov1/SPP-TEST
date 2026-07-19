from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from manufacturing.models import Operation

from .models import Order, OrderStageProgress, Part, PartRoute


class ProductionWorkflowError(Exception):
    """A user-facing order workflow validation error."""


def _complete_all_routes_for_stage(order, stage, completed_by):
    """Bulk-finish every detail/part still outstanding at `stage`.

    QR scanning marks one detail done at a time; this is the "finish
    everyone at once" fast path "Bosqichni yakunlash" is meant to be — any
    detail not yet individually scanned is marked done here too, same as if
    it had been. Each stage's completion is tracked on its own PartRoute row
    (unique per part+operation), so the next stage's routes are untouched
    and every detail starts that stage as "not yet done" again.
    """

    now = timezone.now()
    routes = list(
        PartRoute.objects.select_for_update()
        .filter(part__order=order, operation=stage)
        .exclude(status__in=[PartRoute.Status.COMPLETED, PartRoute.Status.NOT_REQUIRED])
        .select_related("part")
    )
    if not routes:
        return

    PartRoute.objects.filter(id__in=[route.id for route in routes]).update(
        status=PartRoute.Status.COMPLETED, completed_at=now, completed_by=completed_by,
    )

    for route in routes:
        part = route.part
        next_step = part.routes.filter(status=PartRoute.Status.PENDING).order_by("sequence_index").first()
        part.current_operation = next_step.operation if next_step else None
        part.status = Part.Status.COMPLETED if not next_step else Part.Status.IN_PROGRESS
        part.save(update_fields=["current_operation", "status"])

    order.recalculate_status()


def _stage_relevant_to_order(order, stage):
    """Whether `stage` is actually part of this order's production route.

    Orders created without detailed Part/PartRoute tracking (e.g. quick
    manual orders) have nothing to check against, so every active stage is
    treated as relevant for them — same as the original whole-order-only
    behaviour. Orders with routed parts only wait on stages at least one of
    their parts actually passes through, so e.g. a "faqat_kesish" order
    doesn't get stuck "in progress" forever on a stage none of its parts use.
    """
    if not order.parts.exists():
        return True
    return PartRoute.objects.filter(part__order=order, operation=stage).exists()


def _first_active_stage(order=None):
    candidates = Operation.objects.filter(is_active=True).order_by("order_index", "id")
    if order is None:
        return candidates.first()
    return next((candidate for candidate in candidates if _stage_relevant_to_order(order, candidate)), None)


def _next_active_stage(order, stage):
    candidates = (
        Operation.objects.filter(is_active=True)
        .filter(Q(order_index__gt=stage.order_index) | Q(order_index=stage.order_index, id__gt=stage.id))
        .order_by("order_index", "id")
    )
    return next((candidate for candidate in candidates if _stage_relevant_to_order(order, candidate)), None)


def _start_locked_order(order):
    if order.current_stage_id and order.stage_status == Order.StageStatus.IN_PROGRESS:
        return order

    first_stage = _first_active_stage(order)
    if not first_stage:
        raise ProductionWorkflowError("Faol ishlab chiqarish bosqichi topilmadi")

    progress, _ = OrderStageProgress.objects.get_or_create(
        order=order,
        stage=first_stage,
        defaults={"status": OrderStageProgress.Status.IN_PROGRESS},
    )
    if progress.status == OrderStageProgress.Status.COMPLETED:
        raise ProductionWorkflowError("Buyurtmaning birinchi bosqichi avval yakunlangan")

    order.current_stage = first_stage
    order.stage_status = Order.StageStatus.IN_PROGRESS
    order.save(update_fields=["current_stage", "stage_status", "updated_at"])
    return order


@transaction.atomic
def start_production_workflow(order_id):
    """Idempotently put an approved order into the first active stage."""

    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.APPROVED:
        raise ProductionWorkflowError("Faqat tasdiqlangan buyurtma ishlab chiqarishga tushadi")
    return _start_locked_order(order)


@transaction.atomic
def approve_order(order_id):
    """Approve a draft order and atomically start its production workflow."""

    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.DRAFT:
        raise ProductionWorkflowError("Faqat yangi (tasdiqlanmagan) buyurtmalarni tasdiqlash mumkin")

    order.status = Order.Status.APPROVED
    order.save(update_fields=["status", "updated_at"])
    return _start_locked_order(order)


@transaction.atomic
def complete_current_stage(order_id, completed_by=None):
    """Complete the current whole-order stage and advance to the next one.

    This service is intentionally transport-agnostic so the manual admin
    action and a future QR/terminal handler can call the same operation.
    """

    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED, Order.Status.DELIVERED):
        raise ProductionWorkflowError("Bu buyurtmaning ishlab chiqarish jarayoni faol emas")
    if not order.current_stage_id or order.stage_status != Order.StageStatus.IN_PROGRESS:
        raise ProductionWorkflowError("Buyurtmada yakunlanadigan joriy bosqich yo'q")

    progress = OrderStageProgress.objects.select_for_update().filter(
        order=order,
        stage=order.current_stage,
    ).first()
    if progress and progress.status != OrderStageProgress.Status.IN_PROGRESS:
        raise ProductionWorkflowError("Joriy bosqich tarixi topilmadi yoki u allaqachon yakunlangan")
    if not progress:
        # order.current_stage/stage_status say this stage is under way but no
        # history row exists for it (e.g. those fields were set directly
        # instead of through this module). Rather than getting the order
        # permanently stuck with no way to advance, backfill the missing
        # history row so completion can proceed normally.
        progress = OrderStageProgress.objects.create(
            order=order, stage=order.current_stage, status=OrderStageProgress.Status.IN_PROGRESS,
        )

    now = timezone.now()
    progress.status = OrderStageProgress.Status.COMPLETED
    progress.completed_at = now
    progress.completed_by = completed_by
    progress.save(update_fields=["status", "completed_at", "completed_by"])

    # Finish off any detail at this stage that wasn't individually QR-scanned
    # yet — clicking this button completes the whole stage in one go.
    _complete_all_routes_for_stage(order, order.current_stage, completed_by)

    next_stage = _next_active_stage(order, order.current_stage)
    if next_stage:
        next_progress, created = OrderStageProgress.objects.get_or_create(
            order=order,
            stage=next_stage,
            defaults={"status": OrderStageProgress.Status.IN_PROGRESS},
        )
        if not created and next_progress.status != OrderStageProgress.Status.IN_PROGRESS:
            raise ProductionWorkflowError("Keyingi bosqich avval yakunlangan")

        order.current_stage = next_stage
        order.stage_status = Order.StageStatus.IN_PROGRESS
        if order.status == Order.Status.APPROVED:
            order.status = Order.Status.IN_PRODUCTION
        order.save(update_fields=["current_stage", "stage_status", "status", "updated_at"])
    else:
        order.current_stage = None
        order.stage_status = Order.StageStatus.COMPLETED
        order.status = Order.Status.COMPLETED
        order.save(update_fields=["current_stage", "stage_status", "status", "updated_at"])

    return order


def advance_orders_past_deactivated_stage(stage):
    """Push orders parked on a stage that was just deactivated onto the next
    active one (or complete them, if it was the last one).

    The production board only shows active-stage columns, so an order left
    sitting on a stage that no longer appears there would otherwise become
    stuck with no visible way to move it forward.
    """

    stuck_order_ids = Order.objects.filter(
        current_stage=stage, stage_status=Order.StageStatus.IN_PROGRESS
    ).values_list("id", flat=True)
    for order_id in list(stuck_order_ids):
        try:
            complete_current_stage(order_id)
        except ProductionWorkflowError:
            pass
