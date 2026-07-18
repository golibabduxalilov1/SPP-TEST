import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Check, Pencil, Printer, QrCode } from "lucide-react";
import { QRCodeCanvas } from "qrcode.react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { useAuthStore } from "../../store/authStore";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { PageLoader } from "../../components/ui/Misc";
import { StatusBadge } from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import EditableDetailsTable from "../../components/admin/EditableDetailsTable";
import EditOrderModal from "../../components/admin/EditOrderModal";
import { format } from "date-fns";

export default function OrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [qrDetail, setQrDetail] = useState(null);
  const [approving, setApproving] = useState(false);
  const hasRole = useAuthStore((s) => s.hasRole);

  async function load() {
    const { data } = await adminApi.get(`/orders/${id}/`);
    setOrder(data);
    setLoading(false);
  }

  async function approve() {
    setApproving(true);
    try {
      await adminApi.post(`/orders/${id}/approve/`);
      toast.success("Buyurtma tasdiqlandi");
      await load();
    } catch {
      toast.error("Tasdiqlashda xatolik yuz berdi");
    } finally {
      setApproving(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function createOrderDetail(payload) {
    await adminApi.post("/order-details/", { ...payload, order: order.id });
    await load();
  }

  async function updateOrderDetail(id, payload) {
    await adminApi.patch(`/order-details/${id}/`, payload);
    await load();
  }

  async function deleteOrderDetail(id) {
    await adminApi.delete(`/order-details/${id}/`);
    await load();
  }

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <Link to="/orders" className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-semibold text-(--accent-strong) hover:text-(--ink)">
        <ArrowLeft size={15} /> Buyurtmalarga qaytish
      </Link>

      <PageHeader
        eyebrow="Buyurtma"
        title={`#${order.order_no}`}
        subtitle={order.product_name}
        actions={
          <div className="flex items-center gap-2">
            {order.status === "draft" && hasRole("super_admin") && (
              <Button size="sm" onClick={approve} loading={approving}>
                <Check size={15} /> Tasdiqlash
              </Button>
            )}
            <Button size="sm" variant="secondary" onClick={() => setEditModalOpen(true)}>
              <Pencil size={15} /> Tahrirlash
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setQrModalOpen(true)}>
              <QrCode size={15} /> QR kodni ko'rish
            </Button>
            <StatusBadge status={order.status} />
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card className="p-5">
          <p className="text-xs text-(--ink-soft) uppercase font-semibold">Mijoz</p>
          <p className="mt-1 font-medium">{order.customer_name || "—"}</p>
          <p className="text-sm text-(--ink-soft)">{order.customer_phone}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-(--ink-soft) uppercase font-semibold">Muddat</p>
          <p className="mt-1 font-medium">{order.deadline ? format(new Date(order.deadline), "dd.MM.yyyy") : "Belgilanmagan"}</p>
        </Card>
        <Card className="p-5 md:col-span-2 xl:col-span-1">
          <p className="text-xs text-(--ink-soft) uppercase font-semibold">Izoh</p>
          <p className="mt-1 text-sm">{order.notes || "—"}</p>
        </Card>
      </div>

      <Card>
        <CardHeader title="Mahsulot detallari" subtitle="Buyurtmaning o'lcham/material ro'yxati — har biri o'ziga xos QR bilan" />
        <CardBody>
          <EditableDetailsTable
            rows={order.details}
            onCreate={createOrderDetail}
            onUpdate={updateOrderDetail}
            onDelete={deleteOrderDetail}
            onShowQr={setQrDetail}
            emptyMessage="Detallar yo'q"
          />
        </CardBody>
      </Card>

      <OrderQRModal open={qrModalOpen} onClose={() => setQrModalOpen(false)} order={order} />
      <EditOrderModal
        open={editModalOpen}
        order={order}
        onClose={() => setEditModalOpen(false)}
        onSaved={load}
      />
      <DetailQRModal detail={qrDetail} order={order} onClose={() => setQrDetail(null)} />
    </div>
  );
}

function OrderQRModal({ open, onClose, order }) {
  const canvasRef = useRef(null);

  function download() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = `buyurtma-${order.order_no}-qr.png`;
    link.click();
  }

  function print() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    const win = window.open("", "_blank", "width=420,height=520");
    if (!win) return;
    win.document.write(
      `<title>QR — ${order.order_no}</title>` +
        `<body style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;gap:12px;">` +
        `<img src="${dataUrl}" style="width:280px;height:280px" onload="window.print()" />` +
        `<p style="font-size:14px;color:#444;">#${order.order_no}</p>` +
        `</body>`
    );
    win.document.close();
  }

  return (
    <Modal open={open} onClose={onClose} title={`Buyurtma QR kodi — #${order.order_no}`} size="sm">
      <div className="flex flex-col items-center gap-4">
        <div className="rounded-2xl border border-(--border-subtle) bg-white p-4">
          <QRCodeCanvas ref={canvasRef} value={order.qr_token} size={200} level="M" />
        </div>
        <p className="max-w-full break-all text-center font-mono text-xs text-(--ink-faint)">{order.qr_token}</p>
        <div className="flex w-full flex-col gap-2 sm:flex-row">
          <Button className="flex-1" variant="secondary" onClick={download}>
            Yuklab olish
          </Button>
          <Button className="flex-1" onClick={print}>
            <Printer size={15} /> Chop etish
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function detailSize(detail) {
  const parts = [detail.length_mm, detail.width_mm, detail.thickness_mm].filter((v) => v !== null && v !== undefined);
  return parts.length ? parts.join("x") : null;
}

function DetailQRModal({ detail, order, onClose }) {
  const canvasRef = useRef(null);

  function download() {
    const canvas = canvasRef.current;
    if (!canvas || !detail) return;
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = `detal-${order.order_no}-${detail.id}-qr.png`;
    link.click();
  }

  function print() {
    const canvas = canvasRef.current;
    if (!canvas || !detail) return;
    const dataUrl = canvas.toDataURL("image/png");
    const win = window.open("", "_blank", "width=420,height=520");
    if (!win) return;
    const size = detailSize(detail);
    win.document.write(
      `<title>QR — ${detail.name}</title>` +
        `<body style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;gap:8px;">` +
        `<img src="${dataUrl}" style="width:280px;height:280px" onload="window.print()" />` +
        `<p style="font-size:14px;font-weight:600;color:#222;">${detail.name}</p>` +
        (size ? `<p style="font-size:13px;color:#444;">${size} mm</p>` : "") +
        `<p style="font-size:13px;color:#444;">#${order.order_no}</p>` +
        `</body>`
    );
    win.document.close();
  }

  if (!detail) return null;
  const size = detailSize(detail);

  return (
    <Modal open={Boolean(detail)} onClose={onClose} title={`Detal QR kodi — ${detail.name}`} size="sm">
      <div className="flex flex-col items-center gap-4">
        <div className="rounded-2xl border border-(--border-subtle) bg-white p-4">
          <QRCodeCanvas ref={canvasRef} value={detail.qr_token} size={200} level="M" />
        </div>
        <div className="text-center">
          <p className="font-medium text-(--ink)">{detail.name}</p>
          {size && <p className="text-sm text-(--ink-soft)">{size} mm</p>}
          <p className="text-sm text-(--ink-soft)">#{order.order_no}</p>
        </div>
        <p className="max-w-full break-all text-center font-mono text-xs text-(--ink-faint)">{detail.qr_token}</p>
        <div className="flex w-full flex-col gap-2 sm:flex-row">
          <Button className="flex-1" variant="secondary" onClick={download}>
            Yuklab olish
          </Button>
          <Button className="flex-1" onClick={print}>
            <Printer size={15} /> Chop etish
          </Button>
        </div>
      </div>
    </Modal>
  );
}
