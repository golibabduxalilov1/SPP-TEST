OPERATION_SEEDS = [
    dict(code="ARRA", name="Arra", measure_unit="m2", qr_scan_required=True, order_index=1),
    dict(code="KROMKA", name="Kromka", measure_unit="meter", qr_scan_required=True, order_index=2),
    dict(code="PRISADKA", name="Prisadka", measure_unit="piece", qr_scan_required=True, order_index=3),
    dict(code="PAZ", name="Paz", measure_unit="meter", qr_scan_required=False, order_index=4),
    dict(code="ROVER", name="Rover/CNC", measure_unit="meter", qr_scan_required=False, order_index=5),
    dict(code="STOLYARKA", name="Stolyarka", measure_unit="piece", qr_scan_required=False, order_index=6),
    dict(code="YIGISH", name="Yig'ish", measure_unit="piece", qr_scan_required=True, order_index=7),
    dict(code="QADOQLASH", name="Qadoqlash", measure_unit="package", qr_scan_required=True, order_index=8),
    dict(code="OMBOR", name="Tayyor ombor", measure_unit="package", qr_scan_required=True, order_index=9),
]

# Route templates per spec section 5.6 — mapped by a short key used in file import ("route" column).
ROUTE_TEMPLATES = {
    "oddiy_panel": ["ARRA", "KROMKA", "PRISADKA", "YIGISH", "QADOQLASH", "OMBOR"],
    "faqat_kesish": ["ARRA", "QADOQLASH", "OMBOR"],
    "cnc": ["ARRA", "KROMKA", "ROVER", "PRISADKA", "YIGISH", "QADOQLASH", "OMBOR"],
    "stolyarka": ["ARRA", "STOLYARKA", "YIGISH", "QADOQLASH", "OMBOR"],
}

DEFAULT_ROUTE_KEY = "oddiy_panel"
