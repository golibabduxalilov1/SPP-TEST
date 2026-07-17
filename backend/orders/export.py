import io

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

STATUS_LABELS = {
    "draft": "Yangi", "approved": "Tasdiqlangan", "in_production": "Jarayonda",
    "partially_ready": "Qisman tayyor", "ready_for_packaging": "Qadoqlashga tayyor",
    "packaging": "Qadoqlanmoqda", "warehouse": "Tayyor omborda", "delivered": "Mijozga topshirildi",
    "cancelled": "Bekor qilingan",
}
PRIORITY_LABELS = {"low": "Past", "normal": "Oddiy", "high": "Yuqori", "urgent": "Shoshilinch"}

HEADERS = ["Buyurtma", "Mijoz", "Telefon", "Mahsulot", "Muddat", "Prioritet", "Status", "Detallar", "Yaratilgan"]


def _row(order):
    parts = list(order.parts.all())
    completed = sum(1 for p in parts if p.status == "completed")
    return [
        order.order_no,
        order.customer_name or "-",
        order.customer_phone or "-",
        order.product_name or "-",
        order.deadline.strftime("%d.%m.%Y") if order.deadline else "-",
        PRIORITY_LABELS.get(order.priority, order.priority),
        STATUS_LABELS.get(order.status, order.status),
        f"{completed}/{len(parts)}",
        order.created_at.strftime("%d.%m.%Y"),
    ]


def render_orders_excel(orders):
    wb = Workbook()
    ws = wb.active
    ws.title = "Buyurtmalar"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for order in orders:
        ws.append(_row(order))
    for column_cells in ws.columns:
        length = max(len(str(cell.value or "")) for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), 40)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def render_orders_pdf(orders):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title="Buyurtmalar")
    styles = getSampleStyleSheet()
    data = [HEADERS] + [_row(order) for order in orders]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6B4423")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8C6AC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F1E8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    doc.build([Paragraph("Buyurtmalar ro'yxati", styles["Title"]), Spacer(1, 12), table])
    buf.seek(0)
    return buf
