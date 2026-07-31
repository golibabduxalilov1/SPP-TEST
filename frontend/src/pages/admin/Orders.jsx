import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, Download, ExternalLink, FileSpreadsheet, FileText, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { useAuthStore } from "../../store/authStore";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Input, Select } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import Badge from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import EditOrderModal from "../../components/admin/EditOrderModal";
import GibLabImportModal from "../../components/admin/GibLabImportModal";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { ordersSteps } from "../../tutorial/content/orders";

const LIFECYCLE_STATUS_TONES = { draft: "blue", approved: "blue", delivered: "green", cancelled: "red" };
const STAGE_STATUS_TONE = "yellow";

function orderStatusTone(displayStatus) {
  if (!displayStatus || !displayStatus.value) return "gray";
  return LIFECYCLE_STATUS_TONES[displayStatus.value] || STAGE_STATUS_TONE;
}

// Status filter values are namespaced so lifecycle statuses and dynamic
// production stages can share one dropdown/query param without colliding.
function parseStatusFilter(value) {
  if (!value) return {};
  if (value.startsWith("status:")) return { status: value.slice("status:".length) };
  if (value.startsWith("stage:")) return { production_stage: value.slice("stage:".length) };
  return {};
}

const PRIORITY_LABELS = { normal: "Oddiy", high: "Yuqori", urgent: "Shoshilinch" };
const PRIORITY_TONES = { normal: "gray", high: "orange", urgent: "red" };

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [operations, setOperations] = useState([]);
  const [exportOpen, setExportOpen] = useState(false);
  const [giblabImportOpen, setGiblabImportOpen] = useState(false);
  const [deletingOrder, setDeletingOrder] = useState(null);
  const [editingOrder, setEditingOrder] = useState(null);
  const [approvingId, setApprovingId] = useState(null);
  const navigate = useNavigate();
  const { registerAndAutoStart } = useTutorial();
  const hasRole = useAuthStore((s) => s.hasRole);

  useEffect(() => registerAndAutoStart("orders", ordersSteps), [registerAndAutoStart]);

  useEffect(() => {
    adminApi.get("/operations/", { params: { is_active: true } }).then(({ data }) => {
      setOperations(data.results || data);
    });
  }, []);

  async function load() {
    setLoading(true);
    const { status, production_stage } = parseStatusFilter(statusFilter);
    const { data } = await adminApi.get("/orders/", {
      params: { search: search || undefined, status, production_stage },
    });
    setOrders(data.results || data);
    setLoading(false);
  }

  async function approve(order) {
    setApprovingId(order.id);
    try {
      await adminApi.post(`/orders/${order.id}/approve/`);
      toast.success(`#${order.order_no} tasdiqlandi`);
      await load();
    } catch {
      toast.error("Tasdiqlashda xatolik yuz berdi");
    } finally {
      setApprovingId(null);
    }
  }

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFilter]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Buyurtmalar"
        title="Buyurtmalar"
        subtitle="Barcha buyurtmalar va ularning ishlab chiqarish holati"
        actions={
          <>
            <Button data-tutorial="orders-import-button" variant="secondary" onClick={() => setExportOpen(true)}>
              <Download size={16} /> Yuklab olish
            </Button>
            {hasRole("admin", "director", "manager") && (
              <Button variant="secondary" onClick={() => setGiblabImportOpen(true)}>
                <Upload size={16} /> GibLab import
              </Button>
            )}
            <Button data-tutorial="orders-new-button" onClick={() => navigate("/orders/new")}>
              <Plus size={16} /> Yangi buyurtma
            </Button>
          </>
        }
      />

      <Card>
        <CardHeader
          title="Ro'yxat"
          actions={
            <div data-tutorial="orders-filters" className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
              <div className="relative w-full sm:w-auto">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-(--ink-soft)" />
                <Input className="pl-8 w-full sm:w-56" placeholder="Qidirish..." value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <Select
                containerClassName="w-full sm:w-auto"
                className="w-full sm:w-44"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">Barcha statuslar</option>
                <option value="status:draft">Yangi</option>
                <option value="status:approved">Tasdiqlangan</option>
                {operations.map((op) => (
                  <option key={op.id} value={`stage:${op.id}`}>{op.name}</option>
                ))}
                <option value="status:delivered">Topshirildi</option>
                <option value="status:cancelled">Bekor qilingan</option>
              </Select>
            </div>
          }
        />
        <CardBody data-tutorial="orders-table" className="p-0">
          {loading ? (
            <PageLoader />
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th>Mahsulot turi</Th>
                  <Th>Mijoz</Th>
                  <Th>Muddat</Th>
                  <Th>Prioritet</Th>
                  <Th>Mahsulot soni</Th>
                  <Th>Detallar</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Amallar</Th>
                </tr>
              </Thead>
              <Tbody>
                {orders.length === 0 && <EmptyRow colSpan={8} />}
                {orders.map((o) => (
                  <Tr key={o.id}>
                    <Td>
                      <p
                        className="max-w-50 truncate font-semibold"
                        title={o.product_type_name || o.product_name || "Mahsulot ko'rsatilmagan"}
                      >
                        {o.product_type_name || o.product_name || "Mahsulot ko'rsatilmagan"}
                      </p>
                    </Td>
                    <Td>{o.customer_name || "—"}</Td>
                    <Td>{o.deadline ? format(new Date(o.deadline), "dd.MM.yyyy") : "—"}</Td>
                    <Td>
                      <Badge tone={PRIORITY_TONES[o.priority]}>{PRIORITY_LABELS[o.priority]}</Badge>
                    </Td>
                    <Td>{o.product_quantity} dona</Td>
                    <Td>
                      {o.parts_completed}/{o.parts_total}
                    </Td>
                    <Td>
                      <Badge tone={orderStatusTone(o.display_status)} dot>
                        {o.display_status?.label ?? "—"}
                      </Badge>
                    </Td>
                    <Td>
                      <div className="ml-auto flex w-fit items-center gap-1.5">
                        {o.status === "draft" && hasRole("super_admin") && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            magnetic={false}
                            onClick={() => approve(o)}
                            loading={approvingId === o.id}
                            aria-label={`#${o.order_no} buyurtmasini tasdiqlash`}
                            title="Tasdiqlash"
                            className="min-h-9! min-w-9! rounded-lg! border! border-(--border-strong)! px-0! text-status-green! hover:bg-status-green-bg!"
                          >
                            <Check size={14} strokeWidth={2.2} />
                          </Button>
                        )}
                        <Button
                          as={Link}
                          to={`/orders/${o.id}`}
                          variant="ghost"
                          size="sm"
                          magnetic={false}
                          aria-label={`#${o.order_no} buyurtmasini ochish`}
                          title="Batafsil"
                          className="min-h-9! min-w-9! rounded-lg! border! border-(--border-strong)! px-0! text-(--ink-soft)! hover:bg-(--surface-muted)! hover:text-(--ink)!"
                        >
                          <ExternalLink size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          magnetic={false}
                          onClick={() => setEditingOrder(o)}
                          aria-label={`#${o.order_no} buyurtmasini tahrirlash`}
                          title="Tahrirlash"
                          className="min-h-9! min-w-9! rounded-lg! border! border-(--border-strong)! px-0! text-(--ink-soft)! hover:bg-(--surface-muted)! hover:text-(--ink)!"
                        >
                          <Pencil size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          magnetic={false}
                          onClick={() => setDeletingOrder(o)}
                          aria-label={`#${o.order_no} buyurtmasini o'chirish`}
                          title="O'chirish"
                          className="min-h-9! min-w-9! rounded-lg! border! border-(--border-strong)! px-0! text-status-red! hover:bg-status-red-bg!"
                        >
                          <Trash2 size={14} strokeWidth={2.2} />
                        </Button>
                      </div>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <ExportModal open={exportOpen} onClose={() => setExportOpen(false)} search={search} statusFilter={statusFilter} />
      <GibLabImportModal open={giblabImportOpen} onClose={() => setGiblabImportOpen(false)} onImported={load} />
      <DeleteOrderModal order={deletingOrder} onClose={() => setDeletingOrder(null)} onDeleted={load} />
      <EditOrderModal
        open={Boolean(editingOrder)}
        order={editingOrder}
        onClose={() => setEditingOrder(null)}
        onSaved={load}
      />
    </div>
  );
}

function DeleteOrderModal({ order, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/orders/${order.id}/`);
      toast.success("Buyurtma o'chirildi");
      await onDeleted();
      onClose();
    } catch {
      toast.error("Xatolik yuz berdi");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(order)} onClose={onClose} title="Buyurtmani o'chirish" size="sm">
      <p className="text-sm leading-6 text-(--ink-soft)">
        <strong className="font-semibold text-(--ink)">#{order?.order_no}</strong> buyurtmasini o'chirmoqchimisiz?
        Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}

function ExportModal({ open, onClose, search, statusFilter }) {
  const [downloading, setDownloading] = useState(null);

  async function download(fmt) {
    setDownloading(fmt);
    try {
      const { status, production_stage } = parseStatusFilter(statusFilter);
      const response = await adminApi.get("/orders/export/", {
        params: { file_type: fmt, search: search || undefined, status, production_stage },
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = fmt === "excel" ? "buyurtmalar.xlsx" : "buyurtmalar.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      onClose();
    } catch {
      toast.error("Yuklab olishda xatolik");
    } finally {
      setDownloading(null);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Yuklab olish" size="sm">
      <p className="mb-4 text-sm text-(--ink-soft)">Buyurtmalar ro'yxatini qaysi ko'rinishda yuklab olasiz?</p>
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => download("pdf")}
          disabled={downloading !== null}
          className="focus-ring flex flex-col items-center gap-2 rounded-xl border border-(--border-strong) bg-(--surface) px-4 py-5 text-sm font-semibold text-(--ink) transition-colors duration-200 hover:border-(--accent) hover:bg-(--accent-soft) disabled:pointer-events-none disabled:opacity-50"
        >
          <FileText size={22} className="text-status-red" />
          {downloading === "pdf" ? "Tayyorlanmoqda..." : "PDF"}
        </button>
        <button
          type="button"
          onClick={() => download("excel")}
          disabled={downloading !== null}
          className="focus-ring flex flex-col items-center gap-2 rounded-xl border border-(--border-strong) bg-(--surface) px-4 py-5 text-sm font-semibold text-(--ink) transition-colors duration-200 hover:border-(--accent) hover:bg-(--accent-soft) disabled:pointer-events-none disabled:opacity-50"
        >
          <FileSpreadsheet size={22} className="text-status-green" />
          {downloading === "excel" ? "Tayyorlanmoqda..." : "Excel"}
        </button>
      </div>
    </Modal>
  );
}
