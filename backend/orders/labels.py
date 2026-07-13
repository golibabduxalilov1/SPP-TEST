import io

import qrcode
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _draw_label(c, part, width_mm, height_mm):
    w, h = width_mm * mm, height_mm * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(3 * mm, h - 5 * mm, "SPP")
    c.setFont("Helvetica", 6.5)
    c.drawString(3 * mm, h - 9 * mm, f"Buyurtma: #{part.order.order_no} | {part.order.product_name or ''}"[:48])
    c.drawString(3 * mm, h - 13 * mm, f"Detal: {part.code} - {part.name}"[:48])
    dims = f"{part.length_mm or '-'}x{part.width_mm or '-'}x{part.thickness_mm or '-'} mm"
    c.drawString(3 * mm, h - 17 * mm, dims)
    c.drawString(3 * mm, h - 21 * mm, f"Material: {part.material} | Rang: {part.color}"[:48])
    c.drawString(3 * mm, h - 25 * mm, f"Soni: {part.quantity} dona")
    route_codes = " -> ".join(r.operation.code for r in part.routes.all())
    c.setFont("Helvetica", 5.5)
    c.drawString(3 * mm, h - 29 * mm, route_codes[:60])

    qr_img = qrcode.make(part.qr_token)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    from reportlab.lib.utils import ImageReader

    qr_size = min(h - 32 * mm, 20 * mm)
    c.drawImage(ImageReader(buf), w - qr_size - 3 * mm, 3 * mm, width=qr_size, height=qr_size)
    c.setFont("Helvetica", 5)
    c.drawString(3 * mm, 2 * mm, part.qr_token)


def render_labels_pdf(parts, width_mm=70, height_mm=50):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width_mm * mm, height_mm * mm))
    for part in parts:
        _draw_label(c, part, width_mm, height_mm)
        c.showPage()
    c.save()
    buf.seek(0)
    return buf
