"""Single source of truth for production-stage measurement units.

Every place that turns an Operation's measure_unit into a displayed number
(Tablo, dashboard, reports) must go through `stage_value` below instead of
branching on a stage's code or name — that's what lets a user-created stage
work correctly with no code changes.
"""

from decimal import Decimal

MEASURE_UNIT_CHOICES = [
    ("m2", "m²"),
    ("meter", "metr"),
    ("piece", "dona"),
    ("package", "qadoq"),
]

MEASURE_UNIT_LABELS = dict(MEASURE_UNIT_CHOICES)

DEFAULT_MEASURE_UNIT = "piece"


def stage_value(measure_unit, *, quantity=None, area=None, edge=None, package_count=None):
    """The one rule every hajm figure is derived from:

    - m2      -> area (OrderDetail length/width-derived m2)
    - meter   -> edge (OrderDetail edge/qirra length in meters)
    - package -> package_count (existing packages linked to the order)
    - piece (and any other/unknown unit) -> quantity
    """
    if measure_unit == "m2":
        return area if area is not None else Decimal("0")
    if measure_unit == "meter":
        return edge if edge is not None else Decimal("0")
    if measure_unit == "package":
        return package_count if package_count is not None else Decimal("0")
    return quantity if quantity is not None else Decimal("0")
