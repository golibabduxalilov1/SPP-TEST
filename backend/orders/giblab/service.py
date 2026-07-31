"""Transactional GibLab `.project` import service.

`validate_project_file` is fully read-only (no database writes at all, not
even an import-history row). `import_project_file` persists everything in
one `transaction.atomic()` block -- any failure rolls back all domain
writes, unlike the existing CSV/XLSX importer's per-row error tolerance
(explicit spec requirement for this pipeline).
"""

import hashlib
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from catalog.models import Material
from core.audit import log_action
from manufacturing.models import Operation

from . import file_reader, mapper, parser, validator
from .constants import SOURCE_SYSTEM
from .exceptions import GibLabImportError, GibLabValidationFailed


def _check_duplicate(checksum, project_uuid, plan):
    """Mutates `plan.errors`/`plan.is_valid` in place if this file was
    already imported, or if the same project.uuid completed under a
    different checksum (spec section 16 -- no silent overwrite)."""
    from orders.models import GibLabImportBatch

    from .exceptions import error_dict

    existing = GibLabImportBatch.objects.filter(file_checksum=checksum).first()
    if existing and existing.status == GibLabImportBatch.Status.COMPLETED:
        plan.errors.append(
            error_dict(
                "DUPLICATE_IMPORT", "Ushbu fayl allaqachon import qilingan",
                entity_type="project", external_id=project_uuid, details={"import_id": existing.pk, "order_id": existing.order_id},
            )
        )
        plan.is_valid = False
        return

    if project_uuid:
        conflicting = (
            GibLabImportBatch.objects.filter(project_uuid=project_uuid, status=GibLabImportBatch.Status.COMPLETED)
            .exclude(file_checksum=checksum)
            .first()
        )
        if conflicting:
            plan.errors.append(
                error_dict(
                    "IMPORT_CONFLICT",
                    "Bu project.uuid boshqa fayl checksum bilan allaqachon import qilingan -- revizion siyosati tasdiqlanmagan",
                    entity_type="project", external_id=project_uuid, details={"import_id": conflicting.pk, "order_id": conflicting.order_id},
                )
            )
            plan.is_valid = False


def _analyze(uploaded_file):
    """Read + parse + validate + map. No database writes."""
    filename = getattr(uploaded_file, "name", "")
    data = file_reader.read_uploaded_bytes(uploaded_file)
    checksum = hashlib.sha256(data).hexdigest()

    xml_text = file_reader.detect_and_extract(data)
    root = file_reader.parse_xml_safely(xml_text)
    project = parser.parse(root)

    structural_errors, structural_warnings = validator.structural_validate(project)

    business_errors, business_warnings, part_operation_codes = [], [], {}
    if project.products and not any(e["code"] == "UNSUPPORTED_GIBLAB_VERSION" for e in structural_errors):
        existing_operation_codes = set(Operation.objects.filter(is_active=True).values_list("code", flat=True))
        business_errors, business_warnings, part_operation_codes = validator.business_validate(
            project, existing_operation_codes
        )

    errors = structural_errors + business_errors
    warnings = structural_warnings + business_warnings
    plan = mapper.build_import_plan(project, errors, warnings, part_operation_codes)
    return filename, checksum, project, plan


def _preview_dict(plan, checksum=None):
    return {
        "is_valid": plan.is_valid,
        "project": plan.project,
        "statistics": plan.statistics,
        "operation_mapping": plan.operation_mapping,
        "conflicts": plan.conflicts,
        "errors": plan.errors,
        "warnings": plan.warnings,
        "file_checksum": checksum,
    }


def validate_project_file(uploaded_file, user):
    _filename, checksum, project, plan = _analyze(uploaded_file)
    _check_duplicate(checksum, project.uuid, plan)
    return _preview_dict(plan, checksum)


def _create_domain_objects(plan, project, order_no_prefix=""):
    from orders.models import BOM, BOMItem, Order, Part, PartRoute, Product

    order = Order.objects.create(
        product_name=plan.order_payload["product_name"],
        product_quantity=plan.order_payload["product_quantity"],
        status=Order.Status.DRAFT,
        notes=f"GibLab import (project {project.uuid})",
    )

    materials_by_external_id = {}
    for m in plan.materials_payload:
        material, _created = Material.objects.get_or_create(
            source_system=SOURCE_SYSTEM,
            external_id=m["external_id"],
            category=m["category"],
            defaults={
                "code": m["code"],
                "name": m["name"],
                "length_mm": m["length_mm"],
                "width_mm": m["width_mm"],
                "thickness_mm": m["thickness_mm"],
                "metadata": {"source_type": m["source_type"]},
            },
        )
        materials_by_external_id[m["external_id"]] = material

    products_by_external_id = {}
    parts_by_external_id = {}
    boms_by_product_external_id = {}
    part_to_product_external_id = {}

    for p in plan.products_payload:
        product = Product.objects.create(order=order, name=p["name"])
        products_by_external_id[p["external_id"]] = product
        bom = BOM.objects.create(product=product, source_system=SOURCE_SYSTEM, source_project_uuid=project.uuid)
        boms_by_product_external_id[p["external_id"]] = bom

        for part_dict in p["parts"]:
            material = materials_by_external_id.get(part_dict["material_external_id"])
            part = Part.objects.create(
                order=order,
                product=product,
                code=part_dict["code"],
                name=part_dict["name"],
                material=part_dict["material_name"],
                material_ref=material,
                length_mm=part_dict["length_mm"],
                width_mm=part_dict["width_mm"],
                thickness_mm=part_dict["thickness_mm"],
                quantity=part_dict["quantity"],
                area_m2=part_dict["area_m2"],
                edge_meter=part_dict["edge_meter"],
                drilling_count=part_dict["drilling_count"],
            )
            parts_by_external_id[part_dict["external_id"]] = part
            part_to_product_external_id[part_dict["external_id"]] = p["external_id"]

    bom_item_objs = []
    for index, item in enumerate(plan.bom_items_payload):
        owner_external_id = item["part_external_id"] or item["target_part_external_id"]
        product_ext_id = part_to_product_external_id.get(owner_external_id)
        bom = boms_by_product_external_id.get(product_ext_id)
        if bom is None:
            continue
        bom_item_objs.append(
            BOMItem(
                bom=bom,
                item_type=item["item_type"],
                part=parts_by_external_id.get(item["part_external_id"]) if item["part_external_id"] else None,
                target_part=parts_by_external_id.get(item["target_part_external_id"]) if item["target_part_external_id"] else None,
                material=materials_by_external_id.get(item["material_external_id"]) if item["material_external_id"] else None,
                quantity=item["quantity"],
                unit=item["unit"],
                edge_side=item["edge_side"],
                source_external_id=item["source_external_id"],
                sequence_index=index,
            )
        )
    BOMItem.objects.bulk_create(bom_item_objs)

    needed_codes = {code for route in plan.part_routes_payload for code in route["operation_codes"]}
    operations_by_code = {op.code: op for op in Operation.objects.filter(code__in=needed_codes)}

    route_objs = []
    part_first_operation = {}
    for route in plan.part_routes_payload:
        part = parts_by_external_id.get(route["part_external_id"])
        if part is None:
            continue
        for sequence_index, code in enumerate(route["operation_codes"], start=1):
            operation = operations_by_code.get(code)
            if operation is None:
                continue
            if route["part_external_id"] not in part_first_operation:
                part_first_operation[route["part_external_id"]] = operation
            route_objs.append(
                PartRoute(part=part, operation=operation, sequence_index=sequence_index, status=PartRoute.Status.PENDING)
            )
    PartRoute.objects.bulk_create(route_objs)

    for external_id, operation in part_first_operation.items():
        part = parts_by_external_id.get(external_id)
        if part is not None:
            part.current_operation = operation
            part.save(update_fields=["current_operation"])

    created = {
        "orders": 1,
        "products": len(products_by_external_id),
        "parts": len(parts_by_external_id),
        "materials": len(materials_by_external_id),
        "boms": len(boms_by_product_external_id),
        "bom_items": len(bom_item_objs),
        "part_routes": len(route_objs),
    }
    return order, created


def import_project_file(uploaded_file, user):
    from orders.models import GibLabImportBatch

    filename, checksum, project, plan = _analyze(uploaded_file)
    _check_duplicate(checksum, project.uuid, plan)

    conflict_error = next((e for e in plan.errors if e["code"] in ("DUPLICATE_IMPORT", "IMPORT_CONFLICT")), None)
    if conflict_error is not None:
        raise GibLabImportError(
            conflict_error["code"], conflict_error["message"],
            entity_type=conflict_error["entity_type"], external_id=conflict_error["external_id"],
            details=conflict_error["details"],
        )

    if not plan.is_valid:
        raise GibLabValidationFailed(plan.errors, plan.warnings)

    batch = GibLabImportBatch.objects.create(
        original_filename=filename,
        file_checksum=checksum,
        project_uuid=project.uuid,
        file_version=project.version,
        status=GibLabImportBatch.Status.IMPORTING,
        statistics=plan.statistics,
        warnings=plan.warnings,
        imported_by=user if getattr(user, "is_authenticated", False) else None,
    )

    try:
        with transaction.atomic():
            order, created = _create_domain_objects(plan, project)
    except Exception as exc:  # noqa: BLE001 -- must not leak internals; batch record must still be marked FAILED
        batch.status = GibLabImportBatch.Status.FAILED
        batch.errors = [{"code": "DATABASE_ERROR", "message": "Import vaqtida xatolik yuz berdi, barcha o'zgarishlar bekor qilindi"}]
        batch.save(update_fields=["status", "errors"])
        log_action(user, "giblab.import_failed", details={"checksum": checksum, "project_uuid": project.uuid, "error": str(exc)})
        raise GibLabImportError("IMPORT_ROLLED_BACK", "Import vaqtida xatolik yuz berdi, barcha o'zgarishlar bekor qilindi") from exc

    batch.status = GibLabImportBatch.Status.COMPLETED
    batch.order = order
    batch.completed_at = timezone.now()
    batch.save(update_fields=["status", "order", "completed_at"])

    result = {
        "success": True,
        "import_id": str(batch.pk),
        "order_id": order.id,
        "project_uuid": project.uuid,
        "version": project.version,
        "created": created,
        "statistics": plan.statistics,
        "warnings": plan.warnings,
        "errors": [],
    }
    log_action(
        user, "giblab.import", entity_type="Order", entity_id=order.id,
        details={"checksum": checksum, "project_uuid": project.uuid, "created": created},
    )
    return result
