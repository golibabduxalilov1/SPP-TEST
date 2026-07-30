# The 13 standard production stages, in their fixed 1-13 order. This is the
# single source of truth mirrored by manufacturing/migrations/0005_seed_standard_stages.py
# (which writes these rows to the database) — see that migration for why the
# list can't just live in the database alone.
OPERATION_SEEDS = [
    dict(code="ARRA", name="Arra", measure_unit="meter", qr_scan_required=True, order_index=1),
    dict(code="ARRA_AVTOMAT", name="Arra (avtomat)", measure_unit="meter", qr_scan_required=True, order_index=2),
    dict(code="KROMKA", name="Kromka", measure_unit="meter", qr_scan_required=True, order_index=3),
    dict(code="OVAL_KROMKA", name="Oval kromka", measure_unit="meter", qr_scan_required=True, order_index=4),
    dict(code="PRISADKA", name="Prisadka", measure_unit="piece", qr_scan_required=True, order_index=5),
    dict(code="NAQSH_ROVER", name="Naqsh (rover)", measure_unit="m2", qr_scan_required=True, order_index=6),
    dict(code="FREZER", name="Frezer", measure_unit="meter", qr_scan_required=True, order_index=7),
    dict(code="YELIMLASH", name="Yelimlash", measure_unit="m2", qr_scan_required=True, order_index=8),
    dict(code="SAYQALLASH", name="Sayqallash", measure_unit="m2", qr_scan_required=True, order_index=9),
    dict(code="BOYASH", name="Bo'yash", measure_unit="m2", qr_scan_required=True, order_index=10),
    dict(code="TERI_QOPLASH", name="Teri qoplash", measure_unit="m2", qr_scan_required=True, order_index=11),
    dict(code="YIGISH", name="Yig'ish", measure_unit="piece", qr_scan_required=True, order_index=12),
    dict(code="QADOQLASH", name="Qadoqlash", measure_unit="package", qr_scan_required=True, order_index=13),
]

STANDARD_OPERATION_CODES = [seed["code"] for seed in OPERATION_SEEDS]

# Route templates per spec section 5 — mapped by a short key used in file
# import ("route" column) and for non-default/import product routes. Every
# code here must be one of STANDARD_OPERATION_CODES, and the codes within a
# template must already be in standard order_index order.
ROUTE_TEMPLATES = {
    "oddiy_panel": list(STANDARD_OPERATION_CODES),
    "faqat_kesish": ["ARRA", "QADOQLASH"],
    "cnc": ["ARRA", "KROMKA", "PRISADKA", "QADOQLASH"],
    "stolyarka": ["ARRA", "PRISADKA", "YIGISH", "QADOQLASH"],
}

DEFAULT_ROUTE_KEY = "oddiy_panel"
