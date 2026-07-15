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
import Badge from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import { useTutorial } from "../../tutorial/TutorialContext";
import { employeesSteps } from "../../tutorial/content/employees";

const ROLE_OPTIONS = [
  ["super_admin", "Super Admin"], ["director", "Rahbar / Direktor"], ["manager", "Ishlab chiqarish menejeri"],
  ["master", "Master / Tsex boshlig'i"], ["technologist", "Texnolog / Konstruktor"], ["operator", "Operator / Usta"],
  ["packaging", "Qadoqlash operatori"], ["warehouse", "Omborchi"], ["sysadmin", "Tizim administratori"],
];

export default function Employees() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("employees", employeesSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
    const { data } = await adminApi.get("/employees/");
    setEmployees(data.results || data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Jamoa"
        title="Xodimlar"
        subtitle="Terminal PIN kodlari va rollar"
        actions={<Button data-tutorial="employees-add-button" onClick={() => setModalOpen(true)}><Plus size={16} /> Xodim qo'shish</Button>}
      />

      <Card>
        <CardHeader title="Ro'yxat" subtitle={`${employees.length} ta xodim`} />
        <CardBody data-tutorial="employees-table" className="p-0">
          <Table>
            <Thead>
              <tr>
                <Th>Login</Th>
                <Th>Rol</Th>
                <Th>PIN</Th>
                <Th>Telefon</Th>
                <Th>Holat</Th>
              </tr>
            </Thead>
            <Tbody>
              {employees.length === 0 && <EmptyRow colSpan={5} />}
              {employees.map((e) => (
                <Tr key={e.id}>
                  <Td className="font-medium">{e.username}</Td>
                  <Td>{e.role_display}</Td>
                  <Td className="font-mono">{e.pin_code || "—"}</Td>
                  <Td>{e.phone || "—"}</Td>
                  <Td><Badge tone={e.is_active_employee ? "green" : "gray"}>{e.is_active_employee ? "Aktiv" : "Noaktiv"}</Badge></Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>

      <EmployeeModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={load} />
    </div>
  );
}

function EmployeeModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({ username: "", first_name: "", last_name: "", role: "operator", phone: "", pin_code: "", password: "" });

  async function submit(e) {
    e.preventDefault();
    try {
      await adminApi.post("/employees/", form);
      toast.success("Xodim qo'shildi");
      onCreated();
      onClose();
    } catch {
      toast.error("Xatolik yuz berdi");
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Yangi xodim">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Ism"><Input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></Field>
          <Field label="Familiya"><Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></Field>
        </div>
        <Field label="Login"><Input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
        <Field label="Rol">
          <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ROLE_OPTIONS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="PIN kod (terminal uchun)"><Input value={form.pin_code} onChange={(e) => setForm({ ...form, pin_code: e.target.value })} /></Field>
          <Field label="Telefon"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
        </div>
        <Field label="Parol (admin panel uchun)" hint="Bo'sh qoldirilsa, tasodifiy parol yaratiladi">
          <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        <Button type="submit" className="w-full">Yaratish</Button>
      </form>
    </Modal>
  );
}
