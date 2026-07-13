import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Plus, Printer } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Field, Input, Select } from "../../components/ui/Input";
import { Checkbox } from "../../components/ui/Checkbox";
import { PageLoader } from "../../components/ui/Misc";
import Badge, { StatusBadge } from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import { format } from "date-fns";

const PART_STATUS_LABELS = { pending: "Kutilmoqda", in_progress: "Jarayonda", completed: "Tayyor", blocked: "Bloklangan", conflict: "Konflikt" };
const ROUTE_TEMPLATE_LABELS = {
  oddiy_panel: "Oddiy panel",
  faqat_kesish: "Faqat kesish",
  cnc: "CNC",
  stolyarka: "Stolyarka",
};

export default function OrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [partModalOpen, setPartModalOpen] = useState(false);

  async function load() {
    const { data } = await adminApi.get(`/orders/${id}/`);
    setOrder(data);
    setSelected((current) => current.filter((partId) => data.parts.some((part) => part.id === partId)));
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function toggle(partId) {
    setSelected((s) => (s.includes(partId) ? s.filter((x) => x !== partId) : [...s, partId]));
  }

  async function printLabels() {
    if (selected.length === 0) return toast.error("Detal tanlanmagan");
    const res = await adminApi.post("/labels/print", { part_ids: selected }, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    window.open(url, "_blank");
  }

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <Link to="/orders" className="focus-ring inline-flex min-h-10 items-center gap-1 rounded-xl text-sm font-semibold text-[var(--accent-strong)] hover:text-[var(--ink)]">
        <ArrowLeft size={15} /> Buyurtmalarga qaytish
      </Link>

      <PageHeader
        eyebrow="Buyurtma"
        title={`#${order.order_no}`}
        subtitle={order.product_name}
        actions={<StatusBadge status={order.status} />}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5">
          <p className="text-xs text-[var(--ink-soft)] uppercase font-semibold">Mijoz</p>
          <p className="mt-1 font-medium">{order.customer_name || "—"}</p>
          <p className="text-sm text-[var(--ink-soft)]">{order.customer_phone}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-[var(--ink-soft)] uppercase font-semibold">Muddat</p>
          <p className="mt-1 font-medium">{order.deadline ? format(new Date(order.deadline), "dd.MM.yyyy") : "Belgilanmagan"}</p>
        </Card>
        <Card className="p-5">
          <p className="text-xs text-[var(--ink-soft)] uppercase font-semibold">Izoh</p>
          <p className="mt-1 text-sm">{order.notes || "—"}</p>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Detallar"
          subtitle={`${order.parts.length} ta detal`}
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="secondary" onClick={printLabels}>
                <Printer size={15} /> Label chop etish ({selected.length})
              </Button>
              <Button size="sm" onClick={() => setPartModalOpen(true)}>
                <Plus size={15} /> Detal qo'shish
              </Button>
            </div>
          }
        />
        <CardBody className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th></Th>
                <Th>Kod</Th>
                <Th>Nomi</Th>
                <Th>Material</Th>
                <Th>O'lcham</Th>
                <Th>Soni</Th>
                <Th>Hozirgi bosqich</Th>
                <Th>Status</Th>
                <Th>Marshrut</Th>
              </tr>
            </Thead>
            <Tbody>
              {order.parts.length === 0 && <EmptyRow colSpan={9} />}
              {order.parts.map((p) => (
                <Tr key={p.id}>
                  <Td>
                    <Checkbox checked={selected.includes(p.id)} onChange={() => toggle(p.id)} />
                  </Td>
                  <Td className="font-mono text-xs">{p.code}</Td>
                  <Td>{p.name}</Td>
                  <Td>{p.material} {p.color && `/ ${p.color}`}</Td>
                  <Td>{p.length_mm}x{p.width_mm}x{p.thickness_mm}</Td>
                  <Td>{p.quantity}</Td>
                  <Td>{p.current_operation_code || "—"}</Td>
                  <Td><StatusBadge status={p.status} labels={PART_STATUS_LABELS} /></Td>
                  <Td>
                    <div className="flex items-center gap-1 flex-wrap">
                      {p.routes.map((r) => (
                        <Badge key={r.id} tone={r.status === "completed" ? "green" : r.status === "blocked" ? "red" : "gray"}>
                          {r.operation_code}
                        </Badge>
                      ))}
                    </div>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>

      <CreatePartModal
        open={partModalOpen}
        orderId={order.id}
        onClose={() => setPartModalOpen(false)}
        onCreated={load}
      />
    </div>
  );
}

function cleanNumber(value) {
  return value === "" ? null : value;
}

function CreatePartModal({ open, orderId, onClose, onCreated }) {
  const initialForm = {
    code: "",
    name: "",
    material: "",
    color: "",
    length_mm: "",
    width_mm: "",
    thickness_mm: "",
    quantity: "1",
    edge_meter: "",
    drilling_count: "0",
    route_key: "oddiy_panel",
  };
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await adminApi.post("/parts/", {
        ...form,
        order: orderId,
        length_mm: cleanNumber(form.length_mm),
        width_mm: cleanNumber(form.width_mm),
        thickness_mm: cleanNumber(form.thickness_mm),
        edge_meter: cleanNumber(form.edge_meter),
        quantity: form.quantity || 1,
        drilling_count: form.drilling_count || 0,
      });
      toast.success("Detal qo'shildi");
      setForm(initialForm);
      await onCreated();
      onClose();
    } catch {
      toast.error("Detal qo'shishda xatolik yuz berdi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Yangi detal">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Kod">
            <Input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          </Field>
          <Field label="Nomi">
            <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Material">
            <Input value={form.material} onChange={(e) => setForm({ ...form, material: e.target.value })} />
          </Field>
          <Field label="Rang">
            <Input value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Uzunlik, mm">
            <Input type="number" step="0.1" min="0" value={form.length_mm} onChange={(e) => setForm({ ...form, length_mm: e.target.value })} />
          </Field>
          <Field label="Eni, mm">
            <Input type="number" step="0.1" min="0" value={form.width_mm} onChange={(e) => setForm({ ...form, width_mm: e.target.value })} />
          </Field>
          <Field label="Qalinlik, mm">
            <Input type="number" step="0.1" min="0" value={form.thickness_mm} onChange={(e) => setForm({ ...form, thickness_mm: e.target.value })} />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Soni">
            <Input type="number" min="1" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          </Field>
          <Field label="Kromka, metr">
            <Input type="number" step="0.01" min="0" value={form.edge_meter} onChange={(e) => setForm({ ...form, edge_meter: e.target.value })} />
          </Field>
          <Field label="Teshiklar">
            <Input type="number" min="0" value={form.drilling_count} onChange={(e) => setForm({ ...form, drilling_count: e.target.value })} />
          </Field>
        </div>

        <Field label="Marshrut">
          <Select value={form.route_key} onChange={(e) => setForm({ ...form, route_key: e.target.value })}>
            {Object.entries(ROUTE_TEMPLATE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </Select>
        </Field>

        <Button type="submit" className="w-full" disabled={saving}>
          {saving ? "Saqlanmoqda..." : "Qo'shish"}
        </Button>
      </form>
    </Modal>
  );
}
