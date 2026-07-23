import { useEffect, useState } from "react";
import { Factory, ListTree, Pencil, Plus, Search, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { Field, Input, Textarea } from "../../components/ui/Input";
import { PageLoader } from "../../components/ui/Misc";
import Modal from "../../components/ui/Modal";
import SegmentedControl from "../../components/ui/SegmentedControl";
import EditableDetailsTable from "../../components/admin/EditableDetailsTable";
import Badge from "../../components/ui/Badge";
import Toggle from "../../components/ui/Toggle";
import { useAuthStore } from "../../store/authStore";

const TABS = [
  { value: "product-types", label: "Mahsulot turlari" },
  { value: "production-stages", label: "Ishlab chiqarish bosqichlari" },
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

export default function References() {
  const [tab, setTab] = useState(TABS[0].value);
  const user = useAuthStore((state) => state.user);
  const canManageStages = Boolean(user?.is_superuser || ["super_admin", "admin"].includes(user?.role));

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Справочники" title="Справочники" subtitle="Mahsulot turlari, standart detallar va ishlab chiqarish bosqichlari" />
      <SegmentedControl options={TABS} value={tab} onChange={setTab} />
      {tab === "product-types" && <ProductTypesTab />}
      {tab === "production-stages" && <ProductionStagesTab canManage={canManageStages} />}
    </div>
  );
}

function ProductionStagesTab({ canManage }) {
  const [stages, setStages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingStage, setEditingStage] = useState(null);
  const [deletingStage, setDeletingStage] = useState(null);
  const [togglingId, setTogglingId] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const { data } = await adminApi.get("/operations/", { params: { ordering: "order_index" } });
      setStages(data.results || data);
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
    setEditingStage(null);
    setModalOpen(true);
  }

  function openEditModal(stage) {
    setEditingStage(stage);
    setModalOpen(true);
  }

  async function toggleStage(stage) {
    setTogglingId(stage.id);
    try {
      await adminApi.patch(`/operations/${stage.id}/`, { is_active: !stage.is_active });
      toast.success(stage.is_active ? "Bosqich nofaol qilindi" : "Bosqich faollashtirildi");
      await load();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setTogglingId(null);
    }
  }

  const nextOrderIndex = stages.reduce((max, stage) => Math.max(max, Number(stage.order_index) || 0), 0) + 1;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Ishlab chiqarish bosqichlari"
          subtitle={`${stages.length} ta bosqich · tablo ustunlari faol bosqichlar tartibida chiqadi`}
          actions={canManage ? (
            <Button onClick={openCreateModal} className="w-full sm:w-auto">
              <Plus size={16} /> Bosqich qo'shish
            </Button>
          ) : null}
        />
        <CardBody className="p-0">
          {loading ? (
            <PageLoader />
          ) : (
            <Table label="Ishlab chiqarish bosqichlari">
              <Thead>
                <tr>
                  <Th className="w-24">Tartib</Th>
                  <Th>Nomi</Th>
                  <Th>Holati</Th>
                  {canManage && <Th className="text-right">Amallar</Th>}
                </tr>
              </Thead>
              <Tbody>
                {stages.length === 0 && <EmptyRow colSpan={canManage ? 4 : 3} message="Ishlab chiqarish bosqichlari yo'q" />}
                {stages.map((stage) => (
                  <Tr key={stage.id}>
                    <Td>
                      <span className="tabular inline-flex min-w-9 items-center justify-center rounded-lg bg-(--surface-muted) px-2.5 py-1.5 font-semibold text-(--ink-soft)">
                        {stage.order_index}
                      </span>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-(--accent-soft) text-(--accent-strong)">
                          <Factory size={16} />
                        </span>
                        <div className="min-w-0">
                          <p className="font-semibold text-(--ink)">{stage.name}</p>
                          {stage.is_default && <p className="text-xs text-(--ink-faint)">Default bosqich</p>}
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-3">
                        <Badge tone={stage.is_active ? "green" : "gray"} dot>
                          {stage.is_active ? "Faol" : "Nofaol"}
                        </Badge>
                        {canManage && (
                          <Toggle
                            checked={stage.is_active}
                            onChange={() => toggleStage(stage)}
                            disabled={togglingId === stage.id}
                            aria-label={`${stage.name} holatini o'zgartirish`}
                          />
                        )}
                      </div>
                    </Td>
                    {canManage && (
                      <Td>
                        <div className="ml-auto flex w-fit items-center gap-1.5">
                          <Button
                            type="button" variant="ghost" size="sm" magnetic={false}
                            onClick={() => openEditModal(stage)}
                            aria-label={`${stage.name} tahrirlash`} title="Tahrirlash"
                            className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
                          >
                            <Pencil size={14} strokeWidth={2.2} />
                          </Button>
                          <Button
                            type="button" variant="ghost" size="sm" magnetic={false}
                            onClick={() => setDeletingStage(stage)}
                            disabled={stage.is_default}
                            aria-label={`${stage.name} o'chirish`}
                            title={stage.is_default ? "Default bosqichni o'chirib bo'lmaydi" : "O'chirish"}
                            className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-status-red! hover:bg-(--color-status-red-bg)!"
                          >
                            <Trash2 size={14} strokeWidth={2.2} />
                          </Button>
                        </div>
                      </Td>
                    )}
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <ProductionStageModal
        open={modalOpen}
        stage={editingStage}
        nextOrderIndex={nextOrderIndex}
        onClose={() => setModalOpen(false)}
        onSaved={load}
      />
      <DeleteProductionStageModal
        stage={deletingStage}
        onClose={() => setDeletingStage(null)}
        onChanged={load}
      />
    </div>
  );
}

function ProductionStageModal({ open, stage, nextOrderIndex, onClose, onSaved }) {
  const [form, setForm] = useState({ name: "", order_index: 1, is_active: true });
  const [saving, setSaving] = useState(false);
  const isEditing = Boolean(stage);

  useEffect(() => {
    if (!open) return;
    setForm(stage ? {
      name: stage.name,
      order_index: stage.order_index,
      is_active: stage.is_active,
    } : {
      name: "",
      order_index: nextOrderIndex,
      is_active: true,
    });
  }, [stage, open, nextOrderIndex]);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    const payload = { ...form, order_index: Number(form.order_index) };
    try {
      if (isEditing) {
        await adminApi.patch(`/operations/${stage.id}/`, payload);
        toast.success("Ishlab chiqarish bosqichi yangilandi");
      } else {
        await adminApi.post("/operations/", payload);
        toast.success("Ishlab chiqarish bosqichi yaratildi");
      }
      await onSaved();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={isEditing ? "Bosqichni tahrirlash" : "Yangi ishlab chiqarish bosqichi"}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nomi" required>
          <Input
            required maxLength={100} autoFocus
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Masalan: Silliqlash"
          />
        </Field>
        <Field label="Tartib raqami" required hint="Tablo ustunlari kichik raqamdan katta raqamga qarab joylashadi.">
          <Input
            required type="number" min="1" step="1"
            value={form.order_index}
            onChange={(e) => setForm({ ...form, order_index: e.target.value })}
          />
        </Field>
        <div className="rounded-xl border border-(--border-subtle) bg-(--surface-muted) px-4 py-3">
          <Toggle
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            label="Faol bosqich"
          />
          <p className="mt-1 text-xs leading-5 text-(--ink-soft)">Faqat faol bosqichlar ishlab chiqarish tablosida ko'rinadi.</p>
        </div>
        <Button type="submit" className="w-full" loading={saving}>{isEditing ? "Saqlash" : "Yaratish"}</Button>
      </form>
    </Modal>
  );
}

function DeleteProductionStageModal({ stage, onClose, onChanged }) {
  const [deleting, setDeleting] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/operations/${stage.id}/`);
      toast.success("Ishlab chiqarish bosqichi o'chirildi");
      await onChanged();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  async function deactivate() {
    setDeactivating(true);
    try {
      await adminApi.patch(`/operations/${stage.id}/`, { is_active: false });
      toast.success("Bosqich nofaol qilindi");
      await onChanged();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <Modal open={Boolean(stage)} onClose={onClose} title="Bosqichni o'chirish" size="sm">
      <p className="text-sm leading-6 text-(--ink-soft)">
        <strong className="font-semibold text-(--ink)">{stage?.name}</strong> bosqichini o'chirmoqchimisiz?
        Agar unga faol yoki tarixiy buyurtma detallari bog'langan bo'lsa, o'chirish bloklanadi.
      </p>
      <p className="mt-3 rounded-lg bg-(--accent-soft) px-3 py-2.5 text-xs leading-5 text-(--accent-strong)">
        Ma'lumotlarni saqlab qolish uchun bosqichni nofaol qilish tavsiya etiladi.
      </p>
      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting || deactivating}>Bekor qilish</Button>
        {stage?.is_active && (
          <Button type="button" variant="secondary" onClick={deactivate} loading={deactivating} disabled={deleting}>Nofaol qilish</Button>
        )}
        <Button type="button" variant="danger" onClick={remove} loading={deleting} disabled={deactivating}>O'chirish</Button>
      </div>
    </Modal>
  );
}

function ProductTypesTab() {
  const [productTypes, setProductTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingType, setEditingType] = useState(null);
  const [deletingType, setDeletingType] = useState(null);
  const [detailsType, setDetailsType] = useState(null);

  async function load(q) {
    setLoading(true);
    try {
      const { data } = await adminApi.get("/product-types/", { params: { search: q || undefined } });
      setProductTypes(data.results || data);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const t = setTimeout(() => load(search), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  function openCreateModal() {
    setEditingType(null);
    setModalOpen(true);
  }

  function openEditModal(productType) {
    setEditingType(productType);
    setModalOpen(true);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Mahsulot turlari"
          subtitle={`${productTypes.length} ta tur`}
          actions={
            <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
              <div className="relative w-full sm:w-auto">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-(--ink-soft)" />
                <Input className="pl-8 w-full sm:w-md" placeholder="Qidirish..." value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <Button onClick={openCreateModal} className="w-full sm:w-auto"><Plus size={16} /> Mahsulot turi qo'shish</Button>
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
                  <Th>Nomi</Th>
                  <Th>Tavsif</Th>
                  <Th>Standart detallar</Th>
                  <Th className="text-right">Amallar</Th>
                </tr>
              </Thead>
              <Tbody>
                {productTypes.length === 0 && <EmptyRow colSpan={4} />}
                {productTypes.map((pt) => (
                  <Tr key={pt.id}>
                    <Td className="font-medium">{pt.name}</Td>
                    <Td className="text-(--ink-soft)">{pt.description || "—"}</Td>
                    <Td>{pt.details.length} ta detal</Td>
                    <Td>
                      <div className="ml-auto flex w-fit items-center gap-1.5">
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          onClick={() => setDetailsType(pt)}
                          aria-label={`${pt.name} standart detallari`} title="Standart detallar"
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
                        >
                          <ListTree size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          onClick={() => openEditModal(pt)}
                          aria-label={`${pt.name} tahrirlash`} title="Tahrirlash"
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
                        >
                          <Pencil size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          onClick={() => setDeletingType(pt)}
                          aria-label={`${pt.name} o'chirish`} title="O'chirish"
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-status-red! hover:bg-(--color-status-red-bg)!"
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

      <ProductTypeModal open={modalOpen} productType={editingType} onClose={() => setModalOpen(false)} onSaved={() => load(search)} />
      <DeleteProductTypeModal productType={deletingType} onClose={() => setDeletingType(null)} onDeleted={() => load(search)} />
      <ProductTypeDetailsModal productType={detailsType} onClose={() => setDetailsType(null)} onChanged={() => load(search)} />
    </div>
  );
}

function ProductTypeModal({ open, productType, onClose, onSaved }) {
  const [form, setForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);
  const isEditing = Boolean(productType);

  useEffect(() => {
    if (!open) return;
    setForm(productType ? { name: productType.name, description: productType.description || "" } : { name: "", description: "" });
  }, [productType, open]);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      if (isEditing) {
        await adminApi.patch(`/product-types/${productType.id}/`, form);
        toast.success("Mahsulot turi yangilandi");
      } else {
        await adminApi.post("/product-types/", form);
        toast.success("Mahsulot turi yaratildi");
      }
      await onSaved();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={isEditing ? "Mahsulot turini tahrirlash" : "Yangi mahsulot turi"}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Nomi"><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Shkaf A12" /></Field>
        <Field label="Tavsif"><Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} /></Field>
        <Button type="submit" className="w-full" loading={saving}>{isEditing ? "Saqlash" : "Yaratish"}</Button>
      </form>
    </Modal>
  );
}

function DeleteProductTypeModal({ productType, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false);

  async function remove() {
    setDeleting(true);
    try {
      await adminApi.delete(`/product-types/${productType.id}/`);
      toast.success("Mahsulot turi o'chirildi");
      await onDeleted();
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Modal open={Boolean(productType)} onClose={onClose} title="Mahsulot turini o'chirish" size="sm">
      <p className="text-sm leading-6 text-(--ink-soft)">
        <strong className="font-semibold text-(--ink)">{productType?.name}</strong> mahsulot turini va uning
        barcha standart detallarini o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.
      </p>
      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose} disabled={deleting}>Bekor qilish</Button>
        <Button type="button" variant="danger" onClick={remove} loading={deleting}>O'chirish</Button>
      </div>
    </Modal>
  );
}

function ProductTypeDetailsModal({ productType, onClose, onChanged }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!productType) return;
    setRows(productType.details);
  }, [productType]);

  async function reload() {
    setLoading(true);
    try {
      const { data } = await adminApi.get(`/product-types/${productType.id}/details/`);
      setRows(data);
      await onChanged();
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(payload) {
    await adminApi.post("/product-type-details/", { ...payload, product_type: productType.id });
    await reload();
  }

  async function handleUpdate(id, payload) {
    await adminApi.patch(`/product-type-details/${id}/`, payload);
    await reload();
  }

  async function handleDelete(id) {
    await adminApi.delete(`/product-type-details/${id}/`);
    await reload();
  }

  return (
    <Modal open={Boolean(productType)} onClose={onClose} title={`Standart detallar — ${productType?.name || ""}`} size="xl">
      {loading ? (
        <PageLoader />
      ) : (
        <EditableDetailsTable rows={rows} onCreate={handleCreate} onUpdate={handleUpdate} onDelete={handleDelete} emptyMessage="Standart detallar yo'q" />
      )}
    </Modal>
  );
}
