"""Structural and business validation for a parsed GibLab project.

Never stops at the first problem: both passes collect every error/warning
they find and return them as lists, so the preview can show the user the
full picture in one round trip.
"""

from decimal import Decimal

from . import operation_mapping
from .constants import EDGE_LENGTH_TOLERANCE_M, SUPPORTED_VERSIONS
from .dto import GibLabProjectDTO
from .exceptions import error_dict


def structural_validate(project: GibLabProjectDTO):
    errors = []
    warnings = list(project.warnings)  # carry forward parser-time warnings (unknown elements, id collisions, ...)

    if not project.uuid:
        errors.append(error_dict("MISSING_REQUIRED_FIELD", "project.uuid mavjud emas", entity_type="project"))
    if not project.version:
        errors.append(error_dict("MISSING_REQUIRED_FIELD", "version mavjud emas", entity_type="project"))
    elif project.version not in SUPPORTED_VERSIONS:
        errors.append(
            error_dict(
                "UNSUPPORTED_GIBLAB_VERSION", f"GibLab versiyasi qo'llab-quvvatlanmaydi: {project.version}",
                entity_type="project", details={"version": project.version, "supported": sorted(SUPPORTED_VERSIONS)},
            )
        )

    if not project.products:
        errors.append(error_dict("MISSING_REQUIRED_FIELD", "Faylda hech qanday product topilmadi", entity_type="project"))

    for product in project.products:
        path = f"/project/good[@typeId='product'][@id='{product.external_id}']"
        if not product.external_id:
            errors.append(error_dict("MISSING_REQUIRED_FIELD", "Product id mavjud emas", entity_type="product", xml_path=path))
        if not product.name:
            errors.append(error_dict("MISSING_REQUIRED_FIELD", "Product name mavjud emas", entity_type="product", external_id=product.external_id, xml_path=path))
        if product.quantity <= 0:
            errors.append(error_dict("INVALID_NUMBER", "Product count 0 dan katta bo'lishi kerak", entity_type="product", external_id=product.external_id, xml_path=path))

        if not product.parts:
            warnings.append(error_dict("MISSING_REQUIRED_FIELD", "Productda part topilmadi", entity_type="product", external_id=product.external_id, xml_path=path))

        for part in product.parts:
            part_path = part.xml_path or f"{path}/part[@id='{part.external_id}']"
            if not part.external_id:
                errors.append(error_dict("MISSING_REQUIRED_FIELD", "Part id mavjud emas", entity_type="part", xml_path=part_path))
            if not part.code:
                errors.append(error_dict("MISSING_REQUIRED_FIELD", "Part code mavjud emas", entity_type="part", external_id=part.external_id, xml_path=part_path))
            if not part.name:
                errors.append(error_dict("MISSING_REQUIRED_FIELD", "Part name mavjud emas", entity_type="part", external_id=part.external_id, xml_path=part_path))
            if part.quantity_per_product <= 0:
                errors.append(error_dict("INVALID_NUMBER", "Part count 0 dan katta bo'lishi kerak", entity_type="part", external_id=part.external_id, xml_path=part_path))
            if part.length_mm is None or part.length_mm <= 0 or part.width_mm is None or part.width_mm <= 0:
                errors.append(error_dict("INVALID_NUMBER", "Part l/w o'lchamlari noto'g'ri", entity_type="part", external_id=part.external_id, xml_path=part_path))

    return errors, warnings


def _resolve_edge_material(project: GibLabProjectDTO, edge, errors, warnings, part_external_id):
    """Resolve an edge's material via its `@operation#N` reference (per spec
    section 8) and cross-check the resolved name against the XML's own
    `elXMat` attribute. Sets `edge.material_external_id` in place."""
    if edge.operation_external_id is None:
        warnings.append(
            error_dict(
                "EDGE_OPERATION_NOT_FOUND", "Edge operatsiya reference mavjud emas, faqat nom bo'yicha aniqlanmoqda",
                entity_type="part", external_id=part_external_id, details={"side": edge.side},
            )
        )
        return

    operation = project.operations_by_id.get(edge.operation_external_id)
    if operation is None or operation.type_id != "EL":
        errors.append(
            error_dict(
                "EDGE_OPERATION_NOT_FOUND", "Edge operatsiya topilmadi", entity_type="part", external_id=part_external_id,
                details={"reference": f"@operation#{edge.operation_external_id}"},
            )
        )
        return

    material = project.materials_by_id.get(operation.material_external_id) if operation.material_external_id else None
    if material is None:
        errors.append(
            error_dict(
                "MATERIAL_NOT_FOUND", "Edge materiali topilmadi", entity_type="part", external_id=part_external_id,
                details={"operation": edge.operation_external_id},
            )
        )
        return

    edge.material_external_id = material.external_id
    if edge.source_material_name and edge.source_material_name != material.name:
        warnings.append(
            error_dict(
                "EDGE_MATERIAL_MISMATCH", "Edge material nomi mos kelmadi", entity_type="part", external_id=part_external_id,
                details={"expected": edge.source_material_name, "resolved": material.name},
            )
        )


def business_validate(project: GibLabProjectDTO, existing_operation_codes: set):
    errors = []
    warnings = []

    for product in project.products:
        for part in product.parts:
            if part.material_external_id is None:
                errors.append(
                    error_dict(
                        "MATERIAL_NOT_FOUND", "Part uchun asosiy material CS/CL orqali aniqlanmadi",
                        entity_type="part", external_id=part.external_id, xml_path=part.xml_path,
                    )
                )
            elif part.material_external_id not in project.materials_by_id:
                errors.append(
                    error_dict(
                        "MATERIAL_NOT_FOUND", "Part materialga bog'langan, ammo material topilmadi (broken reference)",
                        entity_type="part", external_id=part.external_id, xml_path=part.xml_path,
                        details={"material_external_id": part.material_external_id},
                    )
                )

            expected_used_count = part.quantity_per_product * product.quantity
            if part.total_quantity != expected_used_count:
                warnings.append(
                    error_dict(
                        "QUANTITY_MISMATCH",
                        "usedCount = count x product.count invariantiga mos kelmadi (minusCount yoki boshqa GibLab-ichi hisob sabab bo'lishi mumkin)",
                        entity_type="part", external_id=part.external_id, xml_path=part.xml_path,
                        details={"expected": expected_used_count, "actual": part.total_quantity},
                    )
                )

            if part.minus_count:
                warnings.append(
                    error_dict(
                        "QUANTITY_MISMATCH",
                        "minusCount != 0 -- semantikasi tasdiqlanmagan, quantity'dan avtomatik ayirilmadi",
                        entity_type="part", external_id=part.external_id, xml_path=part.xml_path,
                        details={"minus_count": part.minus_count},
                    )
                )

            for edge in part.edges:
                _resolve_edge_material(project, edge, errors, warnings, part.external_id)
                if edge.length_mm <= 0:
                    errors.append(
                        error_dict(
                            "INVALID_NUMBER", "Edge uzunligi musbat bo'lishi kerak",
                            entity_type="part", external_id=part.external_id, details={"side": edge.side},
                        )
                    )

    for conflict in project.conflicts:
        errors.append(
            error_dict(
                "MATERIAL_CONFLICT", "Part bir nechta asosiy materialga bog'langan",
                entity_type="part", external_id=conflict.part_external_id,
                details={"material_ids": conflict.material_external_ids},
            )
        )

    _validate_el_net_lengths(project, warnings)

    part_operation_codes = {}
    for product in project.products:
        for part in product.parts:
            codes = operation_mapping.resolve_part_operation_codes(part, project.materials_by_id, warnings)
            part_operation_codes[part.external_id] = codes
            for code in codes:
                if code not in existing_operation_codes:
                    errors.append(
                        error_dict(
                            "INACTIVE_OPERATION", f"MES operatsiya topilmadi/faol emas: {code}",
                            entity_type="part", external_id=part.external_id, details={"operation_code": code},
                        )
                    )

    return errors, warnings, part_operation_codes


def _validate_el_net_lengths(project: GibLabProjectDTO, warnings):
    """Cross-check the summed per-part edge net length (x usedCount) against
    each EL operation's own declared `elLength` total (spec section 8)."""
    totals_by_material = {}
    for product in project.products:
        for part in product.parts:
            for edge in part.edges:
                if edge.material_external_id is None:
                    continue
                totals_by_material.setdefault(edge.material_external_id, Decimal("0"))
                totals_by_material[edge.material_external_id] += edge.net_quantity_m * part.total_quantity

    tolerance = Decimal(EDGE_LENGTH_TOLERANCE_M)
    for operation in project.operations_by_id.values():
        if operation.type_id != "EL" or operation.el_length is None:
            continue
        computed = totals_by_material.get(operation.material_external_id, Decimal("0"))
        if abs(computed - operation.el_length) > tolerance:
            warnings.append(
                error_dict(
                    "QUANTITY_MISMATCH", "EL.elLength hisoblangan net total bilan mos kelmadi",
                    entity_type="operation", external_id=operation.external_id,
                    details={"declared_el_length": str(operation.el_length), "computed": str(computed)},
                )
            )
