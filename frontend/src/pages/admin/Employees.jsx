import { useEffect, useState } from "react";
import { Ban, CheckCircle2, Pencil, Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { useAuthStore } from "../../store/authStore";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Field, Input, Select, Label } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import Badge from "../../components/ui/Badge";
import Modal from "../../components/ui/Modal";
import Toggle from "../../components/ui/Toggle";
import { Checkbox } from "../../components/ui/Checkbox";
import { useTutorial } from "../../tutorial/TutorialContext";
import { employeesSteps } from "../../tutorial/content/employees";
import { formatUzPhone, normalizeUzPhone } from "../../lib/phone";

const ROLE_OPTIONS = [
  ["super_admin", "Super Admin"], ["admin", "Admin"], ["director", "Rahbar / Direktor"], ["manager", "Ishlab chiqarish menejeri"],
  ["master", "Master / Tsex boshlig'i"], ["technologist", "Texnolog / Konstruktor"], ["operator", "Operator / Usta"],
  ["packaging", "Qadoqlash operatori"], ["warehouse", "Omborchi"], ["sysadmin", "Tizim administratori"],
];

const EMPTY_FORM = {
  username: "",
  first_name: "",
  last_name: "",
  role: "operator",
  phone: "+998 ",
  pin_code: "",
  password: "",
  multi_stage_enabled: false,
  assigned_workstation: "",
  assigned_workstations: [],
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

export default function Employees() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [deletingEmployee, setDeletingEmployee] = useState(null);
  const [togglingId, setTogglingId] = useState(null);
  const currentUser = useAuthStore((state) => state.user);
  const { registerAndAutoStart } = useTutorial();

  useEffect(() => registerAndAutoStart("employees", employeesSteps), [registerAndAutoStart]);

  async function load() {
    setLoading(true);
    try {
      const { data } = await adminApi.get("/employees/");
      setEmployees(data.results || data);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openCreateModal() {
    setEditingEmployee(null);
    setModalOpen(true);
  }

  function openEditModal(employee) {
    setEditingEmployee(employee);
    setModalOpen(true);
  }

  function closeEmployeeModal() {
    setModalOpen(false);
    setEditingEmployee(null);
  }

  async function toggleActive(employee) {
    setTogglingId(employee.id);
    try {
      await adminApi.patch(`/employees/${employee.id}/`, { is_active_employee: !employee.is_active_employee });
      toast.success(employee.is_active_employee ? "Xodim nofaol qilindi" : "Xodim faollashtirildi");
      await load();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setTogglingId(null);
    }
  }

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Jamoa"
        title="Xodimlar"
        subtitle="Terminal PIN kodlari va rollar"
        actions={<Button data-tutorial="employees-add-button" onClick={openCreateModal}><Plus size={16} /> Xodim qo'shish</Button>}
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
                <Th className="text-right">Amallar</Th>
              </tr>
            </Thead>
            <Tbody>
              {employees.length === 0 && <EmptyRow colSpan={6} />}
              {employees.map((employee) => (
                <Tr key={employee.id}>
                  <Td className="font-medium">{employee.username}</Td>
                  <Td>{employee.role_display}</Td>
                  <Td className="font-mono">{employee.pin_code || "—"}</Td>
                  <Td>{employee.phone || "—"}</Td>
                  <Td>
                    <Badge tone={employee.is_active_employee ? "green" : "gray"}>
                      {employee.is_active_employee ? "Aktiv" : "Noaktiv"}
                    </Badge>
                  </Td>
                  <Td className="whitespace-nowrap">
                    {employee.id === currentUser?.id ? (
                      currentUser?.role === "super_admin" ? (
                        <div className="ml-auto flex w-fit items-center gap-1.5">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            magnetic={false}
                            onClick={() => openEditModal(employee)}
                            aria-label={`${employee.username} xodimini tahrirlash`}
                            title="Tahrirlash"
                            className="!min-h-9 !min-w-9 !rounded-lg !border-[var(--border-strong)] !px-0 !text-[var(--accent-strong)] hover:!bg-[var(--accent-soft)]"
                          >
                            <Pencil size={14} strokeWidth={2.2} />
                          </Button>
                        </div>
                      ) : (
                        <span className="ml-auto block w-fit text-xs text-[var(--ink-soft)]">—</span>
                      )
                    ) : employee.role === "super_admin" ? (
                      <span className="ml-auto block w-fit text-xs text-[var(--ink-soft)]">—</span>
                    ) : (
                      <div className="ml-auto flex w-fit items-center gap-1.5">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          magnetic={false}
                          onClick={() => toggleActive(employee)}
                          loading={togglingId === employee.id}
                          aria-label={`${employee.username} xodimini ${employee.is_active_employee ? "nofaol" : "faol"} qilish`}
                          title={employee.is_active_employee ? "Nofaol qilish" : "Faol qilish"}
                          className={`!min-h-9 !min-w-9 !rounded-lg !border-[var(--border-strong)] !px-0 ${employee.is_active_employee ? "!text-[var(--ink-soft)] hover:!bg-[var(--surface-muted)]" : "!text-emerald-600 hover:!bg-[var(--surface-muted)]"}`}
                        >
                          {employee.is_active_employee ? <Ban size={14} strokeWidth={2.2} /> : <CheckCircle2 size={14} strokeWidth={2.2} />}
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          magnetic={false}
                          onClick={() => openEditModal(employee)}
                          aria-label={`${employee.username} xodimini tahrirlash`}
                          title="Tahrirlash"
                          className="!min-h-9 !min-w-9 !rounded-lg !border-[var(--border-strong)] !px-0 !text-[var(--accent-strong)] hover:!bg-[var(--accent-soft)]"
                        >
                          <Pencil size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          magnetic={false}
                          onClick={() => setDeletingEmployee(employee)}
                          aria-label={`${employee.username} xodimini o'chirish`}
                          title="O'chirish"
                          className="!min-h-9 !min-w-9 !rounded-lg !border-[var(--border-strong)] !px-0 !text-status-red hover:!bg-[var(--color-status-red-bg)]"
                        >
                          <Trash2 size={14} strokeWidth={2.2} />
                        </Button>
                      </div>
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>

      <EmployeeModal
        open={modalOpen}
        employee={editingEmployee}
        currentUser={currentUser}
        onClose={closeEmployeeModal}
        onSaved={load}
      />
      <DeleteEmployeeModal
        employee={deletingEmployee}
        onClose={() => setDeletingEmployee(null)}
        onDeleted={load}
      />
    </div>
  );
}

function EmployeeModal({ open, employee, currentUser, onClose, onSaved }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [workstations, setWorkstations] = useState([]);
  const isEditing = Boolean(employee);
  const isEditingSelf = isEditing && employee?.id === currentUser?.id;
  const roleOptions = currentUser?.role === "admin"
    ? ROLE_OPTIONS.filter(([key]) => key !== "super_admin")
    : ROLE_OPTIONS;

  useEffect(() => {
    if (!open) return;
    adminApi.get("/workstations/").then(({ data }) => setWorkstations(data.results || data)).catch(() => {});
    setForm(employee ? {
      username: employee.username || "",
      first_name: employee.first_name || "",
      last_name: employee.last_name || "",
      role: employee.role || "operator",
      phone: formatUzPhone(employee.phone || ""),
      pin_code: employee.pin_code || "",
      password: "",
      is_active_employee: employee.is_active_employee,
      multi_stage_enabled: employee.multi_stage_enabled || false,
      assigned_workstation: employee.assigned_workstation ?? "",
      assigned_workstations: (employee.assigned_workstations_detail || []).map((w) => w.id),
    } : { ...EMPTY_FORM });
  }, [employee, open]);

  function toggleAssignedWorkstation(id) {
    setForm((f) => ({
      ...f,
      assigned_workstations: f.assigned_workstations.includes(id)
        ? f.assigned_workstations.filter((x) => x !== id)
        : [...f.assigned_workstations, id],
    }));
  }

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        phone: normalizeUzPhone(form.phone),
        pin_code: form.pin_code.trim() === "" ? null : form.pin_code.trim(),
        assigned_workstation: form.multi_stage_enabled || form.assigned_workstation === "" ? null : form.assigned_workstation,
        assigned_workstations: form.multi_stage_enabled ? form.assigned_workstations : [],
      };
      if (isEditing) {
        await adminApi.patch(`/employees/${employee.id}/`, payload);
        toast.success("Xodim ma'lumotlari yangilandi");
      } else {
        await adminApi.post("/employees/", payload);
        toast.success("Xodim qo'shildi");
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
    <Modal open={open} onClose={onClose} title={isEditing ? "Xodimni tahrirlash" : "Yangi xodim"}>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Ism"><Input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></Field>
          <Field label="Familiya"><Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></Field>
        </div>
        <Field label="Login"><Input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
        <Field label="Rol" hint={isEditingSelf ? "O'zingizning rolingizni o'zgartira olmaysiz" : undefined}>
          <Select disabled={isEditingSelf} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {roleOptions.map(([key, value]) => <option key={key} value={key}>{value}</option>)}
          </Select>
        </Field>
        <Field label="Holat">
          <Select
            value={String(form.is_active_employee)}
            onChange={(e) => setForm({ ...form, is_active_employee: e.target.value === "true" })}
          >
            <option value="true">Aktiv</option>
            <option value="false">Noaktiv</option>
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="PIN kod (terminal uchun)"><Input value={form.pin_code} onChange={(e) => setForm({ ...form, pin_code: e.target.value })} /></Field>
          <Field label="Telefon" required hint={isEditingSelf ? "O'zingizning raqamingizni o'zgartira olmaysiz" : undefined}>
            <Input
              required
              disabled={isEditingSelf}
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: formatUzPhone(e.target.value) })}
              placeholder="+998 90 123 45 67"
            />
          </Field>
        </div>
        <Field
          label="Parol (admin panel uchun)"
          hint={isEditing ? "O'zgartirmaslik uchun bo'sh qoldiring" : "Bo'sh qoldirilsa, tasodifiy parol yaratiladi"}
        >
          <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>

        <div className="rounded-xl border border-[var(--border-subtle)] p-3.5">
          <Toggle
            label="Bir nechta bosqich"
            checked={form.multi_stage_enabled}
            onChange={(e) => setForm({ ...form, multi_stage_enabled: e.target.checked })}
          />
          <p className="mt-1.5 text-xs text-[var(--ink-soft)]">
            Terminalga PIN bilan kirganda xodim avtomatik shu bosqich(lar)ga yo'naltiriladi.
          </p>

          {form.multi_stage_enabled ? (
            <div className="mt-3 max-h-48 space-y-2 overflow-y-auto">
              {workstations.map((w) => (
                <label key={w.id} className="flex cursor-pointer items-center gap-2.5 text-sm text-[var(--ink)]">
                  <Checkbox
                    checked={form.assigned_workstations.includes(w.id)}
                    onChange={() => toggleAssignedWorkstation(w.id)}
                  />
                  {w.name} — {w.operation_name} ({w.tsex_name})
                </label>
              ))}
              {workstations.length === 0 && <p className="text-xs text-[var(--ink-faint)]">Postlar topilmadi</p>}
            </div>
          ) : (
            <div className="mt-3">
              <Label>Bosqich</Label>
              <Select
                value={form.assigned_workstation}
                onChange={(e) => setForm({ ...form, assigned_workstation: e.target.value })}
              >
                <option value="">Tayinlanmagan</option>
                {workstations.map((w) => (
                  <option key={w.id} value={w.id}>{w.name} — {w.operation_name} ({w.tsex_name})</option>
                ))}
              </Select>
            </div>
          )}
        </div>

        <Button type="submit" loading={submitting} className="w-full">
          {isEditing ? "Saqlash" : "Yaratish"}
        </Button>
      </form>
    </Modal>
  );
}

function DeleteEmployeeModal({ employee, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/employees/${employee.id}/`);
      toast.success("Xodim o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(employee)} onClose={onClose} title="Xodimni o'chirish" size="sm">
      <p className="text-sm leading-6 text-[var(--ink-soft)]">
        <strong className="font-semibold text-[var(--ink)]">{employee?.username}</strong> xodimini o'chirmoqchimisiz?
        Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}
