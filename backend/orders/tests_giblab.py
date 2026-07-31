"""Tests for the GibLab `.project` import pipeline (backend/orders/giblab/).

Uses two kinds of fixtures:
- small, hand-built XML snippets defined inline for isolated parser/
  validator behaviour (duplicate ids, broken references, XXE, ...);
- `orders/giblab/testdata/sample_project.xml`, an anonymized derivative of
  the real customer sample (names/uuid replaced, unused program/data
  payloads stripped) used only for the regression-number assertions
  confirmed against that real file.
"""

import io
import os
import zipfile
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from accounts.models import Role, User
from core.models import AuditLog
from manufacturing.models import Operation

from .giblab import file_reader, mapper, parser, validator
from .giblab.exceptions import GibLabImportError
from .models import BOM, BOMItem, GibLabImportBatch, Order, Part, PartRoute, Product

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "giblab", "testdata", "sample_project.xml")


def _load_fixture_bytes():
    with open(FIXTURE_PATH, "rb") as f:
        return f.read()


def _uploaded(data: bytes, name="sample.project"):
    return SimpleUploadedFile(name, data, content_type="application/octet-stream")


def _seed_operations():
    for index, code in enumerate(["ARRA", "KROMKA", "OVAL_KROMKA", "PRISADKA"], start=1):
        Operation.objects.update_or_create(
            code=code, defaults={"name": code, "measure_unit": "m2", "order_index": index}
        )


MINIMAL_PRODUCT_XML = """<?xml version="1.0"?>
<project project.uuid="11111111-1111-1111-1111-111111111111" version="23051701" currency="UZS" importBMV="1">
  <good typeId="product" id="1" name="P" count="2">
    <part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>
  </good>
  <good typeId="sheet" id="2" code="S1" name="Sheet1" l="2500" w="1800" t="16" count="1"/>
  <operation id="3" typeId="CS">
    <material id="2"/>
    <part id="1"/>
  </operation>
</project>
"""


class GibLabFileReaderTests(APITestCase):
    def test_plain_xml_detected(self):
        text = file_reader.detect_and_extract(MINIMAL_PRODUCT_XML.encode("utf-8"))
        self.assertIn("<project", text)

    def test_empty_file_rejected(self):
        with self.assertRaises(GibLabImportError) as ctx:
            file_reader.read_uploaded_bytes(_uploaded(b""))
        self.assertEqual(ctx.exception.code, "INVALID_FILE")

    def test_unsupported_format_rejected(self):
        with self.assertRaises(GibLabImportError) as ctx:
            file_reader.detect_and_extract(b"not xml or zip at all, just garbage bytes")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_PROJECT_FORMAT")

    def test_bad_encoding_rejected(self):
        with self.assertRaises(GibLabImportError) as ctx:
            file_reader.detect_and_extract(b"<project>\xff\xfe broken</project>")
        self.assertEqual(ctx.exception.code, "INVALID_XML")

    def test_zip_wrapped_xml_extracted(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("inner.project", MINIMAL_PRODUCT_XML)
        text = file_reader.detect_and_extract(buf.getvalue())
        self.assertIn("<project", text)

    def test_corrupt_archive_rejected(self):
        with self.assertRaises(GibLabImportError) as ctx:
            file_reader.detect_and_extract(b"PK\x03\x04" + b"not a real zip body")
        self.assertEqual(ctx.exception.code, "INVALID_ARCHIVE")

    def test_zip_slip_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../../evil.project", MINIMAL_PRODUCT_XML)
        with self.assertRaises(GibLabImportError) as ctx:
            file_reader.detect_and_extract(buf.getvalue())
        self.assertEqual(ctx.exception.code, "INVALID_ARCHIVE")

    def test_xxe_blocked(self):
        malicious = (
            '<?xml version="1.0"?>'
            "<!DOCTYPE project [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>"
            '<project project.uuid="1" version="23051701" currency="UZS">&xxe;</project>'
        )
        root = None
        try:
            root = file_reader.parse_xml_safely(malicious)
        except GibLabImportError:
            pass  # defusedxml rejecting the DOCTYPE outright is an acceptable outcome too
        if root is not None:
            # If parsing succeeded, the entity must NOT have been expanded into file content.
            self.assertNotIn("root:", "".join(root.itertext()))


class GibLabParserTests(APITestCase):
    def test_minimal_valid_project_parses(self):
        root = file_reader.parse_xml_safely(MINIMAL_PRODUCT_XML)
        project = parser.parse(root)
        self.assertEqual(project.version, "23051701")
        self.assertEqual(len(project.products), 1)
        part = project.products[0].parts[0]
        self.assertEqual(part.total_quantity, 2)
        self.assertEqual(part.material_external_id, "2")

    def test_unknown_optional_attributes_tolerated(self):
        xml = MINIMAL_PRODUCT_XML.replace(
            'importBMV="1"', 'importBMV="1" futureAttr="whatever"'
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        self.assertIn("futureAttr", project.unknown_attributes.get("project", {}))

    def test_namespaced_xml_tolerated(self):
        xml = MINIMAL_PRODUCT_XML.replace(
            '<project ', '<project xmlns="urn:giblab" '
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        self.assertEqual(len(project.products), 1)

    def test_duplicate_product_part_id_warns(self):
        xml = MINIMAL_PRODUCT_XML.replace(
            '<part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>',
            '<part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>'
            '<part id="1" code="C2" name="Part2" count="1" usedCount="2" l="400" w="200"/>',
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        codes = [w["code"] for w in project.warnings]
        self.assertIn("DUPLICATE_EXTERNAL_ID", codes)

    def test_waste_part_excluded_from_registry(self):
        xml = MINIMAL_PRODUCT_XML.replace(
            '<good typeId="sheet" id="2" code="S1" name="Sheet1" l="2500" w="1800" t="16" count="1"/>',
            '<good typeId="sheet" id="2" code="S1" name="Sheet1" l="2500" w="1800" t="16" count="1">'
            '<part id="99" l="100" w="100" count="1" usedCount="0" waste="true" business="false" sheetId="2"/>'
            "</good>",
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        self.assertIn("99", project.nested_sheet_parts_by_id)
        self.assertNotIn("99", project.product_parts_by_id)

    def test_broken_material_reference_warns(self):
        xml = MINIMAL_PRODUCT_XML.replace('<material id="2"/>', '<material id="999"/>')
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        errors, _warnings = validator.structural_validate(project)
        berrors, _bwarnings, _codes = validator.business_validate(project, set())
        self.assertTrue(any(e["code"] == "MATERIAL_NOT_FOUND" for e in berrors))


class GibLabValidatorTests(APITestCase):
    def test_unsupported_version_rejected(self):
        xml = MINIMAL_PRODUCT_XML.replace('version="23051701"', 'version="99999999"')
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        errors, _warnings = validator.structural_validate(project)
        self.assertTrue(any(e["code"] == "UNSUPPORTED_GIBLAB_VERSION" for e in errors))

    def test_quantity_mismatch_is_a_warning_not_an_error(self):
        xml = MINIMAL_PRODUCT_XML.replace('usedCount="2"', 'usedCount="3"')
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        errors, _w = validator.structural_validate(project)
        berrors, bwarnings, _codes = validator.business_validate(project, {"ARRA"})
        self.assertFalse(any(e["code"] == "QUANTITY_MISMATCH" for e in errors + berrors))
        self.assertTrue(any(w["code"] == "QUANTITY_MISMATCH" for w in bwarnings))


class GibLabRegressionMappingTests(APITestCase):
    """Reproduces the confirmed statistics from the real sample file (see
    project plan) against its anonymized derivative."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.data = _load_fixture_bytes()

    def _build_plan(self, existing_codes):
        xml_text = file_reader.detect_and_extract(self.data)
        root = file_reader.parse_xml_safely(xml_text)
        project = parser.parse(root)
        errors, warnings = validator.structural_validate(project)
        berrors, bwarnings, codes = validator.business_validate(project, existing_codes)
        plan = mapper.build_import_plan(project, errors + berrors, warnings + bwarnings, codes)
        return project, plan

    def test_confirmed_sample_statistics(self):
        _project, plan = self._build_plan({"ARRA", "KROMKA", "OVAL_KROMKA", "PRISADKA"})
        stats = plan.statistics
        self.assertEqual(stats["products"], 1)
        self.assertEqual(stats["product_quantity"], 20)
        self.assertEqual(stats["part_definitions"], 30)
        self.assertEqual(stats["total_physical_parts"], 1040)
        self.assertEqual(stats["sheet_materials"], 3)
        self.assertEqual(stats["edge_band_materials"], 3)
        self.assertEqual(stats["linear_materials"], 1)
        self.assertEqual(stats["parts_with_edge_band"], 22)
        self.assertEqual(stats["edge_band_items"], 45)
        self.assertEqual(stats["outer_operations"], 36)
        self.assertEqual(stats["cutting_operations"], 3)
        self.assertEqual(stats["edge_operations"], 3)
        self.assertEqual(stats["linear_cutting_operations"], 1)
        self.assertEqual(stats["xnc_operations"], 29)
        self.assertEqual(stats["parts_with_xnc"], 24)

    def test_net_edge_lengths_match_confirmed_totals(self):
        project, _plan = self._build_plan({"ARRA", "KROMKA", "OVAL_KROMKA", "PRISADKA"})
        totals = {}
        for product in project.products:
            for part in product.parts:
                for edge in part.edges:
                    if edge.material_external_id is None:
                        continue
                    totals.setdefault(edge.material_external_id, Decimal("0"))
                    totals[edge.material_external_id] += edge.net_quantity_m * part.total_quantity
        rounded = sorted(round(v, 2) for v in totals.values())
        self.assertEqual(rounded, [Decimal("99.32"), Decimal("534.92"), Decimal("562.44")])

    def test_operation_mapping_leaves_cl_and_xnc_mill_cut_unmapped(self):
        _project, plan = self._build_plan({"ARRA", "KROMKA", "OVAL_KROMKA", "PRISADKA"})
        by_type = {row["giblab_type"]: row for row in plan.operation_mapping}
        self.assertEqual(by_type["CS"]["mes_code"], "ARRA")
        self.assertEqual(by_type["EL_REGULAR"]["mes_code"], "KROMKA")
        self.assertEqual(by_type["EL_OVAL"]["mes_code"], "OVAL_KROMKA")
        self.assertEqual(by_type["XNC_BORE"]["mes_code"], "PRISADKA")
        self.assertIsNone(by_type["CL"]["mes_code"])
        self.assertIsNone(by_type["XNC_MILL"]["mes_code"])
        self.assertIsNone(by_type["XNC_CUT"]["mes_code"])

    def test_edge_band_never_a_standalone_bom_item_type(self):
        _project, plan = self._build_plan({"ARRA", "KROMKA", "OVAL_KROMKA", "PRISADKA"})
        item_types = {item["item_type"] for item in plan.bom_items_payload}
        self.assertTrue(item_types.issubset({"part", "material", "edge_band"}))
        edge_items = [i for i in plan.bom_items_payload if i["item_type"] == "edge_band"]
        self.assertEqual(len(edge_items), 45)
        self.assertTrue(all(i["part_external_id"] is None and i["target_part_external_id"] for i in edge_items))


class GibLabImportIntegrationTests(APITestCase):
    def setUp(self):
        _seed_operations()
        self.manager = User.objects.create_user(
            username="giblab-manager", phone="+998901114401", password="secret-pass", role=Role.MANAGER,
        )
        self.operator = User.objects.create_user(
            username="giblab-operator", phone="+998901114402", password="secret-pass", role=Role.OPERATOR,
        )
        self.data = _load_fixture_bytes()

    def test_validate_makes_no_database_writes(self):
        self.client.force_authenticate(user=self.manager)
        before_orders = Order.objects.count()
        before_parts = Part.objects.count()
        response = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_valid"])
        self.assertEqual(Order.objects.count(), before_orders)
        self.assertEqual(Part.objects.count(), before_parts)
        self.assertEqual(GibLabImportBatch.objects.count(), 0)

    def test_validate_denied_for_non_management_role(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    def test_full_import_creates_draft_order(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            "/api/giblab-imports/import/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        result = response.data
        self.assertTrue(result["success"])
        order = Order.objects.get(pk=result["order_id"])
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertEqual(order.product_quantity, 20)
        self.assertEqual(order.products.count(), 1)
        self.assertEqual(order.parts.count(), 30)
        self.assertEqual(sum(p.quantity for p in order.parts.all()), 1040)
        self.assertEqual(BOM.objects.filter(product__order=order).count(), 1)
        self.assertEqual(BOMItem.objects.filter(bom__product__order=order, item_type="edge_band").count(), 45)
        self.assertTrue(PartRoute.objects.filter(part__order=order).exists())
        self.assertTrue(order.parts.filter(current_operation__isnull=False).exists())

        batch = GibLabImportBatch.objects.get(order=order)
        self.assertEqual(batch.status, GibLabImportBatch.Status.COMPLETED)

        self.assertTrue(AuditLog.objects.filter(action="giblab.import").exists())

    def test_duplicate_checksum_returns_409(self):
        self.client.force_authenticate(user=self.manager)
        first = self.client.post(
            "/api/giblab-imports/import/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(first.status_code, 200, first.data)

        second = self.client.post(
            "/api/giblab-imports/import/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["code"], "DUPLICATE_IMPORT")

    def test_rollback_on_error_leaves_no_domain_rows(self):
        self.client.force_authenticate(user=self.manager)
        before_orders = Order.objects.count()
        before_parts = Part.objects.count()
        with mock.patch.object(PartRoute.objects, "bulk_create", side_effect=RuntimeError("forced failure")):
            response = self.client.post(
                "/api/giblab-imports/import/", {"file": _uploaded(self.data)}, format="multipart",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "IMPORT_ROLLED_BACK")
        self.assertEqual(Order.objects.count(), before_orders)
        self.assertEqual(Part.objects.count(), before_parts)
        batch = GibLabImportBatch.objects.latest("created_at")
        self.assertEqual(batch.status, GibLabImportBatch.Status.FAILED)
