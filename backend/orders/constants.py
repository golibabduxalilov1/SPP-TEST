OPERATION_SEEDS = [
    dict(code="ARRA", name="Arra", measure_unit="m2", qr_scan_required=True, order_index=1),
    dict(code="KROMKA", name="Qirra qoplash", measure_unit="meter", qr_scan_required=True, order_index=2),
    dict(code="PRISADKA", name="Teshik ochish", measure_unit="piece", qr_scan_required=True, order_index=3),
    dict(code="OMBOR", name="Tayyor ombor", measure_unit="package", qr_scan_required=True, order_index=9),
]

# Route templates per spec section 5.6 — mapped by a short key used in file import ("route" column).
ROUTE_TEMPLATES = {
    "oddiy_panel": ["ARRA", "KROMKA", "PRISADKA", "OMBOR"],
    "faqat_kesish": ["ARRA", "OMBOR"],
    "cnc": ["ARRA", "KROMKA", "PRISADKA", "OMBOR"],
    "stolyarka": ["ARRA", "PRISADKA", "OMBOR"],
}

DEFAULT_ROUTE_KEY = "oddiy_panel"
