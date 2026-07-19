import csv
import io

from django.db import transaction
from manufacturing.models import Operation

from .constants import DEFAULT_ROUTE_KEY, ROUTE_TEMPLATES
from .models import Order, Part, PartRoute, Product


def assign_route(part: Part, route_key: str):
    codes = ROUTE_TEMPLATES.get(route_key, ROUTE_TEMPLATES[DEFAULT_ROUTE_KEY])
    operations = {op.code: op for op in Operation.objects.filter(code__in=codes, is_active=True)}
    part.routes.all().delete()
    first_operation = None
    for index, code in enumerate(codes, start=1):
        operation = operations.get(code)
        if not operation:
            continue
        if first_operation is None:
            first_operation = operation
        PartRoute.objects.create(
            part=part,
            operation=operation,
            sequence_index=index,
            status=PartRoute.Status.PENDING,
        )
    part.current_operation = first_operation
    part.save(update_fields=["current_operation"])


def create_part_for_order_detail(detail):
    """Every 'Mahsulot detallari' row gets its own trackable Part (unique QR + route)."""
    part = Part.objects.create(
        order=detail.order,
        code=f"{detail.order.order_no}-{detail.id}",
        name=detail.name,
        material=detail.material_type,
        length_mm=detail.length_mm,
        width_mm=detail.width_mm,
        thickness_mm=detail.thickness_mm,
        quantity=detail.quantity,
    )
    assign_route(part, DEFAULT_ROUTE_KEY)
    detail.part = part
    detail.save(update_fields=["part"])
    return part


def sync_part_from_order_detail(detail):
    if not detail.part_id:
        return
    Part.objects.filter(pk=detail.part_id).update(
        name=detail.name,
        material=detail.material_type,
        length_mm=detail.length_mm,
        width_mm=detail.width_mm,
        thickness_mm=detail.thickness_mm,
        quantity=detail.quantity,
    )


REQUIRED_IMPORT_COLUMNS = [
    "order", "product", "part_code", "part_name", "length_mm", "width_mm", "thickness_mm",
    "quantity", "material", "edge_meter", "drilling_count", "route",
]


def _read_rows(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        text = uploaded_file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]

    import openpyxl

    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    result = []
    for raw in rows[1:]:
        if all(v in (None, "") for v in raw):
            continue
        result.append({headers[i]: raw[i] for i in range(len(headers)) if i < len(raw)})
    return result


@transaction.atomic
def import_parts_from_file(uploaded_file, user):
    rows = _read_rows(uploaded_file)
    errors = []
    created_orders = {}
    created_products = {}
    created_parts = []

    for line_no, row in enumerate(rows, start=2):
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        missing = [c for c in ("order", "part_code", "part_name") if not row.get(c)]
        if missing:
            errors.append({"row": line_no, "error": f"Majburiy ustunlar to'ldirilmagan: {', '.join(missing)}"})
            continue
        try:
            order_key = str(row["order"])
            order = created_orders.get(order_key)
            if not order:
                order = Order.objects.filter(order_no=order_key).first()
                if not order:
                    order = Order.objects.create(order_no=order_key, product_name=str(row.get("product") or ""), created_by=user)
                created_orders[order_key] = order

            product_name = str(row.get("product") or order.product_name or "Mahsulot")
            product_key = (order_key, product_name)
            product = created_products.get(product_key)
            if not product:
                product, _ = Product.objects.get_or_create(order=order, name=product_name)
                created_products[product_key] = product

            part = Part.objects.create(
                order=order,
                product=product,
                code=str(row["part_code"]),
                name=str(row["part_name"]),
                material=str(row.get("material") or ""),
                length_mm=row.get("length_mm") or None,
                width_mm=row.get("width_mm") or None,
                thickness_mm=row.get("thickness_mm") or None,
                quantity=int(row.get("quantity") or 1),
                edge_meter=row.get("edge_meter") or None,
                drilling_count=int(row.get("drilling_count") or 0),
            )
            route_key = str(row.get("route") or DEFAULT_ROUTE_KEY).strip().lower()
            assign_route(part, route_key)
            created_parts.append(part)
        except Exception as exc:  # noqa: BLE001 - surfaced back to the importing user per-row
            errors.append({"row": line_no, "error": str(exc)})

    return {
        "orders_affected": list({o.order_no for o in created_orders.values()}),
        "parts_created": len(created_parts),
        "errors": errors,
    }
