"""Order-creation adapter layer.

Order data can, in principle, arrive from more than one place: today only the
admin panel form (`ManualOrderSource`); in the future an Odoo webhook could
feed the same pipeline. Every source normalizes its payload into `OrderInput`
so `services.create_order` never needs to know where the data came from.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class OrderInput:
    customer_name: str = ""
    customer_phone: str = ""
    product_name: str = ""
    notes: str = ""
    deadline: Optional[date] = None
    priority: str = "normal"
    source: str = "manual"
    external_id: str = ""


class OrderSource:
    """Base adapter: translates a source-specific payload into a normalized OrderInput."""

    source_name = "manual"

    def parse(self, payload: dict) -> OrderInput:
        raise NotImplementedError


class ManualOrderSource(OrderSource):
    """Orders created through the admin panel form — the only implementation today."""

    source_name = "manual"

    def parse(self, payload: dict) -> OrderInput:
        return OrderInput(
            customer_name=payload.get("customer_name") or "",
            customer_phone=payload.get("customer_phone") or "",
            product_name=payload.get("product_name") or "",
            notes=payload.get("notes") or "",
            deadline=payload.get("deadline"),
            priority=payload.get("priority") or "normal",
            source=self.source_name,
            external_id="",
        )
