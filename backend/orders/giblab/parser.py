"""GibLab `.project` XML -> DTO parser.

Pure transformation: no database access, no version gate (that belongs to
`validator.py`, see `constants.SUPPORTED_VERSIONS`). Builds the scoped
registries described in the spec (`materials_by_id`, `operations_by_id`,
`product_parts_by_id`, `nested_sheet_parts_by_id`) because IDs are only
unique within their own element type, never globally.
"""

import re
from decimal import Decimal, InvalidOperation

from .constants import (
    EDGE_SIDE_ATTRS, EDGE_SIDE_USES_LENGTH, GOOD_TYPE_BAND, GOOD_TYPE_PRODUCT, GOOD_TYPE_SHEET,
    GOOD_TYPE_TOOL_CUTTING, GOOD_TYPE_TOOL_EDGELINE, MATERIAL_CATEGORY_EDGE_BAND, MATERIAL_CATEGORY_LINEAR,
    MATERIAL_CATEGORY_OTHER, MATERIAL_CATEGORY_PANEL, OPERATION_TYPE_CL, OPERATION_TYPE_CS, OPERATION_TYPE_EL,
    OPERATION_TYPE_XNC,
)
from .dto import (
    GibLabCncProgramDTO, GibLabEdgeDTO, GibLabMaterialDTO, GibLabOperationDTO, GibLabPartDTO, GibLabProductDTO,
    GibLabProjectDTO, MaterialConflictDTO,
)
from .exceptions import GibLabImportError, error_dict


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _children(elem, local_tag):
    for child in elem:
        if _local(child.tag) == local_tag:
            yield child


def _dec(value, default=None):
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return default


def _int(value, default=0):
    dec = _dec(value)
    return default if dec is None else int(dec)


def _bool(value):
    return str(value).strip().lower() == "true"


def _operation_ref(ref):
    """'@operation#3' -> '3'. Anything else (missing/malformed) -> None."""
    if not ref:
        return None
    ref = str(ref)
    if ref.startswith("@operation#"):
        return ref.split("#", 1)[1] or None
    return None


def _fallback_part_code(external_id, name):
    """Deterministic stand-in for a missing `code`, built from the fields
    that GibLab does reliably send (spec: code is human-readable-only, never
    used for identification -- qr_token owns that). Prefers name (kept short
    for label/log readability) with id appended for uniqueness; falls back to
    id alone if name is blank."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper()[:32] if name else ""
    if slug:
        return f"{slug}-{external_id}" if external_id else slug
    return str(external_id)


def _parse_product_part(part_el, xml_path_prefix, warnings):
    attrs = part_el.attrib
    external_id = attrs.get("id")
    original_name = attrs.get("name", "")
    original_code = attrs.get("code") or ""
    original_part_code = attrs.get("part.code") or ""

    code = original_code or original_part_code
    fallback_code_used = False
    if not code and (external_id or original_name):
        code = _fallback_part_code(external_id, original_name)
        fallback_code_used = True

    # Name fallback order (spec): original name > original `code` > original
    # `part.code` > deterministic "GibLab Part #ID". Sourced from the *raw*
    # code/part.code attributes only -- never from the auto-generated
    # fallback `code` above, so a code-less, name-less part (e.g. id=21)
    # still gets "GibLab Part #21" rather than echoing its own generated code.
    name = original_name
    name_fallback_source = None
    if not name:
        if original_code:
            name = original_code
            name_fallback_source = "code"
        elif original_part_code:
            name = original_part_code
            name_fallback_source = "part.code"
        elif external_id:
            name = f"GibLab Part #{external_id}"
            name_fallback_source = "external_id"

    count = _int(attrs.get("count"), 1)
    used_count = _int(attrs.get("usedCount"), count)
    length_mm = _dec(attrs.get("l"), Decimal("0"))
    width_mm = _dec(attrs.get("w"), Decimal("0"))

    part = GibLabPartDTO(
        external_id=external_id,
        code=code,
        name=name,
        quantity_per_product=count,
        total_quantity=used_count,
        length_mm=length_mm,
        width_mm=width_mm,
        cut_length_mm=_dec(attrs.get("cl")),
        cut_width_mm=_dec(attrs.get("cw")),
        detail_length_mm=_dec(attrs.get("dl")),
        detail_width_mm=_dec(attrs.get("dw")),
        join_length_mm=_dec(attrs.get("jl")),
        join_width_mm=_dec(attrs.get("jw")),
        txt=_bool(attrs.get("txt")),
        minus_count=_int(attrs.get("minusCount"), 0),
        xml_path=f"{xml_path_prefix}/part[@id='{external_id}']",
    )

    if fallback_code_used:
        warnings.append(
            error_dict(
                "PART_CODE_FALLBACK_GENERATED",
                "Part code mavjud emas, name/id asosida o'rinbosar kod avtomatik yaratildi",
                entity_type="part", external_id=external_id, xml_path=part.xml_path,
                details={"generated_code": code},
            )
        )

    if name_fallback_source:
        warnings.append(
            error_dict(
                "PART_NAME_FALLBACK_GENERATED",
                "Part nomi mavjud emas, o'rinbosar nom avtomatik yaratildi",
                entity_type="part", external_id=external_id, xml_path=part.xml_path,
                details={"generated_name": name, "source": name_fallback_source},
            )
        )

    for attr_name, (side, mat_attr) in EDGE_SIDE_ATTRS.items():
        ref = attrs.get(attr_name)
        if not ref:
            continue
        side_length_mm = length_mm if side in EDGE_SIDE_USES_LENGTH else width_mm
        side_length_mm = side_length_mm or Decimal("0")
        part.edges.append(
            GibLabEdgeDTO(
                target_part_external_id=external_id,
                side=side,
                operation_external_id=_operation_ref(ref),
                source_material_name=attrs.get(mat_attr, ""),
                length_mm=side_length_mm,
                net_quantity_m=side_length_mm / Decimal("1000"),
            )
        )
    return part


def _parse_good(elem, project: GibLabProjectDTO, warnings):
    type_id = elem.attrib.get("typeId", "")
    external_id = elem.attrib.get("id")

    if type_id == GOOD_TYPE_PRODUCT:
        product = GibLabProductDTO(
            external_id=external_id,
            name=elem.attrib.get("name", ""),
            quantity=_int(elem.attrib.get("count"), 1),
        )
        xml_path_prefix = f"/project/good[@typeId='product'][@id='{external_id}']"
        for part_el in _children(elem, "part"):
            part = _parse_product_part(part_el, xml_path_prefix, warnings)
            if part.external_id in project.product_parts_by_id:
                warnings.append(
                    error_dict(
                        "DUPLICATE_EXTERNAL_ID", "Product part id takrorlanmoqda",
                        entity_type="part", external_id=part.external_id,
                    )
                )
            project.product_parts_by_id[part.external_id] = (product.external_id, part)
            product.parts.append(part)
        project.products.append(product)

    elif type_id in (GOOD_TYPE_SHEET, GOOD_TYPE_BAND):
        material = GibLabMaterialDTO(
            external_id=external_id,
            source_type=type_id,
            code=elem.attrib.get("code", ""),
            name=elem.attrib.get("name", ""),
            category=None,
            length_mm=_dec(elem.attrib.get("l")),
            width_mm=_dec(elem.attrib.get("w")),
            thickness_mm=_dec(elem.attrib.get("t")),
            source_quantity=_dec(elem.attrib.get("count")),
        )
        project.materials.append(material)
        project.materials_by_id[external_id] = material
        for part_el in _children(elem, "part"):
            waste_id = part_el.attrib.get("id")
            if waste_id:
                project.nested_sheet_parts_by_id[waste_id] = dict(part_el.attrib)

    elif type_id in (GOOD_TYPE_TOOL_CUTTING, GOOD_TYPE_TOOL_EDGELINE):
        pass  # tool/edgeline metadata: not a Material/Product/Part, intentionally not modeled

    else:
        warnings.append(
            error_dict(
                "UNKNOWN_GOOD_TYPE" if type_id else "MISSING_REQUIRED_FIELD",
                f"Noma'lum good typeId: {type_id!r}", entity_type="good", external_id=external_id,
            )
        )


def _parse_operation(elem, project: GibLabProjectDTO):
    attrs = elem.attrib
    type_id = attrs.get("typeId", "")
    external_id = attrs.get("id")

    material_ref = None
    part_ids = []
    for child in elem:
        local = _local(child.tag)
        if local == "material":
            material_ref = child.attrib.get("id")
        elif local == "part":
            pid = child.attrib.get("id")
            if pid:
                part_ids.append(pid)

    op = GibLabOperationDTO(
        external_id=external_id, type_id=type_id, material_external_id=material_ref, part_external_ids=part_ids,
    )
    if type_id == OPERATION_TYPE_EL:
        op.el_length = _dec(attrs.get("elLength"))
    if type_id == OPERATION_TYPE_XNC:
        # Deliberately not retaining the raw `program` XML: only aggregate counts are needed,
        # and CNC program content must never be duplicated in memory/logs (see spec section 10).
        op.metadata["_cnc_program"] = GibLabCncProgramDTO(
            operation_external_id=external_id,
            count=_dec(attrs.get("count"), Decimal("0")),
            count_bore=_dec(attrs.get("countBore"), Decimal("0")),
            count_cut=_dec(attrs.get("countCut"), Decimal("0")),
            count_mill=_dec(attrs.get("countMill"), Decimal("0")),
            side=attrs.get("side"),
            turn=attrs.get("turn"),
            code=attrs.get("code", ""),
            type_name=attrs.get("typeName", ""),
        )
        op.metadata["_cnc_target_part_ids"] = part_ids

    project.operations.append(op)
    project.operations_by_id[external_id] = op


def _resolve_primary_materials(project: GibLabProjectDTO, warnings):
    """CS/CL operations link a sheet/linear material to the parts cut from
    it -- this is the only way to learn a product Part's primary material
    (spec section 5)."""
    for op in project.operations_by_id.values():
        if op.type_id not in (OPERATION_TYPE_CS, OPERATION_TYPE_CL) or not op.material_external_id:
            continue

        material = project.materials_by_id.get(op.material_external_id)
        if material is not None and material.category is None:
            material.category = MATERIAL_CATEGORY_PANEL if op.type_id == OPERATION_TYPE_CS else MATERIAL_CATEGORY_LINEAR

        for part_id in op.part_external_ids:
            entry = project.product_parts_by_id.get(part_id)
            if entry is None:
                if part_id not in project.nested_sheet_parts_by_id:
                    warnings.append(
                        error_dict(
                            "BROKEN_REFERENCE", f"{op.type_id} operatsiyada part topilmadi",
                            entity_type="operation", external_id=op.external_id,
                            details={"reference": f"part#{part_id}"},
                        )
                    )
                continue  # nested sheet/band waste part -- never a Part, silently skipped
            _, part_dto = entry
            if part_dto.material_external_id is None:
                part_dto.material_external_id = op.material_external_id
                part_dto.primary_cut_operation_type = op.type_id
            elif part_dto.material_external_id != op.material_external_id:
                project.conflicts.append(
                    MaterialConflictDTO(
                        part_external_id=part_dto.external_id,
                        material_external_ids=[part_dto.material_external_id, op.material_external_id],
                    )
                )


def _classify_edge_band_materials(project: GibLabProjectDTO):
    for op in project.operations_by_id.values():
        if op.type_id != OPERATION_TYPE_EL or not op.material_external_id:
            continue
        material = project.materials_by_id.get(op.material_external_id)
        if material is not None:
            material.category = MATERIAL_CATEGORY_EDGE_BAND


def _attach_xnc_programs(project: GibLabProjectDTO, warnings):
    for op in project.operations_by_id.values():
        if op.type_id != OPERATION_TYPE_XNC:
            continue
        program = op.metadata.pop("_cnc_program", None)
        target_ids = op.metadata.pop("_cnc_target_part_ids", [])
        if program is None:
            continue
        for part_id in target_ids:
            entry = project.product_parts_by_id.get(part_id)
            if entry is None:
                warnings.append(
                    error_dict(
                        "BROKEN_REFERENCE", "XNC operatsiyada part topilmadi",
                        entity_type="operation", external_id=op.external_id,
                        details={"reference": f"part#{part_id}"},
                    )
                )
                continue
            entry[1].cnc_programs.append(program)


def _finalize_material_classification(project: GibLabProjectDTO, warnings):
    for material in project.materials:
        if material.category is not None:
            continue
        if material.source_type == GOOD_TYPE_SHEET:
            material.category = MATERIAL_CATEGORY_PANEL
        else:
            material.category = MATERIAL_CATEGORY_OTHER
            warnings.append(
                error_dict(
                    "MATERIAL_CLASSIFICATION_UNKNOWN",
                    "Material hech qanday CS/CL/EL operatsiyada ishlatilmagan, turi aniqlanmadi",
                    entity_type="material", external_id=material.external_id,
                )
            )


def parse(root) -> GibLabProjectDTO:
    """`root` is a defusedxml-parsed Element (see `file_reader.parse_xml_safely`)."""
    if _local(root.tag) != "project":
        raise GibLabImportError("INVALID_XML", "Root element <project> emas")

    project = GibLabProjectDTO(
        uuid=root.attrib.get("project.uuid", ""),
        version=root.attrib.get("version", ""),
        currency=root.attrib.get("currency", ""),
        import_bmv=_dec(root.attrib.get("importBMV")),
    )

    known_root_attrs = {"project.uuid", "version", "currency", "importBMV"}
    extra_attrs = {k: v for k, v in root.attrib.items() if k not in known_root_attrs}
    if extra_attrs:
        project.unknown_attributes["project"] = extra_attrs

    warnings = project.warnings
    for elem in root:
        tag = _local(elem.tag)
        if tag == "good":
            _parse_good(elem, project, warnings)
        elif tag == "operation":
            _parse_operation(elem, project)
        else:
            warnings.append(error_dict("MISSING_REQUIRED_FIELD", f"Noma'lum root element: {tag!r}", entity_type=tag))

    _resolve_primary_materials(project, warnings)
    _classify_edge_band_materials(project)
    _attach_xnc_programs(project, warnings)
    _finalize_material_classification(project, warnings)

    return project
