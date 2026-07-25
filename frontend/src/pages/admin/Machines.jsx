import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Field, Input, Select } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import Badge, { StatusBadge } from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import { useTutorial } from "../../tutorial/TutorialContext";
import { machinesSteps } from "../../tutorial/content/machines";
import { measureUnitLabel } from "../../lib/units";

const MACHINE_STATUS_LABELS = { active: "Faol", inactive: "Nofaol", maintenance: "Ta'mirda", broken: "Buzilgan" };

const TABS = [
  { value: "tsexes", label: "Tsexlar" },
  { value: "machines", label: "Dastgohlar" },
];

const TAB_HEADERS = {
  tsexes: { eyebrow: "Infratuzilma", title: "Tsexlar", subtitle: "Ishlab chiqarish bo'linmalari" },
  machines: { eyebrow: "Infratuzilma", title: "Stanoklar", subtitle: "Tsexlardagi dastgohlar ro'yxati" },
};

function getErrorMessage(error) {
  const data = error.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const firstError = Object.values(data).flat()[0];
    if (typeof firstError === "string") return firstError;
  }
  return "Xatolik yuz berdi";
}

function RowActions({ onEdit, onDelete, editLabel, deleteLabel }) {
  return (
    <div className="ml-auto flex w-fit items-center gap-1.5">
      <Button
        type="button" variant="ghost" size="sm" magnetic={false}
        onClick={onEdit} aria-label={editLabel} title="Tahrirlash"
        className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
      >
        <Pencil size={14} strokeWidth={2.2} />
      </Button>
      <Button
        type="button" variant="ghost" size="sm" magnetic={false}
        onClick={onDelete} aria-label={deleteLabel} title="O'chirish"
        className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-status-red! hover:bg-(--color-status-red-bg)!"
      >
        <Trash2 size={14} strokeWidth={2.2} />
      </Button>
    </div>
  );
}

export default function Machines() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(() => searchParams.get("tab") || TABS[0].value);
  const [tsexes, setTsexes] = useState([]);
  const [machines, setMachines] = useState([]);
  const [operations, setOperations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tsexModalOpen, setTsexModalOpen] = useState(false);
  const [editingTsex, setEditingTsex] = useState(null);
  const [deletingTsex, setDeletingTsex] = useState(null);
  const [machineModalOpen, setMachineModalOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState(null);
  const [deletingMachine, setDeletingMachine] = useState(null);
  const { registerAndAutoStart, isActive, pageKey, steps, stepIndex } = useTutorial();

  useEffect(() => registerAndAutoStart("machines", machinesSteps), [registerAndAutoStart]);

  useEffect(() => {
    if (!isActive || pageKey !== "machines") return;
    const step = steps[stepIndex];
    if (step?.tab) setTab(step.tab);
  }, [isActive, pageKey, steps, stepIndex]);

  useEffect(() => {
    const requestedTab = searchParams.get("tab");
    if (requestedTab && requestedTab !== tab) setTab(requestedTab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  async function load() {
    setLoading(true);
    try {
      const [t, m, o] = await Promise.all([
        adminApi.get("/tsexes/"),
        adminApi.get("/machines/"),
        adminApi.get("/operations/", { params: { is_active: true } }),
      ]);
      setTsexes(t.data.results || t.data);
      setMachines(m.data.results || m.data);
      setOperations(o.data.results || o.data);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openCreateTsexModal() {
    setEditingTsex(null);
    setTsexModalOpen(true);
  }

  function openEditTsexModal(tsex) {
    setEditingTsex(tsex);
    setTsexModalOpen(true);
  }

  function closeTsexModal() {
    setTsexModalOpen(false);
    setEditingTsex(null);
  }

  function openCreateMachineModal() {
    setEditingMachine(null);
    setMachineModalOpen(true);
  }

  function openEditMachineModal(machine) {
    setEditingMachine(machine);
    setMachineModalOpen(true);
  }

  function closeMachineModal() {
    setMachineModalOpen(false);
    setEditingMachine(null);
  }

  if (loading) return <PageLoader />;

  const header = TAB_HEADERS[tab] || TAB_HEADERS.tsexes;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow={header.eyebrow} title={header.title} subtitle={header.subtitle} />

      {tab === "tsexes" && (
      <Card>
        <CardHeader
          title="Tsexlar"
          subtitle={`${tsexes.length} ta tsex`}
          actions={<Button size="sm" onClick={openCreateTsexModal}><Plus size={15} /> Tsex qo'shish</Button>}
        />
        <CardBody className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>Nomi</Th>
                <Th>Holat</Th>
                <Th className="text-right">Amallar</Th>
              </tr>
            </Thead>
            <Tbody>
              {tsexes.length === 0 && <EmptyRow colSpan={3} />}
              {tsexes.map((t) => (
                <Tr key={t.id}>
                  <Td className="font-medium">{t.name}</Td>
                  <Td>
                    <Badge tone={t.is_active ? "green" : "gray"}>{t.is_active ? "Aktiv" : "Noaktiv"}</Badge>
                  </Td>
                  <Td className="whitespace-nowrap">
                    <RowActions
                      onEdit={() => openEditTsexModal(t)}
                      onDelete={() => setDeletingTsex(t)}
                      editLabel={`${t.name} tsexini tahrirlash`}
                      deleteLabel={`${t.name} tsexini o'chirish`}
                    />
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>
      )}

      {tab === "machines" && (
      <Card>
        <CardHeader
          title="Dastgohlar"
          subtitle={`${machines.length} ta dastgoh`}
          actions={<Button data-tutorial="machines-add-machine" size="sm" onClick={openCreateMachineModal}><Plus size={15} /> Dastgoh qo'shish</Button>}
        />
        <CardBody data-tutorial="machines-machines-table" className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>ID</Th>
                <Th>Nomi</Th>
                <Th>Bosqich</Th>
                <Th>Tsex</Th>
                <Th>Quvvat/soat</Th>
                <Th>Holat</Th>
                <Th className="text-right">Amallar</Th>
              </tr>
            </Thead>
            <Tbody>
              {machines.length === 0 && <EmptyRow colSpan={7} />}
              {machines.map((m) => (
                <Tr key={m.id}>
                  <Td className="font-mono text-xs">{m.machine_id}</Td>
                  <Td className="font-medium">{m.name}</Td>
                  <Td>{m.operation_name}</Td>
                  <Td>{m.tsex_name}</Td>
                  <Td>{m.capacity_per_hour ?? "—"}</Td>
                  <Td><StatusBadge status={m.status} labels={MACHINE_STATUS_LABELS} /></Td>
                  <Td className="whitespace-nowrap">
                    <RowActions
                      onEdit={() => openEditMachineModal(m)}
                      onDelete={() => setDeletingMachine(m)}
                      editLabel={`${m.name} stanogini tahrirlash`}
                      deleteLabel={`${m.name} stanogini o'chirish`}
                    />
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>
      )}

      <TsexModal
        open={tsexModalOpen}
        tsex={editingTsex}
        onClose={closeTsexModal}
        onSaved={load}
      />
      <DeleteTsexModal tsex={deletingTsex} onClose={() => setDeletingTsex(null)} onDeleted={load} />
      <MachineModal
        open={machineModalOpen}
        machine={editingMachine}
        onClose={closeMachineModal}
        tsexes={tsexes}
        operations={operations}
        onSaved={load}
      />
      <DeleteMachineModal machine={deletingMachine} onClose={() => setDeletingMachine(null)} onDeleted={load} />
    </div>
  );
}

function TsexModal({ open, tsex, onClose, onSaved }) {
  const [form, setForm] = useState({ name: "", is_active: true });
  const [submitting, setSubmitting] = useState(false);
  const isEditing = Boolean(tsex);

  useEffect(() => {
    if (!open) return;
    setForm(tsex ? {
      name: tsex.name || "",
      is_active: tsex.is_active,
    } : { name: "", is_active: true });
  }, [tsex, open]);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (isEditing) {
        await adminApi.patch(`/tsexes/${tsex.id}/`, form);
        toast.success("Tsex ma'lumotlari yangilandi");
      } else {
        await adminApi.post("/tsexes/", form);
        toast.success("Tsex yaratildi");
      }
      await onSaved();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={isEditing ? "Tsexni tahrirlash" : "Yangi tsex"}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nomi" required>
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Holat">
          <Select
            value={String(form.is_active)}
            onChange={(e) => setForm({ ...form, is_active: e.target.value === "true" })}
          >
            <option value="true">Aktiv</option>
            <option value="false">Noaktiv</option>
          </Select>
        </Field>
        <Button type="submit" loading={submitting} className="w-full">
          {isEditing ? "Saqlash" : "Yaratish"}
        </Button>
      </form>
    </Modal>
  );
}

function DeleteTsexModal({ tsex, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/tsexes/${tsex.id}/`);
      toast.success("Tsex o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(tsex)} onClose={onClose} title="Tsexni o'chirish" size="sm">
      <p className="text-sm leading-6 text-(--ink-soft)">
        <strong className="font-semibold text-(--ink)">{tsex?.name}</strong> tsexini o'chirmoqchimisiz?
        Bu tsexga bog'liq dastgohlar bo'lsa, o'chirish rad etilishi mumkin.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}

function MachineModal({ open, machine, onClose, tsexes, operations, onSaved }) {
  const emptyForm = { machine_id: "", name: "", tsex: "", operation: "", capacity_per_hour: "", status: "active" };
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const isEditing = Boolean(machine);

  useEffect(() => {
    if (!open) return;
    setForm(machine ? {
      machine_id: machine.machine_id || "",
      name: machine.name || "",
      tsex: machine.tsex || "",
      operation: machine.operation || "",
      capacity_per_hour: machine.capacity_per_hour ?? "",
      status: machine.status || "active",
    } : emptyForm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machine, open]);

  const selectedOperation = operations.find((o) => String(o.id) === String(form.operation));
  const capacityLabel = selectedOperation
    ? `Quvvat (${measureUnitLabel(selectedOperation.measure_unit)}/soat)`
    : "Quvvat (soatiga)";

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = { ...form, capacity_per_hour: form.capacity_per_hour || null };
      if (isEditing) {
        await adminApi.patch(`/machines/${machine.id}/`, payload);
        toast.success("Dastgoh ma'lumotlari yangilandi");
      } else {
        await adminApi.post("/machines/", payload);
        toast.success("Dastgoh yaratildi");
      }
      await onSaved();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={isEditing ? "Dastgohni tahrirlash" : "Yangi dastgoh"}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Dastgoh ID">
          <Input required value={form.machine_id} onChange={(e) => setForm({ ...form, machine_id: e.target.value })} />
        </Field>
        <Field label="Nomi">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Tsex">
          <Select required value={form.tsex} onChange={(e) => setForm({ ...form, tsex: e.target.value })}>
            <option value="">Tanlang</option>
            {tsexes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </Select>
        </Field>
        <Field label="Bosqich">
          <Select required value={form.operation} onChange={(e) => setForm({ ...form, operation: e.target.value })}>
            <option value="">Tanlang</option>
            {operations.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </Select>
        </Field>
        <Field label="Holat">
          <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {Object.entries(MACHINE_STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </Field>
        <Field label={capacityLabel} hint="Ixtiyoriy — dashboarddagi samaradorlik hisobi uchun">
          <Input
            type="number"
            step="0.01"
            min="0"
            value={form.capacity_per_hour}
            onChange={(e) => setForm({ ...form, capacity_per_hour: e.target.value })}
          />
        </Field>
        <Button type="submit" loading={submitting} className="w-full">
          {isEditing ? "Saqlash" : "Yaratish"}
        </Button>
      </form>
    </Modal>
  );
}

function DeleteMachineModal({ machine, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/machines/${machine.id}/`);
      toast.success("Dastgoh o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(machine)} onClose={onClose} title="Dastgohni o'chirish" size="sm">
      <p className="text-sm leading-6 text-(--ink-soft)">
        <strong className="font-semibold text-(--ink)">{machine?.name}</strong> stanogini o'chirmoqchimisiz?
        Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}
