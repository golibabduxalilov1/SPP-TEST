"""GibLab operation type -> MES `manufacturing.Operation.code` mapping.

Only what the business has actually confirmed is mapped here (spec section
9). `CL` and `XNC` mill/cut are deliberately left unmapped: guessing a
production route for an undecided business rule is worse than skipping
that route step and surfacing a warning so the mapping below can be
extended once the rule is confirmed.
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


def resolve_part_operation_codes(part_dto, materials_by_id, warnings):
    """Ordered, de-duplicated list of MES Operation codes this Part's route
    must include, derived only from what the XML actually recorded."""
    codes = []

    if part_dto.primary_cut_operation_type == "CS":
        codes.append(DEFAULT_OPERATION_MAPPING["CS"])
    elif part_dto.primary_cut_operation_type == "CL":
        warnings.append(
            error_dict(
                "UNKNOWN_OPERATION",
                "CL (chiziqli kesish) uchun MES operatsiya mappingi biznes tomonidan tasdiqlanmagan",
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
                    "XNC frezerlash (countMill) uchun MES operatsiya mappingi biznes tomonidan tasdiqlanmagan",
                    entity_type="part", external_id=part_dto.external_id,
                )
            )
        if program.count_cut and program.count_cut > 0:
            warnings.append(
                error_dict(
                    "UNKNOWN_OPERATION",
                    "XNC kesish (countCut) uchun MES operatsiya mappingi biznes tomonidan tasdiqlanmagan",
                    entity_type="part", external_id=part_dto.external_id,
                )
            )

    seen = set()
    ordered = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered
