"""GibLab `.project` import pipeline: validate-then-consume.

`validate_project_file` is fully read-only towards *domain* data (no Order/
Product/Part/BOM/Material writes) but persists a `GibLabImportBatch` import
session carrying the normalized, JSON-safe import plan -- so a later
`POST /orders/{..., "giblab_import_id": ...}` can build the Order and all
its production objects from that server-side plan alone, never re-trusting
whatever product/detail data the client sends alongside it.

`create_order_from_giblab_import` is the only consumer of an import
session and the only place that ever turns a plan into real domain rows.
Session bookkeeping (status transitions) is committed independently of the
domain-object transaction so a failed import still leaves an accurate,
queryable failure record instead of silently reverting to "as if nothing
happened" (see `_lock_session_for_consumption` / the try/except below).
"""

import hashlib
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone

from catalog.models import Material
from core.audit import log_action
from manufacturing.models import Operation

from . import file_reader, mapper, parser, validator
from .constants import IMPORT_SESSION_TTL_MINUTES, SOURCE_SYSTEM
from .exceptions import GibLabImportError


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
    if project.products and not any(e["code"] in ("UNSUPPORTED_GIBLAB_VERSION", "MULTIPLE_PRODUCTS_NOT_SUPPORTED") for e in structural_errors):
        # Fetched once per import (not per part) to avoid an N+1 query --
        # every Part's route needs the same full active-operation list.
        active_operation_codes = list(
            Operation.objects.filter(is_active=True).order_by("order_index", "id").values_list("code", flat=True)
        )
        existing_operation_codes = set(active_operation_codes)
        business_errors, business_warnings, part_operation_codes = validator.business_validate(
            project, existing_operation_codes, active_operation_codes
        )

    errors = structural_errors + business_errors
    warnings = structural_warnings + business_warnings
    plan = mapper.build_import_plan(project, errors, warnings, part_operation_codes)
    return filename, checksum, project, plan


def _build_form_preview(plan):
    """The frontend's auto-fill payload (spec: "Mahsulot nomi"/"Mahsulot
    soni"/detallar jadvali) -- a flattened view of the single supported
    product's parts, JSON-safe (Decimal -> str)."""
    if not plan.products_payload:
        return {"product_name": "", "product_quantity": 1, "details": []}
    product = plan.products_payload[0]
    details = [
        {
            "external_id": part["external_id"],
            "code": part["code"],
            "name": part["name"],
            "length_mm": _json_safe(part["length_mm"]),
            "width_mm": _json_safe(part["width_mm"]),
            "thickness_mm": _json_safe(part["thickness_mm"]),
            "quantity": part["quantity_per_product"],
            "total_quantity": part["quantity"],
            "material": part["material_name"],
        }
        for part in product["parts"]
    ]
    return {
        "product_name": plan.order_payload["product_name"],
        "product_quantity": plan.order_payload["product_quantity"],
        "details": details,
    }


def _preview_dict(plan, checksum=None):
    return {
        "is_valid": plan.is_valid,
        "project": plan.project,
        "form": _build_form_preview(plan),
        "statistics": plan.statistics,
        "operation_mapping": plan.operation_mapping,
        "conflicts": plan.conflicts,
        "errors": plan.errors,
        "warnings": plan.warnings,
        "file_checksum": checksum,
    }


# ---------------------------------------------------------------------------
# Plan <-> JSON session payload (Decimal is not JSON-native; every Decimal
# field is round-tripped through str explicitly rather than trusting bare
# str(Decimal)-in/Decimal(str)-out on unknown keys).
# ---------------------------------------------------------------------------

def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _plan_to_session_payload(plan, project_uuid):
    return _json_safe({
        "project_uuid": project_uuid,
        "order_payload": plan.order_payload,
        "products_payload": plan.products_payload,
        "materials_payload": plan.materials_payload,
        "bom_items_payload": plan.bom_items_payload,
        "part_routes_payload": plan.part_routes_payload,
    })


_PART_DECIMAL_FIELDS = ("length_mm", "width_mm", "thickness_mm", "area_m2", "edge_meter")
_MATERIAL_DECIMAL_FIELDS = ("length_mm", "width_mm", "thickness_mm", "source_quantity")


def _decimal_or_none(value):
    return None if value is None else Decimal(value)


def _decode_part(part):
    part = dict(part)
    for field in _PART_DECIMAL_FIELDS:
        part[field] = _decimal_or_none(part.get(field))
    return part


def _decode_material(material):
    material = dict(material)
    for field in _MATERIAL_DECIMAL_FIELDS:
        material[field] = _decimal_or_none(material.get(field))
    return material


def _decode_bom_item(item):
    item = dict(item)
    item["quantity"] = Decimal(item["quantity"])
    return item


def _session_payload_to_plan(payload):
    """Reverse of `_plan_to_session_payload` -- rebuilds a plan-shaped
    object (attribute access only, matching what `_populate_domain_objects`
    needs) with every stored Decimal string converted back to `Decimal`."""
    products_payload = [
        {**product, "parts": [_decode_part(part) for part in product["parts"]]}
        for product in payload["products_payload"]
    ]
    plan = SimpleNamespace(
        order_payload=payload["order_payload"],
        materials_payload=[_decode_material(m) for m in payload["materials_payload"]],
        products_payload=products_payload,
        bom_items_payload=[_decode_bom_item(i) for i in payload["bom_items_payload"]],
        part_routes_payload=payload["part_routes_payload"],
    )
    return plan, payload["project_uuid"]


def validate_project_file(uploaded_file, user):
    """Same `.project` file (or the same `project.uuid`) may be validated
    and consumed any number of times -- each becomes its own independent
    import session/Order (e.g. the same furniture design ordered by
    several different customers). No cross-session duplicate check here;
    the only per-session guard is single-use consumption (see
    `_lock_session_for_consumption`)."""
    from orders.models import GibLabImportBatch

    filename, checksum, project, plan = _analyze(uploaded_file)

    imported_by = user if getattr(user, "is_authenticated", False) else None
    now = timezone.now()
    fields = dict(
        original_filename=filename,
        project_uuid=project.uuid,
        file_version=project.version,
        statistics=plan.statistics,
        warnings=plan.warnings,
        errors=plan.errors,
        imported_by=imported_by,
        expires_at=now + timedelta(minutes=IMPORT_SESSION_TTL_MINUTES),
        consumed_at=None,
        order=None,
    )
    if plan.is_valid:
        fields["status"] = GibLabImportBatch.Status.VALIDATED
        fields["import_plan"] = _plan_to_session_payload(plan, project.uuid)
    else:
        fields["status"] = GibLabImportBatch.Status.FAILED
        fields["import_plan"] = {}

    # Re-validating the same file (new upload, or the user clicking
    # "Tekshirish" again) reuses/refreshes any not-yet-completed session for
    # this checksum+user instead of piling up abandoned rows.
    batch = (
        GibLabImportBatch.objects.filter(file_checksum=checksum, imported_by=imported_by)
        .exclude(status=GibLabImportBatch.Status.COMPLETED)
        .order_by("-created_at")
        .first()
    )
    if batch:
        for name, value in fields.items():
            setattr(batch, name, value)
        batch.save()
    else:
        batch = GibLabImportBatch.objects.create(file_checksum=checksum, **fields)

    result = _preview_dict(plan, checksum)
    result["import_id"] = str(batch.uuid)
    result["file"] = {"name": filename, "checksum": checksum, "version": project.version}
    return result


def _populate_domain_objects(order, plan, project_uuid):
    """Create Product/Material/Part/BOM/BOMItem/PartRoute rows for an
    already-created `order`, from a (decoded) import plan. Caller is
    responsible for the surrounding transaction."""
    from orders.models import BOM, BOMItem, Part, PartRoute, Product

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
        bom = BOM.objects.create(product=product, source_system=SOURCE_SYSTEM, source_project_uuid=project_uuid)
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

    return {
        "products": len(products_by_external_id),
        "parts": len(parts_by_external_id),
        "materials": len(materials_by_external_id),
        "boms": len(boms_by_product_external_id),
        "bom_items": len(bom_item_objs),
        "part_routes": len(route_objs),
    }


def _lock_session_for_consumption(import_id, user):
    """Own top-level transaction: locks the session row, checks
    ownership/expiry/consumed state and flips it to CONSUMING. Committing
    this independently of the domain-object transaction is what lets a
    concurrent double-submit see CONSUMING (not VALIDATED) and get
    rejected, and what lets a later domain-write failure still record
    FAILED instead of the whole session reverting as if nothing happened."""
    from orders.models import GibLabImportBatch

    # The status-transition save (EXPIRED or CONSUMING) must be committed
    # before any error is raised: raising *inside* the atomic block would
    # roll that save back too (Django rolls back the whole block on an
    # escaping exception), silently reverting the session to VALIDATED as
    # if the expiry/guard check never happened.
    error = None
    with transaction.atomic():
        batch = GibLabImportBatch.objects.select_for_update().filter(uuid=import_id).first()
        if batch is None:
            error = GibLabImportError("IMPORT_SESSION_NOT_FOUND", "Import sessiyasi topilmadi")
        elif batch.imported_by_id != getattr(user, "id", None):
            error = GibLabImportError("IMPORT_SESSION_FORBIDDEN", "Bu import sessiyasi boshqa foydalanuvchiga tegishli")
        elif batch.status == GibLabImportBatch.Status.COMPLETED or batch.consumed_at:
            error = GibLabImportError("IMPORT_SESSION_CONSUMED", "Import sessiyasi allaqachon ishlatilgan")
        elif batch.status == GibLabImportBatch.Status.CONSUMING:
            error = GibLabImportError("IMPORT_SESSION_CONSUMED", "Import sessiyasi hozir ishlatilmoqda")
        elif batch.status == GibLabImportBatch.Status.EXPIRED or (batch.expires_at and batch.expires_at < timezone.now()):
            if batch.status != GibLabImportBatch.Status.EXPIRED:
                batch.status = GibLabImportBatch.Status.EXPIRED
                batch.save(update_fields=["status"])
            error = GibLabImportError("IMPORT_SESSION_EXPIRED", "Import sessiyasining muddati tugagan, faylni qayta yuklang")
        elif batch.status != GibLabImportBatch.Status.VALIDATED:
            error = GibLabImportError("IMPORT_SESSION_INVALID", "Import sessiyasi ishlatib bo'lmaydi (tekshiruvdan o'tmagan)")
        else:
            batch.status = GibLabImportBatch.Status.CONSUMING
            batch.save(update_fields=["status"])

    if error is not None:
        raise error
    return batch


def _create_extra_details(order, extra_details):
    """Manual "Qo'shimcha detal" rows entered alongside a GibLab import --
    same OrderDetail+Part creation path as the plain manual flow
    (orders.services.create_part_for_order_detail), so they get their own
    trackable Part/route just like a hand-typed detail would. These are
    additive: the GibLab-derived parts stay the read-only source of truth
    for the imported product, these are simply extra rows on top."""
    from orders.models import OrderDetail
    from orders.services import create_part_for_order_detail

    for detail_data in extra_details:
        detail = OrderDetail.objects.create(order=order, **detail_data)
        create_part_for_order_detail(detail)
    return len(extra_details)


def create_order_from_giblab_import(import_id, user, order_fields, extra_details=None):
    """The only place a GibLab import session turns into real domain rows.
    `order_fields` carries the user-entered customer/deadline/priority/notes
    -- product name/quantity/parts/materials/BOM/routes always come from the
    session's stored server-side plan, never from the request. `extra_details`
    (optional) are additional manually-entered detail rows created alongside
    the imported ones (see _create_extra_details)."""
    from orders.models import GibLabImportBatch, Order

    batch = _lock_session_for_consumption(import_id, user)
    plan, project_uuid = _session_payload_to_plan(batch.import_plan)

    try:
        with transaction.atomic():
            order = Order.objects.create(
                customer_name=order_fields.get("customer_name") or "",
                customer_phone=order_fields.get("customer_phone") or "",
                deadline=order_fields.get("deadline"),
                priority=order_fields.get("priority") or Order.Priority.NORMAL,
                notes=order_fields.get("notes") or "",
                product_name=plan.order_payload["product_name"],
                product_quantity=plan.order_payload["product_quantity"],
                status=Order.Status.DRAFT,
                created_by=user if getattr(user, "is_authenticated", False) else None,
            )
            created = _populate_domain_objects(order, plan, project_uuid)
            created["manual_details"] = _create_extra_details(order, extra_details or [])
    except Exception as exc:  # noqa: BLE001 - must not leak internals; session record must still be marked FAILED
        batch.status = GibLabImportBatch.Status.FAILED
        batch.errors = [{"code": "DATABASE_ERROR", "message": "Import vaqtida xatolik yuz berdi, barcha o'zgarishlar bekor qilindi"}]
        batch.save(update_fields=["status", "errors"])
        log_action(
            user, "giblab.import_failed",
            details={"import_id": str(batch.uuid), "checksum": batch.file_checksum, "project_uuid": project_uuid, "error": str(exc)},
        )
        raise GibLabImportError("IMPORT_ROLLED_BACK", "Import vaqtida xatolik yuz berdi, barcha o'zgarishlar bekor qilindi") from exc

    batch.status = GibLabImportBatch.Status.COMPLETED
    batch.order = order
    batch.consumed_at = timezone.now()
    batch.completed_at = batch.consumed_at
    batch.save(update_fields=["status", "order", "consumed_at", "completed_at"])

    log_action(
        user, "order.create_from_giblab", entity_type="Order", entity_id=order.id,
        details={
            "import_id": str(batch.uuid), "checksum": batch.file_checksum, "project_uuid": project_uuid,
            "version": batch.file_version, "created": created, "statistics": batch.statistics,
            "warning_count": len(batch.warnings), "error_count": len(batch.errors),
        },
    )
    return order
