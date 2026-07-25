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
  ["super_admin", "Super Admin"], ["admin", "Admin"], ["director", "Rahbar"], ["manager", "Ishlab chiqarish menejeri"],
  ["operator", "Operator / Usta"], ["warehouse", "Omborchi"],
];

// Rollar shu ro'yxatda bo'lsa, PIN kod maydoni umuman ko'rsatilmaydi — ular
// faqat login/parol orqali boshqaruv paneliga kiradi (backend: NO_PIN_ROLES).
const NO_PIN_ROLES = ["super_admin", "admin", "director"];

// PIN faqat shu rollarda (yoki Omborchi terminaldan foydalansa) mumkin.
const PIN_CAPABLE_ROLES = ["manager", "operator", "warehouse"];

const EMPLOYMENT_STATUS_OPTIONS = [
  ["faol", "Faol"], ["vacation", "Ta'til"], ["sick", "Kasallik"], ["terminated", "Bo'shatilgan"],
];

const EMPTY_FORM = {
  username: "",
  first_name: "",
  last_name: "",
  role: "operator",
  phone: "+998 ",
  is_active_employee: true,
  employment_status: "faol",
  pin_code: "",
  password: "",
  department: "",
  managed_departments: [],
  multiStageEnabled: false,
  assigned_operation: "",
  assigned_operations: [],
  // Per selected stage: { [operationId]: { multi: bool, machines: [machineId, ...] } }
  // — each stage's "Bir nechta stanok" toggle is independent of every other stage's.
  stageMachineConfig: {},
  uses_terminal: false,
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

  function departmentLabel(employee) {
    if (employee.role === "operator") return employee.department_name || "—";
    if (employee.role === "manager") {
      const names = (employee.managed_departments_detail || []).map((t) => t.name);
      return names.length ? names.join(", ") : "—";
    }
    return "—";
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
                <Th>Foydalanuvchi nomi</Th>
                <Th>Rol</Th>
                <Th>Bo'lim</Th>
                <Th>PIN</Th>
                <Th>Telefon</Th>
                <Th>Holat</Th>
                <Th className="text-right">Amallar</Th>
              </tr>
            </Thead>
            <Tbody>
              {employees.length === 0 && <EmptyRow colSpan={7} />}
              {employees.map((employee) => (
                <Tr key={employee.id}>
                  <Td className="font-medium">{employee.username}</Td>
                  <Td>{employee.role_display}</Td>
                  <Td>{departmentLabel(employee)}</Td>
                  <Td>
                    {PIN_CAPABLE_ROLES.includes(employee.role) ? (
                      <Badge tone={employee.has_pin ? "green" : "gray"}>{employee.has_pin ? "Bor" : "Yo'q"}</Badge>
                    ) : "—"}
                  </Td>
                  <Td>{employee.phone || "—"}</Td>
                  <Td>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge tone={employee.is_active_employee ? "green" : "gray"}>
                        {employee.is_active_employee ? "Aktiv" : "Noaktiv"}
                      </Badge>
                      {employee.needs_assignment_warning && <Badge tone="orange">Biriktirish kerak</Badge>}
                    </div>
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
                            className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
                          >
                            <Pencil size={14} strokeWidth={2.2} />
                          </Button>
                        </div>
                      ) : (
                        <span className="ml-auto block w-fit text-xs text-(--ink-soft)">—</span>
                      )
                    ) : employee.role === "super_admin" ? (
                      <span className="ml-auto block w-fit text-xs text-(--ink-soft)">—</span>
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
                          className={`min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! ${employee.is_active_employee ? "text-(--ink-soft)! hover:bg-(--surface-muted)!" : "text-emerald-600! hover:bg-(--surface-muted)!"}`}
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
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
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
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-status-red! hover:bg-(--color-status-red-bg)!"
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
  const [tsexes, setTsexes] = useState([]);
  const [machines, setMachines] = useState([]);
  const [operations, setOperations] = useState([]);
  const isEditing = Boolean(employee);
  const isEditingSelf = isEditing && employee?.id === currentUser?.id;
  const roleOptions = currentUser?.role === "admin"
    ? ROLE_OPTIONS.filter(([key]) => key !== "super_admin")
    : ROLE_OPTIONS;

  const role = form.role;
  const isOperator = role === "operator";
  const isManager = role === "manager";
  const isWarehouse = role === "warehouse";
  const noPinRole = NO_PIN_ROLES.includes(role);
  const showPin = isOperator || isManager || (isWarehouse && form.uses_terminal);
  const showPassword = !isOperator && !(isWarehouse && form.uses_terminal);
  const passwordRequired = !isEditing && noPinRole;
  const showEmploymentStatus = isOperator || isWarehouse;

  useEffect(() => {
    if (!open) return;
    Promise.all([
      adminApi.get("/tsexes/", { params: { is_active: true } }),
      adminApi.get("/machines/"),
      adminApi.get("/operations/", { params: { is_active: true } }),
    ]).then(([t, m, o]) => {
      setTsexes(t.data.results || t.data);
      setMachines(m.data.results || m.data);
      setOperations(o.data.results || o.data);
    }).catch(() => {});
    if (employee) {
      // Reconstruct the per-stage machine config from the flat assigned_machines_detail
      // list (each machine detail already carries its own operation_id) — the server
      // has no separate "multi" flag, so it's inferred as on whenever >1 machine is
      // already assigned to that stage.
      const stageMachineConfig = {};
      for (const m of employee.assigned_machines_detail || []) {
        const key = m.operation_id;
        if (!stageMachineConfig[key]) stageMachineConfig[key] = { multi: false, machines: [] };
        stageMachineConfig[key].machines.push(m.id);
      }
      for (const cfg of Object.values(stageMachineConfig)) {
        cfg.multi = cfg.machines.length > 1;
      }
      setForm({
        username: employee.username || "",
        first_name: employee.first_name || "",
        last_name: employee.last_name || "",
        role: employee.role || "operator",
        phone: formatUzPhone(employee.phone || ""),
        is_active_employee: employee.is_active_employee,
        employment_status: employee.employment_status || "faol",
        pin_code: "",
        password: "",
        department: employee.department ?? "",
        managed_departments: (employee.managed_departments_detail || []).map((t) => t.id),
        multiStageEnabled: employee.multi_stage_enabled || false,
        assigned_operation: employee.assigned_operation ?? "",
        assigned_operations: (employee.assigned_operations_detail || []).map((op) => op.id),
        stageMachineConfig,
        uses_terminal: employee.uses_terminal || false,
      });
    } else {
      setForm({ ...EMPTY_FORM });
    }
  }, [employee, open]);

  // Tsex tanlanmaguncha stanoklar ro'yxati chiqmaydi; tanlangandan keyin ham
  // faqat shu tsexga tegishli stanoklar ko'rsatiladi.
  const availableMachines = form.department
    ? machines.filter((m) => String(m.tsex) === String(form.department))
    : [];

  function machinesForStage(stageId) {
    return availableMachines.filter((m) => String(m.operation) === String(stageId));
  }

  // 1-Daraja: "Bir nechta bosqich" OFF bo'lsa bitta, ON bo'lsa bir nechta
  // bosqich — har bir tanlangan bosqich uchun pastda o'z stanok bloki chiqadi.
  const selectedStageIds = form.multiStageEnabled
    ? form.assigned_operations.map(String)
    : (form.assigned_operation ? [String(form.assigned_operation)] : []);

  function updateForm(patch) {
    setForm((f) => {
      const next = { ...f, ...patch };
      if ("department" in patch) {
        // Tsex o'zgarganda endi noto'g'ri tsexga tegishli bo'lib qolgan
        // stanok tanlovlari har bir bosqich blokidan tozalanadi.
        const validMachineIds = new Set(
          machines
            .filter((m) => !next.department || String(m.tsex) === String(next.department))
            .map((m) => m.id)
        );
        const nextConfig = {};
        for (const [stageId, cfg] of Object.entries(next.stageMachineConfig)) {
          nextConfig[stageId] = { ...cfg, machines: cfg.machines.filter((id) => validMachineIds.has(id)) };
        }
        next.stageMachineConfig = nextConfig;
      }
      return next;
    });
  }

  function setMultiStageEnabled(enabled) {
    setForm((f) => {
      if (enabled) {
        const initial = f.assigned_operation ? [Number(f.assigned_operation)] : [];
        return { ...f, multiStageEnabled: true, assigned_operations: initial, assigned_operation: "" };
      }
      const first = f.assigned_operations[0] ?? "";
      return { ...f, multiStageEnabled: false, assigned_operation: first, assigned_operations: [] };
    });
  }

  function toggleStageSelection(stageId) {
    setForm((f) => ({
      ...f,
      assigned_operations: f.assigned_operations.includes(stageId)
        ? f.assigned_operations.filter((id) => id !== stageId)
        : [...f.assigned_operations, stageId],
    }));
  }

  // 2-Daraja: shu bosqichning O'ZINING "Bir nechta stanok" toggle'i —
  // boshqa bosqichlar blokidan mustaqil.
  function toggleStageMulti(stageId) {
    setForm((f) => {
      const current = f.stageMachineConfig[stageId] || { multi: false, machines: [] };
      const multi = !current.multi;
      // Multi'ni OFF qilganda faqat birinchi tanlangan stanok qoladi (select bitta qiymat kutadi).
      const machinesList = multi ? current.machines : current.machines.slice(0, 1);
      return { ...f, stageMachineConfig: { ...f.stageMachineConfig, [stageId]: { multi, machines: machinesList } } };
    });
  }

  function toggleStageMachine(stageId, machineId) {
    setForm((f) => {
      const current = f.stageMachineConfig[stageId] || { multi: false, machines: [] };
      const machinesList = current.machines.includes(machineId)
        ? current.machines.filter((id) => id !== machineId)
        : [...current.machines, machineId];
      return { ...f, stageMachineConfig: { ...f.stageMachineConfig, [stageId]: { ...current, machines: machinesList } } };
    });
  }

  function setSingleStageMachine(stageId, machineId) {
    setForm((f) => {
      const current = f.stageMachineConfig[stageId] || { multi: false, machines: [] };
      return {
        ...f,
        stageMachineConfig: { ...f.stageMachineConfig, [stageId]: { ...current, machines: machineId ? [machineId] : [] } },
      };
    });
  }

  function toggleManagedDepartment(id) {
    setForm((f) => ({
      ...f,
      managed_departments: f.managed_departments.includes(id)
        ? f.managed_departments.filter((x) => x !== id)
        : [...f.managed_departments, id],
    }));
  }

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        username: form.username,
        first_name: form.first_name,
        last_name: form.last_name,
        role: form.role,
        phone: normalizeUzPhone(form.phone),
        is_active_employee: form.is_active_employee,
      };
      if (showPassword) payload.password = form.password;
      if (showPin && form.pin_code.trim() !== "") payload.pin_code = form.pin_code.trim();
      if (isOperator) {
        payload.department = form.department === "" ? null : form.department;
        payload.multi_stage_enabled = form.multiStageEnabled;
        payload.assigned_operation = form.multiStageEnabled ? null : (form.assigned_operation || null);
        payload.assigned_operations = form.multiStageEnabled ? form.assigned_operations : [];
        payload.assigned_machines = selectedStageIds.flatMap((stageId) => form.stageMachineConfig[stageId]?.machines ?? []);
        payload.employment_status = form.employment_status;
      }
      if (isWarehouse) {
        payload.uses_terminal = form.uses_terminal;
        payload.employment_status = form.employment_status;
      }
      if (isManager) {
        payload.managed_departments = form.managed_departments;
      }
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
        {/* 1. Shaxsiy ma'lumotlar */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Ism"><Input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></Field>
          <Field label="Familiya"><Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></Field>
        </div>
        <Field label="Foydalanuvchi nomi"><Input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
        <Field label="Telefon" required hint={isEditingSelf ? "O'zingizning raqamingizni o'zgartira olmaysiz" : undefined}>
          <Input
            required
            disabled={isEditingSelf}
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: formatUzPhone(e.target.value) })}
            placeholder="+998 90 123 45 67"
          />
        </Field>

        {/* 2. Rol va holat */}
        <Field label="Rol" hint={isEditingSelf ? "O'zingizning rolingizni o'zgartira olmaysiz" : undefined}>
          <Select disabled={isEditingSelf} value={form.role} onChange={(e) => updateForm({ role: e.target.value })}>
            {roleOptions.map(([key, value]) => <option key={key} value={key}>{value}</option>)}
          </Select>
        </Field>
        {/* Yangi xodim yaratilganda holat har doim "Aktiv/Faol" bo'lib boshlanadi —
            tanlash faqat mavjud xodimni tahrirlashda kerak bo'ladi. */}
        {isEditing && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Holat">
              <Select
                value={String(form.is_active_employee)}
                onChange={(e) => setForm({ ...form, is_active_employee: e.target.value === "true" })}
              >
                <option value="true">Aktiv</option>
                <option value="false">Nofaol</option>
              </Select>
            </Field>
            {showEmploymentStatus && (
              <Field label="Ish holati">
                <Select value={form.employment_status} onChange={(e) => setForm({ ...form, employment_status: e.target.value })}>
                  {EMPLOYMENT_STATUS_OPTIONS.map(([key, value]) => <option key={key} value={key}>{value}</option>)}
                </Select>
              </Field>
            )}
          </div>
        )}
        {showPassword && (
          <Field
            label="Parol (boshqaruv paneli uchun)"
            required={passwordRequired}
            hint={isEditing ? "O'zgartirmaslik uchun bo'sh qoldiring" : passwordRequired ? "Ushbu rol uchun parol majburiy" : "Bo'sh qoldirilsa, tasodifiy parol yaratiladi"}
          >
            <Input
              type="password"
              required={passwordRequired}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </Field>
        )}

        {/* 3. PIN kod */}
        {isWarehouse && (
          <div className="rounded-xl border border-(--border-subtle) p-3.5">
            <Toggle
              label="Terminaldan foydalanadi"
              checked={form.uses_terminal}
              onChange={(e) => setForm({ ...form, uses_terminal: e.target.checked, pin_code: "" })}
            />
          </div>
        )}
        {showPin && (
          <Field
            label="PIN kod (terminal uchun)"
            required={isOperator || (isWarehouse && form.uses_terminal)}
            hint={
              isEditing && employee?.has_pin
                ? "PIN o'rnatilgan — o'zgartirmaslik uchun bo'sh qoldiring"
                : isEditing
                  ? "PIN belgilanmagan — 4 ta raqam kiriting"
                  : "4 ta raqam kiriting"
            }
          >
            <Input
              value={form.pin_code}
              onChange={(e) => setForm({ ...form, pin_code: e.target.value.replace(/\D/g, "").slice(0, 4) })}
              inputMode="numeric"
              maxLength={4}
              pattern="[0-9]{4}"
              placeholder="0000"
              title="PIN kod 4 ta raqamdan iborat bo'lishi kerak"
            />
          </Field>
        )}

        {/* 4. Tsex */}
        {isOperator && (
          <Field label="Tsex" required>
            <Select value={form.department} onChange={(e) => updateForm({ department: e.target.value })}>
              <option value="">Tanlang</option>
              {tsexes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </Select>
          </Field>
        )}
        {isManager && (
          <div className="rounded-xl border border-(--border-subtle) p-3.5">
            <Label>Biriktirilgan tsexlar</Label>
            <div className="mt-2 max-h-40 space-y-2 overflow-y-auto">
              {tsexes.map((t) => (
                <label key={t.id} className="flex cursor-pointer items-center gap-2.5 text-sm text-(--ink)">
                  <Checkbox checked={form.managed_departments.includes(t.id)} onChange={() => toggleManagedDepartment(t.id)} />
                  {t.name}
                </label>
              ))}
              {tsexes.length === 0 && <p className="text-xs text-(--ink-faint)">Tsexlar topilmadi</p>}
            </div>
          </div>
        )}

        {/* 5. Ishlab chiqarish bosqichi — 1-daraja on/off: bitta yoki bir nechta */}
        {isOperator && (
          <div className="rounded-xl border border-(--border-subtle) p-3.5">
            <Toggle
              label="Bir nechta bosqich"
              checked={form.multiStageEnabled}
              onChange={(e) => setMultiStageEnabled(e.target.checked)}
            />
            <div className="mt-3">
              <Label required>Ishlab chiqarish bosqichi</Label>
              {!form.multiStageEnabled ? (
                <Select
                  className="mt-2"
                  value={form.assigned_operation}
                  onChange={(e) => setForm((f) => ({ ...f, assigned_operation: e.target.value }))}
                >
                  <option value="">Tanlang</option>
                  {operations.map((op) => <option key={op.id} value={op.id}>{op.name}</option>)}
                </Select>
              ) : (
                <div className="mt-2 max-h-40 space-y-2 overflow-y-auto">
                  {operations.map((op) => (
                    <label key={op.id} className="flex cursor-pointer items-center gap-2.5 text-sm text-(--ink)">
                      <Checkbox checked={form.assigned_operations.includes(op.id)} onChange={() => toggleStageSelection(op.id)} />
                      {op.name}
                    </label>
                  ))}
                  {operations.length === 0 && <p className="text-xs text-(--ink-faint)">Bosqichlar topilmadi</p>}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 6. Har bir tanlangan bosqich uchun ALOHIDA stanok bloki — 2-daraja
            on/off: har birining "Bir nechta stanok" toggle'i mustaqil. */}
        {isOperator && !form.department && (
          <p className="text-xs text-(--ink-faint)">Dastgoh tanlash uchun avval tsexni tanlang.</p>
        )}
        {isOperator && form.department && selectedStageIds.length === 0 && (
          <p className="text-xs text-(--ink-faint)">Dastgoh tanlash uchun avval ishlab chiqarish bosqichini tanlang.</p>
        )}
        {isOperator && form.department && selectedStageIds.map((stageId) => {
          const stage = operations.find((op) => String(op.id) === stageId);
          const stageMachines = machinesForStage(stageId);
          const config = form.stageMachineConfig[stageId] || { multi: false, machines: [] };
          return (
            <div key={stageId} className="rounded-xl border border-(--border-subtle) p-3.5">
              <Label required>{stage ? `${stage.name} uchun dastgoh` : "Dastgoh"}</Label>
              <Toggle
                className="mt-2"
                label="Bir nechta dastgoh"
                checked={config.multi}
                onChange={() => toggleStageMulti(stageId)}
              />
              {stageMachines.length === 0 ? (
                <p className="mt-2 text-xs text-(--ink-faint)">Tanlangan tsex va bosqichga tegishli dastgoh topilmadi.</p>
              ) : config.multi ? (
                <div className="mt-2 max-h-40 space-y-2 overflow-y-auto">
                  {stageMachines.map((m) => (
                    <label key={m.id} className="flex cursor-pointer items-center gap-2.5 text-sm text-(--ink)">
                      <Checkbox checked={config.machines.includes(m.id)} onChange={() => toggleStageMachine(stageId, m.id)} />
                      {m.name}
                    </label>
                  ))}
                </div>
              ) : (
                <Select
                  className="mt-2"
                  value={config.machines[0] ?? ""}
                  onChange={(e) => setSingleStageMachine(stageId, e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">Tanlang</option>
                  {stageMachines.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </Select>
              )}
            </div>
          );
        })}

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
      <p className="text-sm leading-6 text-(--ink-soft)">
        <strong className="font-semibold text-(--ink)">{employee?.username}</strong> xodimini o'chirmoqchimisiz?
        Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}
