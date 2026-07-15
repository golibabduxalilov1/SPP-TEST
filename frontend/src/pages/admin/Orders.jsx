import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, Upload } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Input, Select, Field } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import { StatusBadge } from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import { format } from "date-fns";
import { useTutorial } from "../../tutorial/TutorialContext";
import { ordersSteps } from "../../tutorial/content/orders";

const STATUS_LABELS = {
  draft: "Yangi", approved: "Tasdiqlangan", in_production: "Jarayonda", partially_ready: "Qisman tayyor",
  ready_for_packaging: "Qadoqlashga tayyor", packaging: "Qadoqlanmoqda", warehouse: "Omborda",
  delivered: "Topshirildi", cancelled: "Bekor qilingan",
};

const PRIORITY_LABELS = { low: "Past", normal: "Oddiy", high: "Yuqori", urgent: "Shoshilinch" };

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("orders", ordersSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
    const { data } = await adminApi.get("/orders/", { params: { search: search || undefined, status: status || undefined } });
    setOrders(data.results || data);
    setLoading(false);
  }

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, status]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Buyurtmalar"
        title="Buyurtmalar"
        subtitle="Barcha buyurtmalar va ularning ishlab chiqarish holati"
        actions={
          <>
            <Button data-tutorial="orders-import-button" variant="secondary" onClick={() => setImportOpen(true)}>
              <Upload size={16} /> Import
            </Button>
            <Button data-tutorial="orders-new-button" onClick={() => setCreateOpen(true)}>
              <Plus size={16} /> Yangi buyurtma
            </Button>
          </>
        }
      />

      <Card>
        <CardHeader
          title="Ro'yxat"
          actions={
            <div data-tutorial="orders-filters" className="flex items-center gap-2 flex-wrap">
              <div className="relative w-full sm:w-auto">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-soft)]" />
                <Input className="pl-8 w-full sm:w-56" placeholder="Qidirish..." value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <Select className="w-full sm:w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">Barcha statuslar</option>
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
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
                  <Th>Buyurtma</Th>
                  <Th>Mijoz</Th>
                  <Th>Muddat</Th>
                  <Th>Prioritet</Th>
                  <Th>Detallar</Th>
                  <Th>Status</Th>
                  <Th></Th>
                </tr>
              </Thead>
              <Tbody>
                {orders.length === 0 && <EmptyRow colSpan={7} />}
                {orders.map((o) => (
                  <Tr key={o.id}>
                    <Td>
                      <p className="font-semibold">#{o.order_no}</p>
                      <p className="text-xs text-[var(--ink-faint)]">{o.product_name}</p>
                    </Td>
                    <Td>{o.customer_name || "—"}</Td>
                    <Td>{o.deadline ? format(new Date(o.deadline), "dd.MM.yyyy") : "—"}</Td>
                    <Td>{PRIORITY_LABELS[o.priority]}</Td>
                    <Td>
                      {o.parts_completed}/{o.parts_total}
                    </Td>
                    <Td>
                      <StatusBadge status={o.status} labels={STATUS_LABELS} />
                    </Td>
                    <Td>
                      <Link to={`/orders/${o.id}`} className="focus-ring rounded-md text-sm font-semibold text-[var(--accent-strong)] hover:underline">
                        Batafsil
                      </Link>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <CreateOrderModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={load} />
      <ImportModal open={importOpen} onClose={() => setImportOpen(false)} onImported={load} />
    </div>
  );
}

function CreateOrderModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({ customer_name: "", customer_phone: "", product_name: "", deadline: "", priority: "normal", notes: "" });
  const [saving, setSaving] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await adminApi.post("/orders/", { ...form, deadline: form.deadline || null });
      toast.success("Buyurtma yaratildi");
      onCreated();
      onClose();
      setForm({ customer_name: "", customer_phone: "", product_name: "", deadline: "", priority: "normal", notes: "" });
    } catch {
      toast.error("Xatolik yuz berdi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Yangi buyurtma">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Mahsulot nomi">
          <Input required value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
        </Field>
        <Field label="Mijoz nomi">
          <Input value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} />
        </Field>
        <Field label="Mijoz telefoni">
          <Input value={form.customer_phone} onChange={(e) => setForm({ ...form, customer_phone: e.target.value })} />
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Muddat">
            <Input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          </Field>
          <Field label="Prioritet">
            <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              {Object.entries(PRIORITY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Izoh">
          <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </Field>
        <Button type="submit" className="w-full" disabled={saving} loading={saving}>
          Yaratish
        </Button>
      </form>
    </Modal>
  );
}

function ImportModal({ open, onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await adminApi.post("/orders/import_file/", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data);
      onImported();
      toast.success(`${data.parts_created} ta detal import qilindi`);
    } catch {
      toast.error("Import muvaffaqiyatsiz");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={() => { onClose(); setResult(null); }} title="Excel/CSV import">
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-[var(--ink-soft)]">
          Ustunlar: order, product, part_code, part_name, length_mm, width_mm, thickness_mm, quantity, material,
          edge_meter, drilling_count, route (oddiy_panel / faqat_kesish / cnc / stolyarka)
        </p>
        <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface)] px-4 py-3.5 text-sm shadow-[inset_0_1px_2px_rgba(28,26,22,0.05)] transition-colors duration-200 hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]">
          <Upload size={16} className="shrink-0 text-[var(--ink-soft)]" />
          <span className="truncate text-[var(--ink-soft)]">
            {file ? file.name : "Excel yoki CSV faylni tanlang"}
          </span>
          <input type="file" accept=".xlsx,.csv" onChange={(e) => setFile(e.target.files[0])} className="sr-only" />
        </label>
        <Button type="submit" disabled={loading || !file} loading={loading} className="w-full">
          Import qilish
        </Button>
        {result && (
          <div className="text-sm bg-[var(--surface-muted)] border border-[var(--border-subtle)] rounded-lg p-3">
            <p>Yaratilgan detallar: {result.parts_created}</p>
            <p>Buyurtmalar: {result.orders_affected.join(", ")}</p>
            {result.errors.length > 0 && (
              <div className="mt-2 text-status-red">
                {result.errors.map((e, i) => (
                  <p key={i}>Qator {e.row}: {e.error}</p>
                ))}
              </div>
            )}
          </div>
        )}
      </form>
    </Modal>
  );
}
