import { useEffect, useState } from "react";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import { format } from "date-fns";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Field, Input } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import Modal from "../../components/ui/Modal";
import { formatUzPhone, normalizeUzPhone } from "../../lib/phone";

const EMPTY_FORM = { name: "", phone: "+998 ", address: "" };

function getErrorMessage(error) {
  const data = error?.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const firstError = Object.values(data).flat()[0];
    if (typeof firstError === "string") return firstError;
  }
  return "Xatolik yuz berdi";
}

function initials(name) {
  return (name || "?").trim().slice(0, 1).toUpperCase();
}

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [deletingCustomer, setDeletingCustomer] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const { data } = await adminApi.get("/customers/", { params: { search: search || undefined } });
      setCustomers(data.results || data);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  function openCreateModal() {
    setEditingCustomer(null);
    setModalOpen(true);
  }

  function openEditModal(customer) {
    setEditingCustomer(customer);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingCustomer(null);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Mijozlar"
        title="Mijozlar"
        subtitle="Ro'yxatdan o'tgan mijozlar va ularning buyurtmalari"
        actions={
          <Button onClick={openCreateModal}>
            <Plus size={16} /> Mijoz qo'shish
          </Button>
        }
      />

      <Card>
        <CardHeader
          title="Ro'yxat"
          subtitle={`Jami ${customers.length} ta mijoz`}
          actions={
            <div className="relative w-full sm:w-64">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-soft)]" />
              <Input className="pl-8 w-full" placeholder="Ism yoki telefon..." value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
          }
        />
        <CardBody className="p-0">
          {loading ? (
            <PageLoader />
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th>Mijoz</Th>
                  <Th>Telefon</Th>
                  <Th>Manzil</Th>
                  <Th>Ro'yxatdan o'tgan</Th>
                  <Th className="text-right">Amallar</Th>
                </tr>
              </Thead>
              <Tbody>
                {customers.length === 0 && <EmptyRow colSpan={5} />}
                {customers.map((customer) => (
                  <Tr key={customer.id}>
                    <Td>
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-semibold text-[var(--accent-strong)]">
                          {initials(customer.name)}
                        </span>
                        <p className="font-medium">{customer.name || "—"}</p>
                      </div>
                    </Td>
                    <Td>
                      <a href={`tel:${customer.phone}`} className="text-[var(--accent-strong)] hover:underline">
                        {customer.phone}
                      </a>
                    </Td>
                    <Td>{customer.address || "—"}</Td>
                    <Td>{customer.created_at ? format(new Date(customer.created_at), "dd.MM.yyyy") : "—"}</Td>
                    <Td>
                      <div className="ml-auto flex w-fit items-center gap-1.5">
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          onClick={() => openEditModal(customer)}
                          aria-label={`${customer.name} mijozini tahrirlash`} title="Tahrirlash"
                          className={clsx(
                            "!min-h-9 !min-w-9 !rounded-lg !px-0 !border-[var(--border-strong)]",
                            "!text-[var(--accent-strong)] hover:!bg-[var(--accent-soft)]"
                          )}
                        >
                          <Pencil size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          onClick={() => setDeletingCustomer(customer)}
                          aria-label={`${customer.name} mijozini o'chirish`} title="O'chirish"
                          className="!min-h-9 !min-w-9 !rounded-lg !px-0 !border-[var(--border-strong)] !text-status-red hover:!bg-[var(--color-status-red-bg)]"
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

      <CustomerModal open={modalOpen} customer={editingCustomer} onClose={closeModal} onSaved={load} />
      <DeleteCustomerModal customer={deletingCustomer} onClose={() => setDeletingCustomer(null)} onDeleted={load} />
    </div>
  );
}

function CustomerModal({ open, customer, onClose, onSaved }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const isEditing = Boolean(customer);

  useEffect(() => {
    if (!open) return;
    setForm(customer ? {
      name: customer.name || "",
      phone: formatUzPhone(customer.phone || ""),
      address: customer.address || "",
    } : { ...EMPTY_FORM });
  }, [customer, open]);

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const payload = { ...form, phone: normalizeUzPhone(form.phone) };
      if (isEditing) {
        await adminApi.patch(`/customers/${customer.id}/`, payload);
        toast.success("Mijoz ma'lumotlari yangilandi");
      } else {
        await adminApi.post("/customers/", payload);
        toast.success("Mijoz qo'shildi");
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
    <Modal open={open} onClose={onClose} title={isEditing ? "Mijozni tahrirlash" : "Yangi mijoz"} size="sm">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Ism familiya" required>
          <Input required autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Mijoz ismi" />
        </Field>
        <Field label="Telefon raqami" required>
          <Input
            required
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: formatUzPhone(e.target.value) })}
            placeholder="+998 90 123 45 67"
          />
        </Field>
        <Field label="Manzil">
          <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Yetkazib berish manzili" />
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>Bekor qilish</Button>
          <Button type="submit" loading={submitting}>{isEditing ? "Saqlash" : "Qo'shish"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function DeleteCustomerModal({ customer, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/customers/${customer.id}/`);
      toast.success("Mijoz o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(customer)} onClose={onClose} title="Mijozni o'chirish" size="sm">
      <p className="text-sm leading-6 text-[var(--ink-soft)]">
        <strong className="font-semibold text-[var(--ink)]">{customer?.name}</strong> mijozini o'chirmoqchimisiz?
        Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}
