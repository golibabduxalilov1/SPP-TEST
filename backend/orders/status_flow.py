"""Linear order-status progression, used by the QR scan status-update flow.

There is no explicit "allowed next status" map elsewhere in the codebase —
Order.status is mostly auto-derived (see Order.recalculate_status and the
packaging/warehouse services). This mirrors the same sequence already shown
to admins via Order.Status.choices order, so QR-driven manual transitions
never invent a new workflow.
"""

from .models import Order

ORDER_STATUS_SEQUENCE = [
    Order.Status.DRAFT,
    Order.Status.APPROVED,
    Order.Status.IN_PRODUCTION,
    Order.Status.PARTIALLY_READY,
    Order.Status.WAREHOUSE,
    Order.Status.COMPLETED,
    Order.Status.DELIVERED,
]


def next_allowed_statuses(current_status):
    """Returns the Order.Status values that a QR scan may transition to from
    `current_status`: the next step in the sequence (if any) plus CANCELLED,
    which is always available as an escape hatch from a non-terminal order."""
    if current_status in (Order.Status.DELIVERED, Order.Status.CANCELLED):
        return []
    if current_status not in ORDER_STATUS_SEQUENCE:
        return [Order.Status.CANCELLED]

    idx = ORDER_STATUS_SEQUENCE.index(current_status)
    options = []
    if idx + 1 < len(ORDER_STATUS_SEQUENCE):
        options.append(ORDER_STATUS_SEQUENCE[idx + 1])
    options.append(Order.Status.CANCELLED)
    return options
