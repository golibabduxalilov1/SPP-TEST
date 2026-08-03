"""Tests for the GibLab `.project` import pipeline (backend/orders/giblab/)
and its integration into Order creation (`POST /api/orders/` with
`giblab_import_id`, see orders/views.py OrderViewSet._create_from_giblab_import).

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
from .models import BOM, BOMItem, GibLabImportBatch, Order, OrderDetail, Part, PartRoute, Product

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

MULTI_PRODUCT_XML = """<?xml version="1.0"?>
<project project.uuid="22222222-2222-2222-2222-222222222222" version="23051701" currency="UZS" importBMV="1">
  <good typeId="product" id="1" name="P1" count="2">
    <part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>
  </good>
  <good typeId="product" id="2" name="P2" count="3">
    <part id="2" code="C2" name="Part2" count="1" usedCount="3" l="400" w="200"/>
  </good>
  <good typeId="sheet" id="3" code="S1" name="Sheet1" l="2500" w="1800" t="16" count="1"/>
  <operation id="4" typeId="CS">
    <material id="3"/>
    <part id="1"/>
    <part id="2"/>
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

    def test_missing_code_gets_deterministic_fallback_and_warns(self):
        xml = MINIMAL_PRODUCT_XML.replace(
            '<part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>',
            '<part id="1" name="Part1" count="1" usedCount="2" l="500" w="300"/>',
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        part = project.products[0].parts[0]
        self.assertTrue(part.code)
        self.assertIn("1", part.code)
        self.assertIn("PART1", part.code)

        errors, _warnings = validator.structural_validate(project)
        self.assertFalse(any(e["code"] == "MISSING_REQUIRED_FIELD" and e["external_id"] == "1" for e in errors))
        self.assertTrue(any(w["code"] == "PART_CODE_FALLBACK_GENERATED" for w in project.warnings))

        # Re-parsing the same input always yields the same fallback code.
        project2 = parser.parse(file_reader.parse_xml_safely(xml))
        self.assertEqual(part.code, project2.products[0].parts[0].code)

    def test_missing_code_without_name_falls_back_to_id(self):
        xml = MINIMAL_PRODUCT_XML.replace(
            '<part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>',
            '<part id="1" count="1" usedCount="2" l="500" w="300"/>',
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        part = project.products[0].parts[0]
        self.assertEqual(part.code, "1")  # id-only fallback -- still usable, id is present

        errors, _warnings = validator.structural_validate(project)
        self.assertTrue(any(e["code"] == "MISSING_REQUIRED_FIELD" and "name" in e["message"] for e in errors))

    def test_missing_code_id_and_name_leaves_import_fatal(self):
        """Boundary case: with neither id nor name, there is nothing to build
        a fallback code from -- the pre-existing id/name fatal errors should
        still stand, unaffected by the fallback-code logic."""
        xml = MINIMAL_PRODUCT_XML.replace(
            '<part id="1" code="C1" name="Part1" count="1" usedCount="2" l="500" w="300"/>',
            '<part count="1" usedCount="2" l="500" w="300"/>',
        )
        root = file_reader.parse_xml_safely(xml)
        project = parser.parse(root)
        part = project.products[0].parts[0]
        self.assertEqual(part.code, "")

        errors, _warnings = validator.structural_validate(project)
        error_codes = [e["code"] for e in errors if e["entity_type"] == "part"]
        self.assertIn("MISSING_REQUIRED_FIELD", error_codes)
        self.assertTrue(any("id" in e["message"] for e in errors if e["entity_type"] == "part"))
        self.assertTrue(any("name" in e["message"] for e in errors if e["entity_type"] == "part"))


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

    def test_multiple_products_rejected(self):
        root = file_reader.parse_xml_safely(MULTI_PRODUCT_XML)
        project = parser.parse(root)
        errors, _warnings = validator.structural_validate(project)
        error = next(e for e in errors if e["code"] == "MULTIPLE_PRODUCTS_NOT_SUPPORTED")
        self.assertEqual(error["details"]["count"], 2)
        self.assertEqual(sorted(error["details"]["names"]), ["P1", "P2"])


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


class GibLabValidateSessionApiTests(APITestCase):
    """`POST /api/giblab-imports/validate/` persists an import session but
    must never touch Order/Product/Part/BOM domain tables."""

    def setUp(self):
        _seed_operations()
        self.manager = User.objects.create_user(
            username="giblab-manager", phone="+998901114401", password="secret-pass", role=Role.MANAGER,
        )
        self.operator = User.objects.create_user(
            username="giblab-operator", phone="+998901114402", password="secret-pass", role=Role.OPERATOR,
        )
        self.data = _load_fixture_bytes()

    def test_validate_creates_a_session_without_domain_writes(self):
        self.client.force_authenticate(user=self.manager)
        before_orders = Order.objects.count()
        before_parts = Part.objects.count()
        response = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_valid"])
        self.assertTrue(response.data["import_id"])
        self.assertEqual(response.data["file"]["version"], "23051701")
        self.assertEqual(Order.objects.count(), before_orders)
        self.assertEqual(Part.objects.count(), before_parts)

        batch = GibLabImportBatch.objects.get(uuid=response.data["import_id"])
        self.assertEqual(batch.status, GibLabImportBatch.Status.VALIDATED)
        self.assertTrue(batch.import_plan)
        self.assertIsNotNone(batch.expires_at)
        self.assertEqual(batch.imported_by, self.manager)

        form = response.data["form"]
        self.assertEqual(form["product_name"], "Test Product A")
        self.assertEqual(form["product_quantity"], 20)
        self.assertEqual(len(form["details"]), 30)
        row = next(d for d in form["details"] if d["code"] == "1 Shkaf_1")
        self.assertEqual(row["name"], "Shkaf_1-Bok l")
        self.assertEqual(Decimal(row["length_mm"]), Decimal("2400"))
        self.assertEqual(Decimal(row["width_mm"]), Decimal("516"))
        self.assertEqual(row["quantity"], 1)
        self.assertEqual(row["total_quantity"], 20)
        self.assertTrue(row["material"])

    def test_revalidating_same_file_reuses_session_row(self):
        self.client.force_authenticate(user=self.manager)
        first = self.client.post("/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart")
        second = self.client.post("/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart")
        self.assertEqual(GibLabImportBatch.objects.count(), 1)
        self.assertNotEqual(first.data["import_id"], None)
        self.assertEqual(first.data["import_id"], second.data["import_id"])

    def test_validate_denied_for_non_management_role(self):
        self.client.force_authenticate(user=self.operator)
        response = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_file_session_cannot_be_consumed(self):
        self.client.force_authenticate(user=self.manager)
        broken = MINIMAL_PRODUCT_XML.replace('<material id="2"/>', '<material id="999"/>')
        response = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(broken.encode("utf-8"), name="broken.project")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_valid"])
        import_id = response.data["import_id"]

        create_response = self.client.post("/api/orders/", {
            "customer_name": "Ali", "customer_phone": "+998901110000", "giblab_import_id": import_id,
        }, format="json")
        self.assertEqual(create_response.status_code, 400, create_response.data)
        self.assertEqual(create_response.data["code"], "IMPORT_SESSION_INVALID")


class GibLabOrderCreateApiTests(APITestCase):
    """`POST /api/orders/` with `giblab_import_id` -- the only place a
    validated import session turns into real Order/Product/Part/BOM/
    PartRoute rows (see orders/giblab/service.create_order_from_giblab_import)."""

    def setUp(self):
        _seed_operations()
        self.manager = User.objects.create_user(
            username="giblab-order-manager", phone="+998901114410", password="secret-pass", role=Role.MANAGER,
        )
        self.other_manager = User.objects.create_user(
            username="giblab-order-other", phone="+998901114411", password="secret-pass", role=Role.MANAGER,
        )
        self.data = _load_fixture_bytes()

    def _validate(self, user=None, data=None):
        self.client.force_authenticate(user=user or self.manager)
        response = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(data or self.data)}, format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["import_id"]

    def _create_order(self, import_id, **overrides):
        payload = {
            "customer_name": "Ali Valiyev", "customer_phone": "+998901234567",
            "deadline": "2026-08-15", "priority": "normal", "notes": "Shoshilinch",
            "giblab_import_id": import_id,
        }
        payload.update(overrides)
        return self.client.post("/api/orders/", payload, format="json")

    def test_full_flow_creates_order_from_server_side_plan(self):
        import_id = self._validate()
        self.client.force_authenticate(user=self.manager)
        response = self._create_order(import_id)
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.customer_name, "Ali Valiyev")
        self.assertEqual(order.customer_phone, "+998901234567")
        self.assertEqual(str(order.deadline), "2026-08-15")
        self.assertEqual(order.priority, "normal")
        self.assertEqual(order.notes, "Shoshilinch")
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertEqual(order.product_name, "Test Product A")
        self.assertEqual(order.product_quantity, 20)
        self.assertEqual(order.products.count(), 1)
        self.assertEqual(order.parts.count(), 30)
        self.assertEqual(sum(p.quantity for p in order.parts.all()), 1040)
        self.assertEqual(BOM.objects.filter(product__order=order).count(), 1)
        self.assertEqual(BOMItem.objects.filter(bom__product__order=order, item_type="edge_band").count(), 45)
        self.assertTrue(PartRoute.objects.filter(part__order=order).exists())
        self.assertTrue(order.parts.filter(current_operation__isnull=False).exists())

        batch = GibLabImportBatch.objects.get(uuid=import_id)
        self.assertEqual(batch.status, GibLabImportBatch.Status.COMPLETED)
        self.assertEqual(batch.order, order)
        self.assertIsNotNone(batch.consumed_at)

        self.assertTrue(AuditLog.objects.filter(action="order.create_from_giblab").exists())

    def test_client_supplied_product_fields_are_ignored(self):
        """Even if the client sends a different product_name/quantity/details
        alongside giblab_import_id, the server-side plan wins (spec: never
        trust client-supplied import data)."""
        import_id = self._validate()
        self.client.force_authenticate(user=self.manager)
        response = self._create_order(import_id, product_name="Hacked name", product_quantity=999)
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.product_name, "Test Product A")
        self.assertEqual(order.product_quantity, 20)

    def test_extra_manual_details_are_created_alongside_the_import(self):
        """The user can add extra hand-typed detail rows (e.g. an accessory
        the GibLab file doesn't cover) on top of the imported ones -- these
        become real OrderDetail+Part rows, additive to (never replacing)
        the 30 imported parts."""
        import_id = self._validate()
        self.client.force_authenticate(user=self.manager)
        response = self._create_order(
            import_id, details=[{"name": "Qo'lda qo'shilgan aksessuar", "quantity": 2, "material_type": "Furnitura"}],
        )
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])

        self.assertEqual(OrderDetail.objects.filter(order=order).count(), 1)
        extra_detail = OrderDetail.objects.get(order=order)
        self.assertEqual(extra_detail.name, "Qo'lda qo'shilgan aksessuar")
        self.assertIsNotNone(extra_detail.part_id)
        # OrderDetail.quantity (2) x Order.product_quantity (20, from the
        # import) -- same invariant as the plain manual-detail flow.
        self.assertEqual(extra_detail.part.quantity, 40)

        # The 30 imported parts are untouched -- extra details are additive.
        self.assertEqual(order.parts.count(), 31)

        response = self.client.get(f"/api/orders/{order.id}/")
        details = response.data["details"]
        self.assertEqual(len(details), 31)
        manual_row = next(d for d in details if d["source"] == "manual")
        self.assertTrue(manual_row["editable"])
        self.assertEqual(sum(1 for d in details if d["source"] == "giblab"), 30)

    def test_session_cannot_be_reused_after_consumption(self):
        import_id = self._validate()
        self.client.force_authenticate(user=self.manager)
        first = self._create_order(import_id)
        self.assertEqual(first.status_code, 201, first.data)
        second = self._create_order(import_id)
        self.assertEqual(second.status_code, 409, second.data)
        self.assertEqual(second.data["code"], "IMPORT_SESSION_CONSUMED")
        self.assertEqual(Order.objects.count(), 1)

    def test_other_user_cannot_consume_session(self):
        import_id = self._validate(user=self.manager)
        self.client.force_authenticate(user=self.other_manager)
        response = self._create_order(import_id)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "IMPORT_SESSION_FORBIDDEN")

    def test_unknown_import_id_returns_404(self):
        self.client.force_authenticate(user=self.manager)
        response = self._create_order("00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "IMPORT_SESSION_NOT_FOUND")

    def test_expired_session_rejected(self):
        import_id = self._validate()
        batch = GibLabImportBatch.objects.get(uuid=import_id)
        from django.utils import timezone
        batch.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        batch.save(update_fields=["expires_at"])

        self.client.force_authenticate(user=self.manager)
        response = self._create_order(import_id)
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data["code"], "IMPORT_SESSION_EXPIRED")
        batch.refresh_from_db()
        self.assertEqual(batch.status, GibLabImportBatch.Status.EXPIRED)

    def test_rollback_on_error_marks_session_failed_and_leaves_no_domain_rows(self):
        import_id = self._validate()
        self.client.force_authenticate(user=self.manager)
        before_orders = Order.objects.count()
        with mock.patch.object(PartRoute.objects, "bulk_create", side_effect=RuntimeError("forced failure")):
            response = self._create_order(import_id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "IMPORT_ROLLED_BACK")
        self.assertEqual(Order.objects.count(), before_orders)

        batch = GibLabImportBatch.objects.get(uuid=import_id)
        self.assertEqual(batch.status, GibLabImportBatch.Status.FAILED)
        self.assertTrue(batch.errors)
        self.assertTrue(AuditLog.objects.filter(action="giblab.import_failed").exists())

    def test_same_file_can_be_reimported_to_create_multiple_orders(self):
        """A GibLab design (e.g. one furniture model) is routinely ordered by
        several different customers -- re-validating and re-consuming the
        exact same `.project` file must succeed every time and produce a
        separate, independent Order each time, not a DUPLICATE_IMPORT error."""
        self.client.force_authenticate(user=self.manager)

        first_import_id = self._validate()
        first_create = self._create_order(first_import_id, customer_name="Ali")
        self.assertEqual(first_create.status_code, 201, first_create.data)

        second_validate = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(second_validate.status_code, 200, second_validate.data)
        self.assertTrue(second_validate.data["is_valid"])
        self.assertEqual(second_validate.data["errors"], [])
        self.assertNotEqual(second_validate.data["import_id"], first_import_id)

        second_create = self._create_order(second_validate.data["import_id"], customer_name="Vali")
        self.assertEqual(second_create.status_code, 201, second_create.data)
        self.assertNotEqual(second_create.data["id"], first_create.data["id"])

        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(GibLabImportBatch.objects.filter(status=GibLabImportBatch.Status.COMPLETED).count(), 2)
        for order in Order.objects.all():
            self.assertEqual(order.product_name, "Test Product A")
            self.assertEqual(order.parts.count(), 30)

    def test_deleting_the_order_does_not_affect_future_reimport(self):
        """`GibLabImportBatch.order` is SET_NULL -- deleting an Order created
        from a GibLab import must not disturb later re-imports of the same
        file (which already succeed regardless, see the test above)."""
        import_id = self._validate()
        self.client.force_authenticate(user=self.manager)
        create_response = self._create_order(import_id)
        self.assertEqual(create_response.status_code, 201, create_response.data)
        order_id = create_response.data["id"]

        delete_response = self.client.delete(f"/api/orders/{order_id}/")
        self.assertEqual(delete_response.status_code, 204, delete_response.data)

        batch = GibLabImportBatch.objects.get(uuid=import_id)
        self.assertEqual(batch.status, GibLabImportBatch.Status.COMPLETED)
        self.assertIsNone(batch.order_id)

        revalidate = self.client.post(
            "/api/giblab-imports/validate/", {"file": _uploaded(self.data)}, format="multipart",
        )
        self.assertEqual(revalidate.status_code, 200, revalidate.data)
        self.assertTrue(revalidate.data["is_valid"])

        second_create = self._create_order(revalidate.data["import_id"])
        self.assertEqual(second_create.status_code, 201, second_create.data)


class GibLabOrderDetailsApiTests(APITestCase):
    """`GET /api/orders/{id}/` must surface GibLab-imported Parts in the same
    `details` list the "Mahsulot detallari" table renders, without ever
    writing OrderDetail rows for them (see OrderDetailSerializer.get_details)."""

    def setUp(self):
        _seed_operations()
        self.manager = User.objects.create_user(
            username="giblab-details-manager", phone="+998901114403", password="secret-pass", role=Role.MANAGER,
        )
        self.client.force_authenticate(user=self.manager)
        validate_response = self.client.post(
            "/api/giblab-imports/validate/",
            {"file": _uploaded(MINIMAL_PRODUCT_XML.encode("utf-8"), name="minimal.project")},
            format="multipart",
        )
        self.assertEqual(validate_response.status_code, 200, validate_response.data)
        import_id = validate_response.data["import_id"]
        create_response = self.client.post("/api/orders/", {
            "customer_name": "Test", "customer_phone": "+998900000000", "giblab_import_id": import_id,
        }, format="json")
        self.assertEqual(create_response.status_code, 201, create_response.data)
        self.order_id = create_response.data["id"]

    def test_order_details_endpoint_includes_giblab_part(self):
        response = self.client.get(f"/api/orders/{self.order_id}/")
        self.assertEqual(response.status_code, 200, response.data)
        details = response.data["details"]
        self.assertEqual(len(details), 1)
        row = details[0]
        self.assertEqual(row["name"], "Part1")
        self.assertEqual(Decimal(row["length_mm"]), Decimal("500.0"))
        self.assertEqual(Decimal(row["width_mm"]), Decimal("300.0"))
        self.assertEqual(row["source"], "giblab")
        self.assertFalse(row["editable"])
        self.assertTrue(row["qr_token"])
        self.assertEqual(row["part_code"], "C1")

    def test_giblab_quantity_is_per_product_not_double_multiplied(self):
        """MINIMAL_PRODUCT_XML: count="1" (per product), usedCount="2" (order
        total, product count=2). The table's `quantity` column must be the
        per-product number (1), matching OrderDetail semantics — the
        frontend multiplies by product_quantity itself for the "Jami" total."""
        order = Order.objects.get(pk=self.order_id)
        part = order.parts.get()
        self.assertEqual(order.product_quantity, 2)
        self.assertEqual(part.quantity, 2)  # already the whole-order total

        response = self.client.get(f"/api/orders/{self.order_id}/")
        row = response.data["details"][0]
        self.assertEqual(Decimal(row["quantity"]), Decimal("1"))
        self.assertEqual(Decimal(row["quantity"]) * order.product_quantity, part.quantity)

    def test_giblab_parts_are_not_duplicated_into_orderdetail_rows(self):
        self.assertEqual(OrderDetail.objects.filter(order_id=self.order_id).count(), 0)
        response = self.client.get(f"/api/orders/{self.order_id}/")
        self.assertEqual(len(response.data["details"]), 1)

    def test_manual_orderdetail_flow_unaffected(self):
        """Adding a manual detail row alongside a GibLab-imported order
        exercises both code paths together — the pre-existing OrderDetail
        create flow must still work exactly as before."""
        response = self.client.post(
            "/api/order-details/",
            {"order": self.order_id, "name": "Qo'shimcha panel", "quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        detail_response = self.client.get(f"/api/orders/{self.order_id}/")
        details = detail_response.data["details"]
        self.assertEqual(len(details), 2)
        manual_row = next(d for d in details if d["source"] == "manual")
        giblab_row = next(d for d in details if d["source"] == "giblab")
        self.assertTrue(manual_row["editable"])
        self.assertEqual(manual_row["name"], "Qo'shimcha panel")
        self.assertFalse(giblab_row["editable"])

    def test_editing_giblab_detail_row_via_order_details_api_is_rejected(self):
        """A GibLab row has no OrderDetail id — its synthesized id (`part-N`)
        must not resolve against the OrderDetail endpoint, so it cannot be
        edited/deleted through the manual-details API."""
        giblab_part_id = f"part-{Part.objects.get(order_id=self.order_id).id}"
        response = self.client.patch(
            f"/api/order-details/{giblab_part_id}/", {"name": "hacked"}, format="json",
        )
        self.assertEqual(response.status_code, 404)


class GibLabManualOrderCreateRegressionTests(APITestCase):
    """The pre-existing manual (non-GibLab) `POST /api/orders/` flow must be
    completely unaffected by the giblab_import_id branch in
    OrderViewSet.create."""

    def setUp(self):
        self.manager = User.objects.create_user(
            username="manual-order-manager", phone="+998901114420", password="secret-pass", role=Role.MANAGER,
        )
        self.client.force_authenticate(user=self.manager)

    def test_manual_order_create_still_works(self):
        response = self.client.post("/api/orders/", {
            "customer_name": "Manual mijoz", "customer_phone": "+998901112233",
            "product_name": "Qo'lda kiritilgan shkaf", "product_quantity": 3,
            "details": [{"name": "Panel", "quantity": 2}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.product_name, "Qo'lda kiritilgan shkaf")
        self.assertEqual(OrderDetail.objects.filter(order=order).count(), 1)
        self.assertEqual(Part.objects.filter(order=order).count(), 1)
