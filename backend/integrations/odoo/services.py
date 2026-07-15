"""Import logic for the Odoo -> SPP one-way order sync.

sync_orders_from_odoo() is the only entry point: it reads confirmed
sale.order records via OdooClient (search_read only) and mirrors them into
SPP's own Order table. Nothing here ever calls back into Odoo.
"""

import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.audit import log_action, push_live_log
from orders.models import Order

from .client import OdooClient
from .models import SyncLog

logger = logging.getLogger(__name__)


def _parse_partner(partner_field):
    """Odoo many2one fields arrive as [id, "display name"] or False."""
    if isinstance(partner_field, (list, tuple)) and len(partner_field) == 2:
        return str(partner_field[0]), partner_field[1] or ""
    return "", ""


def _parse_odoo_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _import_one(odoo_order):
    """Returns "created", "updated" or None (no change). Never touches production fields."""
    external_id = str(odoo_order["id"])
    customer_id, customer_name = _parse_partner(odoo_order.get("partner_id"))
    deadline = _parse_odoo_date(odoo_order.get("commitment_date"))
    price = odoo_order.get("amount_total") or None

    with transaction.atomic():
        order, created = Order.objects.get_or_create(
            external_order_id=external_id,
            external_system="odoo",
            defaults={
                "customer_name": customer_name,
                "product_name": odoo_order.get("name") or "",
                "external_customer_id": customer_id,
                "approved_price": price,
                "approved_deadline": deadline,
                "customer_confirmed_at": timezone.now(),
                "odoo_sync_status": "synced",
            },
        )
        if created:
            log_action(None, "order.odoo_sync_create", "Order", order.id, {"order_no": order.order_no, "odoo_id": external_id})
            push_live_log("order", f"Odoo'dan yangi buyurtma import qilindi: #{order.order_no}", {"odoo_id": external_id})
            return "created"

        changed_fields = []
        if price != order.approved_price:
            order.approved_price = price
            changed_fields.append("approved_price")
        if deadline != order.approved_deadline:
            order.approved_deadline = deadline
            changed_fields.append("approved_deadline")

        if not changed_fields:
            return None

        order.customer_confirmed_at = timezone.now()
        order.odoo_sync_status = "synced"
        changed_fields += ["customer_confirmed_at", "odoo_sync_status"]
        order.save(update_fields=changed_fields)
        log_action(None, "order.odoo_sync_update", "Order", order.id, {"order_no": order.order_no, "changed": changed_fields})
        return "updated"


def sync_orders_from_odoo(since_datetime=None):
    """Poll Odoo once, import/update SPP orders, and record a SyncLog entry.

    A single failing order (e.g. malformed data) is logged and skipped —
    it does not abort the rest of the batch or the log entry.
    """
    imported_count = 0
    updated_count = 0
    error_messages = []

    try:
        odoo_orders = OdooClient().fetch_confirmed_orders(since_datetime=since_datetime)
    except Exception as exc:  # connection/auth/RPC failure — logged by OdooClient already
        odoo_orders = []
        error_messages.append(str(exc))

    for odoo_order in odoo_orders:
        try:
            outcome = _import_one(odoo_order)
        except Exception as exc:
            logger.exception("Failed to import Odoo order %s", odoo_order.get("id"))
            error_messages.append(f"order {odoo_order.get('id')}: {exc}")
            continue
        if outcome == "created":
            imported_count += 1
        elif outcome == "updated":
            updated_count += 1

    log_status = SyncLog.Status.FAILED if error_messages else SyncLog.Status.SUCCESS
    sync_log = SyncLog.objects.create(
        status=log_status,
        orders_imported_count=imported_count,
        error_message="; ".join(error_messages),
    )

    return {
        "status": log_status,
        "imported": imported_count,
        "updated": updated_count,
        "errors": error_messages,
        "sync_log_id": sync_log.id,
    }
