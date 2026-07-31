"""Typed in-memory representation of a parsed GibLab `.project` file.

Nothing in this module touches the database or Django models -- these are
plain dataclasses built by `parser.py` and consumed by `validator.py` /
`mapper.py`. All measurements are `Decimal`, never `float`.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class GibLabEdgeDTO:
    target_part_external_id: str
    side: str  # TOP | BOTTOM | LEFT | RIGHT
    operation_external_id: Optional[str]
    source_material_name: str
    length_mm: Decimal
    net_quantity_m: Decimal
    material_external_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GibLabCncProgramDTO:
    """Aggregated XNC facts for one operation element. The raw nested
    `program` XML is intentionally never retained here (perf + no logging
    of CNC program content)."""

    operation_external_id: str
    count: Decimal
    count_bore: Decimal
    count_cut: Decimal
    count_mill: Decimal
    side: Optional[str] = None
    turn: Optional[str] = None
    code: str = ""
    type_name: str = ""


@dataclass
class GibLabPartDTO:
    external_id: str
    code: str
    name: str
    quantity_per_product: int
    total_quantity: int
    length_mm: Decimal
    width_mm: Decimal
    cut_length_mm: Optional[Decimal] = None
    cut_width_mm: Optional[Decimal] = None
    detail_length_mm: Optional[Decimal] = None
    detail_width_mm: Optional[Decimal] = None
    join_length_mm: Optional[Decimal] = None
    join_width_mm: Optional[Decimal] = None
    txt: bool = False
    minus_count: int = 0
    material_external_id: Optional[str] = None
    primary_cut_operation_type: Optional[str] = None  # "CS" | "CL" -- which op resolved material_external_id
    edges: list = field(default_factory=list)  # GibLabEdgeDTO
    cnc_programs: list = field(default_factory=list)  # GibLabCncProgramDTO
    xml_path: str = ""

    @property
    def drilling_count(self):
        return sum((p.count_bore for p in self.cnc_programs), Decimal("0"))


@dataclass
class GibLabProductDTO:
    external_id: str
    name: str
    quantity: int
    parts: list = field(default_factory=list)  # GibLabPartDTO


@dataclass
class GibLabMaterialDTO:
    external_id: str
    source_type: str  # sheet | band
    code: str
    name: str
    category: Optional[str]  # resolved later once operations are known
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    source_quantity: Optional[Decimal] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GibLabOperationDTO:
    external_id: str
    type_id: str  # CS | EL | CL | XNC
    material_external_id: Optional[str] = None
    part_external_ids: list = field(default_factory=list)
    el_length: Optional[Decimal] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class MaterialConflictDTO:
    part_external_id: str
    material_external_ids: list


@dataclass
class GibLabProjectDTO:
    uuid: str
    version: str
    currency: str
    import_bmv: Optional[Decimal]
    products: list = field(default_factory=list)  # GibLabProductDTO
    materials: list = field(default_factory=list)  # GibLabMaterialDTO
    operations: list = field(default_factory=list)  # GibLabOperationDTO
    warnings: list = field(default_factory=list)  # dicts, see exceptions.error_dict
    conflicts: list = field(default_factory=list)  # MaterialConflictDTO
    unknown_attributes: dict = field(default_factory=dict)

    # Convenience registries built by the parser alongside the DTOs above --
    # kept scoped and separate per the "IDs are not globally unique" rule.
    materials_by_id: dict = field(default_factory=dict)  # id -> GibLabMaterialDTO
    operations_by_id: dict = field(default_factory=dict)  # id -> GibLabOperationDTO
    product_parts_by_id: dict = field(default_factory=dict)  # id -> (product_external_id, GibLabPartDTO)
    nested_sheet_parts_by_id: dict = field(default_factory=dict)  # id -> waste part raw attrs


@dataclass
class GibLabImportPlanDTO:
    is_valid: bool
    project: dict
    statistics: dict
    operation_mapping: list
    errors: list
    warnings: list
    order_payload: dict
    products_payload: list
    materials_payload: list
    bom_items_payload: list
    part_routes_payload: list
    conflicts: list = field(default_factory=list)
