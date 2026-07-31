"""GibLab DTO -> MES import plan.

Pure transformation (no database writes): turns a parsed+validated
`GibLabProjectDTO` into a `GibLabImportPlanDTO` carrying everything
`service.py` needs to persist, plus a JSON-serializable preview for the
`validate/` endpoint. EdgeBands are never a standalone payload entity here
-- they only ever appear as `BOMItem(item_type=EDGE_BAND)` rows.
"""

from decimal import Decimal

from .constants import BOM_ITEM_EDGE_BAND, BOM_ITEM_MATERIAL, BOM_ITEM_PART, MATERIAL_CATEGORY_EDGE_BAND, MATERIAL_CATEGORY_LINEAR, MATERIAL_CATEGORY_PANEL
from .dto import GibLabImportPlanDTO, GibLabProjectDTO


def _resolve_order_product_quantity(project: GibLabProjectDTO, warnings):
    quantities = {p.quantity for p in project.products}
    if len(quantities) > 1:
        from .exceptions import error_dict

        warnings.append(
            error_dict(
                "QUANTITY_MISMATCH",
                "Bir nechta product turli quantity'ga ega -- Order.product_quantity birinchi product'dan olindi",
                entity_type="project", details={"quantities": sorted(quantities)},
            )
        )
    return project.products[0].quantity if project.products else 1


def _build_statistics(project: GibLabProjectDTO):
    parts = [part for product in project.products for part in product.parts]
    return {
        "products": len(project.products),
        "product_quantity": sum(p.quantity for p in project.products) if len(project.products) == 1 else None,
        "part_definitions": len(parts),
        "total_physical_parts": sum(part.total_quantity for part in parts),
        "sheet_materials": sum(1 for m in project.materials if m.category == MATERIAL_CATEGORY_PANEL),
        "edge_band_materials": sum(1 for m in project.materials if m.category == MATERIAL_CATEGORY_EDGE_BAND),
        "linear_materials": sum(1 for m in project.materials if m.category == MATERIAL_CATEGORY_LINEAR),
        "bom_part_items": len(parts),
        "edge_band_items": sum(len(part.edges) for part in parts),
        "parts_with_edge_band": sum(1 for part in parts if part.edges),
        "parts_with_xnc": sum(1 for part in parts if part.cnc_programs),
        "outer_operations": len(project.operations),
        "cutting_operations": sum(1 for op in project.operations if op.type_id == "CS"),
        "edge_operations": sum(1 for op in project.operations if op.type_id == "EL"),
        "linear_cutting_operations": sum(1 for op in project.operations if op.type_id == "CL"),
        "xnc_operations": sum(1 for op in project.operations if op.type_id == "XNC"),
    }


def _build_operation_mapping_summary(part_operation_codes, parts):
    from . import operation_mapping as om

    unmapped_cl = sum(1 for part in parts if part.primary_cut_operation_type == "CL")
    unmapped_mill = sum(1 for part in parts for prog in part.cnc_programs if prog.count_mill and prog.count_mill > 0)
    unmapped_cut = sum(1 for part in parts for prog in part.cnc_programs if prog.count_cut and prog.count_cut > 0)

    mapped_counts = {}
    for codes in part_operation_codes.values():
        for code in codes:
            mapped_counts[code] = mapped_counts.get(code, 0) + 1

    summary = [
        {"giblab_type": giblab_type, "mes_code": mes_code, "part_count": mapped_counts.get(mes_code, 0)}
        for giblab_type, mes_code in om.DEFAULT_OPERATION_MAPPING.items()
        if mapped_counts.get(mes_code, 0) > 0
    ]
    if unmapped_cl:
        summary.append({"giblab_type": "CL", "mes_code": None, "part_count": unmapped_cl})
    if unmapped_mill:
        summary.append({"giblab_type": "XNC_MILL", "mes_code": None, "part_count": unmapped_mill})
    if unmapped_cut:
        summary.append({"giblab_type": "XNC_CUT", "mes_code": None, "part_count": unmapped_cut})
    return summary


def _material_dict(material):
    return {
        "external_id": material.external_id,
        "source_type": material.source_type,
        "code": material.code,
        "name": material.name,
        "category": material.category,
        "length_mm": material.length_mm,
        "width_mm": material.width_mm,
        "thickness_mm": material.thickness_mm,
        "source_quantity": material.source_quantity,
    }


def _part_dict(part, materials_by_id):
    material = materials_by_id.get(part.material_external_id) if part.material_external_id else None
    length = part.length_mm or Decimal("0")
    width = part.width_mm or Decimal("0")
    edge_total_mm = sum((edge.length_mm for edge in part.edges), Decimal("0"))

    # Per the BOMItem model: PART/MATERIAL rows hang off `part` (the part
    # itself); EDGE_BAND rows hang off `target_part` (the part the edge
    # belongs to) with `part` left null -- `part_external_id`/
    # `target_part_external_id` below map 1:1 onto those two FKs.
    bom_items = [
        {
            "item_type": BOM_ITEM_PART,
            "part_external_id": part.external_id,
            "target_part_external_id": None,
            "material_external_id": None,
            "quantity": Decimal(part.quantity_per_product),
            "unit": "dona",
            "edge_side": None,
            "source_external_id": part.external_id,
        },
    ]
    if part.material_external_id:
        bom_items.append(
            {
                "item_type": BOM_ITEM_MATERIAL,
                "part_external_id": part.external_id,
                "target_part_external_id": None,
                "material_external_id": part.material_external_id,
                "quantity": Decimal("1"),
                "unit": "",
                "edge_side": None,
                "source_external_id": part.external_id,
            }
        )
    for edge in part.edges:
        bom_items.append(
            {
                "item_type": BOM_ITEM_EDGE_BAND,
                "part_external_id": None,
                "target_part_external_id": part.external_id,
                "material_external_id": edge.material_external_id,
                "quantity": edge.net_quantity_m,
                "unit": "m",
                "edge_side": edge.side.lower(),
                "source_external_id": f"{part.external_id}:{edge.side}",
            }
        )

    return {
        "external_id": part.external_id,
        "code": part.code,
        "name": part.name,
        "quantity_per_product": part.quantity_per_product,
        "quantity": part.total_quantity,  # Part.quantity -- already usedCount, no further multiplication
        "length_mm": length,
        "width_mm": width,
        "thickness_mm": material.thickness_mm if material else None,
        "area_m2": (length * width * part.total_quantity / Decimal("1000000")) if length and width else Decimal("0"),
        "edge_meter": (edge_total_mm * part.total_quantity / Decimal("1000")) if edge_total_mm else Decimal("0"),
        "drilling_count": part.drilling_count,
        "material_external_id": part.material_external_id,
        "material_name": material.name if material else "",
    }, bom_items


def build_import_plan(project: GibLabProjectDTO, errors, warnings, part_operation_codes) -> GibLabImportPlanDTO:
    warnings = list(warnings)
    product_quantity = _resolve_order_product_quantity(project, warnings)

    products_payload = []
    bom_items_payload = []
    part_routes_payload = []
    all_parts = []

    for product in project.products:
        parts_payload = []
        for part in product.parts:
            all_parts.append(part)
            part_dict, bom_items = _part_dict(part, project.materials_by_id)
            parts_payload.append(part_dict)
            bom_items_payload.extend(bom_items)
            part_routes_payload.append(
                {"part_external_id": part.external_id, "operation_codes": part_operation_codes.get(part.external_id, [])}
            )
        products_payload.append({"external_id": product.external_id, "name": product.name, "quantity": product.quantity, "parts": parts_payload})

    materials_payload = [_material_dict(m) for m in project.materials]

    statistics = _build_statistics(project)
    operation_mapping_summary = _build_operation_mapping_summary(part_operation_codes, all_parts)

    order_payload = {
        "product_quantity": product_quantity,
        "product_name": project.products[0].name if project.products else "",
    }

    return GibLabImportPlanDTO(
        is_valid=not errors,
        project={"uuid": project.uuid, "version": project.version, "currency": project.currency},
        statistics=statistics,
        operation_mapping=operation_mapping_summary,
        errors=errors,
        warnings=warnings,
        order_payload=order_payload,
        products_payload=products_payload,
        materials_payload=materials_payload,
        bom_items_payload=bom_items_payload,
        part_routes_payload=part_routes_payload,
        conflicts=[{"part_external_id": c.part_external_id, "material_external_ids": c.material_external_ids} for c in project.conflicts],
    )
