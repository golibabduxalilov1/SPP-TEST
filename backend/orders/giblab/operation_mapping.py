"""GibLab operation type -> MES `manufacturing.Operation.code` mapping.

Business decision: every currently active MES operation belongs on a
GibLab-imported Part's route, mirroring `orders.services.
assign_active_stages_route()` in the manual "Yangi buyurtma" flow -- so
Tablo's per-operation columns are always fillable, regardless of what the
GibLab XML happened to record. What the XML *does* positively identify
(CS/EL/XNC_BORE, spec section 9) only decides where those specific
operations land at the front of the route; every other active operation is
appended after them in `order_index` order. `CL` and XNC mill/cut counts
still have no confirmed MES mapping of their own -- they no longer gate
anything, they just emit a diagnostic warning.
"""

from .exceptions import error_dict

DEFAULT_OPERATION_MAPPING = {
    "CS": "ARRA",
    "EL_REGULAR": "KROMKA",
    "EL_OVAL": "OVAL_KROMKA",
    "XNC_BORE": "PRISADKA",
}

# Case-insensitive substring match against a resolved edge-band Material's
# name -- the single place to extend if another oval-kromka naming
# convention shows up in a future GibLab version.
OVAL_KEYWORDS = ["oval"]


def is_oval_material_name(name: str) -> bool:
    lowered = (name or "").lower()
    return any(keyword in lowered for keyword in OVAL_KEYWORDS)


def resolve_part_operation_codes(part_dto, materials_by_id, warnings, active_operation_codes):
    """Ordered, de-duplicated list of MES Operation codes this Part's route
    must include: every currently active operation, with whatever the XML
    positively identified (CS/EL/XNC_BORE) pinned to the front in that
    order, followed by every other active operation in `order_index` order.

    `active_operation_codes` must already be ordered (`order_index`, `id`)
    -- the caller fetches it once per import, not per part, to avoid an
    N+1 query."""
    codes = []

    if part_dto.primary_cut_operation_type == "CS":
        codes.append(DEFAULT_OPERATION_MAPPING["CS"])
    elif part_dto.primary_cut_operation_type == "CL":
        warnings.append(
            error_dict(
                "UNKNOWN_OPERATION",
                "CL (chiziqli kesish) uchun MES operatsiya mappingi biznes tomonidan tasdiqlanmagan "
                "(operatsiya baribir umumiy faol marshrutga qo'shiladi)",
                entity_type="part", external_id=part_dto.external_id,
            )
        )

    seen_oval = False
    seen_regular = False
    for edge in part_dto.edges:
        material = materials_by_id.get(edge.material_external_id) if edge.material_external_id else None
        name = material.name if material else edge.source_material_name
        if is_oval_material_name(name):
            seen_oval = True
        else:
            seen_regular = True
    if seen_oval:
        codes.append(DEFAULT_OPERATION_MAPPING["EL_OVAL"])
    if seen_regular:
        codes.append(DEFAULT_OPERATION_MAPPING["EL_REGULAR"])

    if part_dto.drilling_count and part_dto.drilling_count > 0:
        codes.append(DEFAULT_OPERATION_MAPPING["XNC_BORE"])

    for program in part_dto.cnc_programs:
        if program.count_mill and program.count_mill > 0:
            warnings.append(
                error_dict(
                    "UNKNOWN_OPERATION",
                    "XNC frezerlash (countMill) uchun MES operatsiya mappingi biznes tomonidan tasdiqlanmagan "
                    "(operatsiya baribir umumiy faol marshrutga qo'shiladi)",
                    entity_type="part", external_id=part_dto.external_id,
                )
            )
        if program.count_cut and program.count_cut > 0:
            warnings.append(
                error_dict(
                    "UNKNOWN_OPERATION",
                    "XNC kesish (countCut) uchun MES operatsiya mappingi biznes tomonidan tasdiqlanmagan "
                    "(operatsiya baribir umumiy faol marshrutga qo'shiladi)",
                    entity_type="part", external_id=part_dto.external_id,
                )
            )

    seen = set()
    ordered = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)

    for code in active_operation_codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)

    return ordered
