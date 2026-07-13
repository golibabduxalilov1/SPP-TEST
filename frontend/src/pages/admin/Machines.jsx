import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Field, Input, Select } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import { StatusBadge } from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import { useTutorial } from "../../tutorial/TutorialContext";
import { machinesSteps } from "../../tutorial/content/machines";

const WS_STATUS_LABELS = { active: "Ishlayapti", inactive: "Noaktiv", maintenance: "Ta'mirda", stopped: "To'xtagan" };
const MACHINE_STATUS_LABELS = { active: "active", inactive: "inactive", maintenance: "maintenance", broken: "broken" };

export default function Machines() {
  const [tsexes, setTsexes] = useState([]);
  const [workstations, setWorkstations] = useState([]);
  const [machines, setMachines] = useState([]);
  const [operations, setOperations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wsModalOpen, setWsModalOpen] = useState(false);
  const [machineModalOpen, setMachineModalOpen] = useState(false);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("machines", machinesSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
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
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Infratuzilma" title="Tsex va stanoklar" subtitle="Postlar, stanoklar va ularning holati" />

      <Card>
        <CardHeader
          title="Postlar"
          subtitle={`${workstations.length} ta post`}
          actions={<Button data-tutorial="machines-add-workstation" size="sm" onClick={() => setWsModalOpen(true)}><Plus size={15} /> Post qo'shish</Button>}
        />
        <CardBody data-tutorial="machines-workstations-table" className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>Nomi</Th>
                <Th>Tsex</Th>
                <Th>Bosqich</Th>
                <Th>Status</Th>
              </tr>
            </Thead>
            <Tbody>
              {workstations.length === 0 && <EmptyRow colSpan={4} />}
              {workstations.map((w) => (
                <Tr key={w.id}>
                  <Td className="font-medium">{w.name}</Td>
                  <Td>{w.tsex_name}</Td>
                  <Td>{w.operation_name}</Td>
                  <Td><StatusBadge status={w.status} labels={WS_STATUS_LABELS} /></Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Stanoklar"
          subtitle={`${machines.length} ta stanok`}
          actions={<Button data-tutorial="machines-add-machine" size="sm" onClick={() => setMachineModalOpen(true)}><Plus size={15} /> Stanok qo'shish</Button>}
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
              </tr>
            </Thead>
            <Tbody>
              {machines.length === 0 && <EmptyRow colSpan={6} />}
              {machines.map((m) => (
                <Tr key={m.id}>
                  <Td className="font-mono text-xs">{m.machine_id}</Td>
                  <Td className="font-medium">{m.name}</Td>
                  <Td>{m.operation_name}</Td>
                  <Td>{m.workstation_name}</Td>
                  <Td>{m.capacity_per_hour ?? "—"}</Td>
                  <Td><StatusBadge status={m.status} labels={MACHINE_STATUS_LABELS} /></Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>

      <WorkstationModal
        open={wsModalOpen}
        onClose={() => setWsModalOpen(false)}
        tsexes={tsexes}
        operations={operations}
        onCreated={load}
      />
      <MachineModal
        open={machineModalOpen}
        onClose={() => setMachineModalOpen(false)}
        workstations={workstations}
        operations={operations}
        onCreated={load}
      />
    </div>
  );
}

function WorkstationModal({ open, onClose, tsexes, operations, onCreated }) {
  const [form, setForm] = useState({ name: "", tsex: "", operation: "" });
  async function submit(e) {
    e.preventDefault();
    try {
      await adminApi.post("/workstations/", form);
      toast.success("Post yaratildi");
      onCreated();
      onClose();
    } catch {
      toast.error("Xatolik yuz berdi");
    }
  }
  return (
    <Modal open={open} onClose={onClose} title="Yangi post">
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
        <Button type="submit" className="w-full">Yaratish</Button>
      </form>
    </Modal>
  );
}

function MachineModal({ open, onClose, workstations, operations, onCreated }) {
  const [form, setForm] = useState({ machine_id: "", name: "", workstation: "", operation: "", capacity_per_hour: "" });
  async function submit(e) {
    e.preventDefault();
    try {
      await adminApi.post("/machines/", { ...form, capacity_per_hour: form.capacity_per_hour || null });
      toast.success("Stanok yaratildi");
      onCreated();
      onClose();
    } catch {
      toast.error("Xatolik yuz berdi");
    }
  }
  return (
    <Modal open={open} onClose={onClose} title="Yangi stanok">
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
        <Field label="Quvvat (soatiga)" hint="Ixtiyoriy — dashboarddagi samaradorlik hisobi uchun">
          <Input
            type="number"
            step="0.01"
            min="0"
            value={form.capacity_per_hour}
            onChange={(e) => setForm({ ...form, capacity_per_hour: e.target.value })}
          />
        </Field>
        <Button type="submit" className="w-full">Yaratish</Button>
      </form>
    </Modal>
  );
}
