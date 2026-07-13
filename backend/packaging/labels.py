import io

import qrcode
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_package_label_pdf(package, width_mm=70, height_mm=50):
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    w, h = width_mm * mm, height_mm * mm
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(3 * mm, h - 6 * mm, "SPP — QADOQ")
    c.setFont("Helvetica", 7)
    c.drawString(3 * mm, h - 11 * mm, f"Buyurtma: #{package.order.order_no}")
    c.drawString(3 * mm, h - 15 * mm, f"Qadoq: {package.package_no}")
    c.drawString(3 * mm, h - 19 * mm, f"Detallar soni: {package.items.count()}")

    qr_img = qrcode.make(package.qr_token)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_size = min(h - 22 * mm, 22 * mm)
    c.drawImage(ImageReader(qr_buf), w - qr_size - 3 * mm, 2 * mm, width=qr_size, height=qr_size)
    c.setFont("Helvetica", 5)
    c.drawString(3 * mm, 2 * mm, package.qr_token)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf
