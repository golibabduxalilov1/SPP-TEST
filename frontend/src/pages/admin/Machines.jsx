import { useEffect, useState } from "react";
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
import SegmentedControl from "../../components/ui/SegmentedControl";
import { useTutorial } from "../../tutorial/TutorialContext";
import { machinesSteps } from "../../tutorial/content/machines";

const WS_STATUS_LABELS = { active: "Ishlayapti", inactive: "Noaktiv", maintenance: "Ta'mirda", stopped: "To'xtagan" };
const MACHINE_STATUS_LABELS = { active: "active", inactive: "inactive", maintenance: "maintenance", broken: "broken" };

const TABS = [
  { value: "tsexes", label: "Tsexlar" },
  { value: "workstations", label: "Postlar" },
  { value: "machines", label: "Stanoklar" },
];

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
        className="!min-h-9 !min-w-9 !rounded-lg !border-[var(--border-strong)] !px-0 !text-[var(--accent-strong)] hover:!bg-[var(--accent-soft)]"
      >
        <Pencil size={14} strokeWidth={2.2} />
      </Button>
      <Button
        type="button" variant="ghost" size="sm" magnetic={false}
        onClick={onDelete} aria-label={deleteLabel} title="O'chirish"
        className="!min-h-9 !min-w-9 !rounded-lg !border-[var(--border-strong)] !px-0 !text-status-red hover:!bg-[var(--color-status-red-bg)]"
      >
        <Trash2 size={14} strokeWidth={2.2} />
      </Button>
    </div>
  );
}

export default function Machines() {
  const [tab, setTab] = useState(TABS[0].value);
  const [tsexes, setTsexes] = useState([]);
  const [workstations, setWorkstations] = useState([]);
  const [machines, setMachines] = useState([]);
  const [operations, setOperations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tsexModalOpen, setTsexModalOpen] = useState(false);
  const [editingTsex, setEditingTsex] = useState(null);
  const [deletingTsex, setDeletingTsex] = useState(null);
  const [wsModalOpen, setWsModalOpen] = useState(false);
  const [editingWorkstation, setEditingWorkstation] = useState(null);
  const [deletingWorkstation, setDeletingWorkstation] = useState(null);
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

  async function load() {
    setLoading(true);
    try {
      const [t, w, m, o] = await Promise.all([
        adminApi.get("/tsexes/"),
        adminApi.get("/workstations/"),
        adminApi.get("/machines/"),
        adminApi.get("/operations/"),
      ]);
      setTsexes(t.data.results || t.data);
      setWorkstations(w.data.results || w.data);
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

  function openCreateWsModal() {
    setEditingWorkstation(null);
    setWsModalOpen(true);
  }

  function openEditWsModal(ws) {
    setEditingWorkstation(ws);
    setWsModalOpen(true);
  }

  function closeWsModal() {
    setWsModalOpen(false);
    setEditingWorkstation(null);
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

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Infratuzilma" title="Tsex va stanoklar" subtitle="Bo'linmalar, postlar va stanoklar" />

      <SegmentedControl options={TABS} value={tab} onChange={setTab} />

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

      {tab === "workstations" && (
      <Card>
        <CardHeader
          title="Postlar"
          subtitle={`${workstations.length} ta post`}
          actions={<Button data-tutorial="machines-add-workstation" size="sm" onClick={openCreateWsModal}><Plus size={15} /> Post qo'shish</Button>}
        />
        <CardBody data-tutorial="machines-workstations-table" className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>Nomi</Th>
                <Th>Tsex</Th>
                <Th>Bosqich</Th>
                <Th>Status</Th>
                <Th className="text-right">Amallar</Th>
              </tr>
            </Thead>
            <Tbody>
              {workstations.length === 0 && <EmptyRow colSpan={5} />}
              {workstations.map((w) => (
                <Tr key={w.id}>
                  <Td className="font-medium">{w.name}</Td>
                  <Td>{w.tsex_name}</Td>
                  <Td>{w.operation_name}</Td>
                  <Td><StatusBadge status={w.status} labels={WS_STATUS_LABELS} /></Td>
                  <Td className="whitespace-nowrap">
                    <RowActions
                      onEdit={() => openEditWsModal(w)}
                      onDelete={() => setDeletingWorkstation(w)}
                      editLabel={`${w.name} postini tahrirlash`}
                      deleteLabel={`${w.name} postini o'chirish`}
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
          title="Stanoklar"
          subtitle={`${machines.length} ta stanok`}
          actions={<Button data-tutorial="machines-add-machine" size="sm" onClick={openCreateMachineModal}><Plus size={15} /> Stanok qo'shish</Button>}
        />
        <CardBody data-tutorial="machines-machines-table" className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>ID</Th>
                <Th>Nomi</Th>
                <Th>Bosqich</Th>
                <Th>Post</Th>
                <Th>Quvvat/soat</Th>
                <Th>Status</Th>
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
                  <Td>{m.workstation_name}</Td>
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
      <WorkstationModal
        open={wsModalOpen}
        workstation={editingWorkstation}
        onClose={closeWsModal}
        tsexes={tsexes}
        operations={operations}
        onSaved={load}
      />
      <DeleteWorkstationModal workstation={deletingWorkstation} onClose={() => setDeletingWorkstation(null)} onDeleted={load} />
      <MachineModal
        open={machineModalOpen}
        machine={editingMachine}
        onClose={closeMachineModal}
        workstations={workstations}
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
      <p className="text-sm leading-6 text-[var(--ink-soft)]">
        <strong className="font-semibold text-[var(--ink)]">{tsex?.name}</strong> tsexini o'chirmoqchimisiz?
        Bu tsexga bog'liq postlar bo'lsa, o'chirish rad etilishi mumkin.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}

function WorkstationModal({ open, workstation, onClose, tsexes, operations, onSaved }) {
  const emptyForm = { name: "", tsex: "", operation: "", status: "active" };
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const isEditing = Boolean(workstation);

  useEffect(() => {
    if (!open) return;
    setForm(workstation ? {
      name: workstation.name || "",
      tsex: workstation.tsex || "",
      operation: workstation.operation || "",
      status: workstation.status || "active",
    } : emptyForm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workstation, open]);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (isEditing) {
        await adminApi.patch(`/workstations/${workstation.id}/`, form);
        toast.success("Post ma'lumotlari yangilandi");
      } else {
        await adminApi.post("/workstations/", form);
        toast.success("Post yaratildi");
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
    <Modal open={open} onClose={onClose} title={isEditing ? "Postni tahrirlash" : "Yangi post"}>
      <form onSubmit={submit} className="space-y-4">
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
        <Field label="Status">
          <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {Object.entries(WS_STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </Field>
        <Button type="submit" loading={submitting} className="w-full">
          {isEditing ? "Saqlash" : "Yaratish"}
        </Button>
      </form>
    </Modal>
  );
}

function DeleteWorkstationModal({ workstation, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/workstations/${workstation.id}/`);
      toast.success("Post o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(workstation)} onClose={onClose} title="Postni o'chirish" size="sm">
      <p className="text-sm leading-6 text-[var(--ink-soft)]">
        <strong className="font-semibold text-[var(--ink)]">{workstation?.name}</strong> postini o'chirmoqchimisiz?
        Bu postga bog'liq stanoklar bo'lsa, o'chirish rad etilishi mumkin.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}

function MachineModal({ open, machine, onClose, workstations, operations, onSaved }) {
  const emptyForm = { machine_id: "", name: "", workstation: "", operation: "", capacity_per_hour: "", status: "active" };
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const isEditing = Boolean(machine);

  useEffect(() => {
    if (!open) return;
    setForm(machine ? {
      machine_id: machine.machine_id || "",
      name: machine.name || "",
      workstation: machine.workstation || "",
      operation: machine.operation || "",
      capacity_per_hour: machine.capacity_per_hour ?? "",
      status: machine.status || "active",
    } : emptyForm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [machine, open]);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = { ...form, capacity_per_hour: form.capacity_per_hour || null };
      if (isEditing) {
        await adminApi.patch(`/machines/${machine.id}/`, payload);
        toast.success("Stanok ma'lumotlari yangilandi");
      } else {
        await adminApi.post("/machines/", payload);
        toast.success("Stanok yaratildi");
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
    <Modal open={open} onClose={onClose} title={isEditing ? "Stanokni tahrirlash" : "Yangi stanok"}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Stanok ID">
          <Input required value={form.machine_id} onChange={(e) => setForm({ ...form, machine_id: e.target.value })} />
        </Field>
        <Field label="Nomi">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Post">
          <Select required value={form.workstation} onChange={(e) => setForm({ ...form, workstation: e.target.value })}>
            <option value="">Tanlang</option>
            {workstations.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </Select>
        </Field>
        <Field label="Bosqich">
          <Select required value={form.operation} onChange={(e) => setForm({ ...form, operation: e.target.value })}>
            <option value="">Tanlang</option>
            {operations.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
          </Select>
        </Field>
        <Field label="Status">
          <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {Object.entries(MACHINE_STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </Field>
        <Field label="Quvvat (soatiga)" hint="Ixtiyoriy — dashboarddagi samaradorlik hisobi uchun">
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
      toast.success("Stanok o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(machine)} onClose={onClose} title="Stanokni o'chirish" size="sm">
      <p className="text-sm leading-6 text-[var(--ink-soft)]">
        <strong className="font-semibold text-[var(--ink)]">{machine?.name}</strong> stanogini o'chirmoqchimisiz?
        Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}
