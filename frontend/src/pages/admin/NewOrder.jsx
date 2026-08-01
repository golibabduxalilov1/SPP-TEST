import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, Loader2, PackageSearch, Save, Search, Truck, UploadCloud, User, X, XCircle, TriangleAlert,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import Button from "../../components/ui/Button";
import Badge from "../../components/ui/Badge";
import { Field, Input, Select, Textarea, Label } from "../../components/ui/Input";
import EditableDetailsTable from "../../components/admin/EditableDetailsTable";
import { formatUzPhone, normalizeUzPhone, isValidUzPhone } from "../../lib/phone";

const PRIORITY_LABELS = { normal: "Oddiy", high: "Yuqori", urgent: "Shoshilinch" };

let tempDetailIdCounter = 0;
function nextTempDetailId() {
  tempDetailIdCounter -= 1;
  return tempDetailIdCounter;
}

function SectionCard({ icon: Icon, tone, title, subtitle, headerAction, children, className }) {
  return (
    <div className={clsx("rounded-xl border border-(--border-subtle) bg-(--surface) p-4 sm:p-5", className)}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={clsx("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", tone)}>
            <Icon size={17} />
          </span>
          <div className="min-w-0">
            <p className="font-display text-sm font-semibold text-(--ink)">{title}</p>
            {subtitle && <p className="text-xs text-(--ink-soft)">{subtitle}</p>}
          </div>
        </div>
        {headerAction}
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

export default function NewOrder() {
  const navigate = useNavigate();
  const emptyForm = {
    customer_name: "", customer_phone: "+998 ", delivery_address: "",
    product_name: "", product_quantity: "1", deadline: "", priority: "normal", notes: "",
  };
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [details, setDetails] = useState([]);

  // GibLab `.project` import: `giblab` holds the last validate() response
  // (or an error shape) once a file has been uploaded; `giblabStatus` tracks
  // the state machine (idle -> validating -> valid|invalid). While a valid
  // import is active, Mahsulot nomi/soni/Detallar are driven by the
  // server-validated `giblab.form` instead of manual entry (see
  // giblabActive below) -- the actual Order is created from the stored
  // import session (`giblab_import_id`), never from these display values.
  const [giblab, setGiblab] = useState(null);
  const [giblabStatus, setGiblabStatus] = useState("idle");
  const fileInputRef = useRef(null);
  const giblabActive = giblabStatus === "valid" && Boolean(giblab?.is_valid);

  const giblabDetailRows = useMemo(() => {
    if (!giblab?.form?.details) return [];
    return giblab.form.details.map((d) => ({
      id: `giblab-${d.external_id}-${d.code}`,
      name: d.name,
      length_mm: d.length_mm,
      width_mm: d.width_mm,
      thickness_mm: d.thickness_mm,
      quantity: d.quantity,
      material_type: d.material,
      editable: false,
    }));
  }, [giblab]);

  async function addLocalDetail(payload) {
    setDetails((d) => [...d, { ...payload, id: nextTempDetailId() }]);
  }

  async function updateLocalDetail(id, payload) {
    setDetails((d) => d.map((row) => (row.id === id ? { ...payload, id } : row)));
  }

  async function removeLocalDetail(id) {
    setDetails((d) => d.filter((row) => row.id !== id));
  }

  function clearGiblabImport() {
    setGiblab(null);
    setGiblabStatus("idle");
    setForm((f) => ({ ...f, product_name: "", product_quantity: "1" }));
  }

  async function handleGiblabFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setGiblabStatus("validating");
    setGiblab(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await adminApi.post("/giblab-imports/validate/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setGiblab(data);
      setGiblabStatus(data.is_valid ? "valid" : "invalid");
      if (data.is_valid) {
        setForm((f) => ({
          ...f,
          product_name: data.form.product_name,
          product_quantity: String(data.form.product_quantity),
        }));
        toast.success("GibLab fayli tasdiqlandi — forma to'ldirildi");
      } else {
        toast.error("Faylda xatoliklar topildi, pastda ko'ring");
      }
    } catch (err) {
      const data = err.response?.data;
      setGiblab({ is_valid: false, errors: data?.message ? [data] : [], warnings: [] });
      setGiblabStatus("invalid");
      toast.error(data?.message || "Faylni tekshirishda xatolik yuz berdi");
    }
  }

  async function lookupCustomer() {
    if (!isValidUzPhone(form.customer_phone)) {
      toast.error("Telefon raqamini to'liq kiriting");
      return;
    }
    setLookingUp(true);
    try {
      const { data } = await adminApi.get("/customers/lookup/", {
        params: { phone: normalizeUzPhone(form.customer_phone) },
      });
      if (data) {
        setForm((f) => ({
          ...f,
          customer_name: data.name || f.customer_name,
          delivery_address: data.address || f.delivery_address,
        }));
        toast.success(`Mavjud mijoz topildi: ${data.name}`);
      } else {
        toast("Yangi mijoz — ism va manzilni kiriting");
      }
    } catch {
      toast.error("Mijozni qidirishda xatolik");
    } finally {
      setLookingUp(false);
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (!isValidUzPhone(form.customer_phone)) {
      toast.error("Telefon raqamini to'liq kiriting");
      return;
    }
    if (!form.customer_name.trim()) {
      toast.error("Mijoz ismini kiriting");
      return;
    }
    const productQuantity = Number(form.product_quantity);
    if (!Number.isInteger(productQuantity) || productQuantity < 1) {
      toast.error("Mahsulot sonini to'g'ri kiriting (kamida 1)");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        customer_phone: isValidUzPhone(form.customer_phone) ? normalizeUzPhone(form.customer_phone) : "",
        product_quantity: productQuantity,
        deadline: form.deadline || null,
        // Imported Product/Parts/Materials/BOM/Routes are rebuilt server-side
        // from the import session, never from client data -- `details` here
        // is only the hand-typed rows added on top (manual flow, or extra
        // rows alongside a GibLab import), so it's always sent as-is.
        details: details.map(({ id: _id, ...rest }) => rest),
      };
      if (giblabActive) payload.giblab_import_id = giblab.import_id;
      const { data } = await adminApi.post("/orders/", payload);
      toast.success("Buyurtma yaratildi");
      navigate(`/orders/${data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.message || "Xatolik yuz berdi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <button
          type="button"
          onClick={() => navigate("/orders")}
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-semibold text-(--accent-strong) hover:text-(--ink)"
        >
          <ArrowLeft size={15} /> Buyurtmalarga qaytish
        </button>
        <h1 className="page-title mt-2 text-[clamp(1.5rem,2.6vw,2rem)] font-semibold leading-tight text-(--ink)">Yangi buyurtma</h1>
        <p className="mt-1 text-sm leading-6 text-(--ink-soft)">Yangi mebel buyurtmasini ro'yxatdan o'tkazish</p>
      </div>

      <form onSubmit={submit} className="space-y-5">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SectionCard icon={User} tone="bg-status-blue-bg text-status-blue" title="Mijoz ma'lumotlari" subtitle="Mavjud mijozni qidiring yoki yangi qo'shing">
            <Field label="Telefon raqami" required>
              <Input
                required
                value={form.customer_phone}
                onChange={(e) => setForm({ ...form, customer_phone: formatUzPhone(e.target.value) })}
                placeholder="+998 90 123 45 67"
                trailing={
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    magnetic={false}
                    onClick={lookupCustomer}
                    loading={lookingUp}
                    aria-label="Mijozni qidirish"
                    title="Mijozni qidirish"
                    className="mr-1! min-h-9! min-w-9! rounded-lg! border-transparent! text-(--ink-soft)! hover:bg-(--surface-muted)!"
                  >
                    <Search size={15} />
                  </Button>
                }
              />
            </Field>
            <Field label="Ism familiya" required>
              <Input required value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} placeholder="Mijoz ismi" />
            </Field>
            <Field label="Manzil">
              <Input value={form.delivery_address} onChange={(e) => setForm({ ...form, delivery_address: e.target.value })} placeholder="Yetkazib berish manzili" />
            </Field>
          </SectionCard>

          <SectionCard icon={Truck} tone="bg-status-orange-bg text-status-orange" title="Yetkazib berish" subtitle="Muddat va qo'shimcha izoh">
            <Field label="Yetkazib berish muddati">
              <Input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
            </Field>
            <Field label="Izoh">
              <Textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Qo'shimcha izoh..." />
            </Field>
            <Field label="Prioritet">
              <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {Object.entries(PRIORITY_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </Select>
            </Field>
          </SectionCard>

          <SectionCard
            className="lg:col-span-2"
            icon={PackageSearch}
            tone="bg-(--accent-soft) text-(--accent-strong)"
            title="Mebel parametrlari"
            subtitle="Mahsulot va detallar ma'lumotlari"
            headerAction={
              <div className="flex flex-wrap items-center gap-2">
                {giblabActive ? (
                  <>
                    <Button type="button" variant="secondary" size="sm" onClick={() => fileInputRef.current?.click()}>
                      <UploadCloud size={14} /> Boshqa fayl yuklash
                    </Button>
                    <Button type="button" variant="ghost" size="sm" onClick={clearGiblabImport}>
                      <X size={14} /> Importni tozalash
                    </Button>
                  </>
                ) : (
                  <Button
                    type="button" variant="secondary" size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    loading={giblabStatus === "validating"}
                  >
                    <UploadCloud size={14} /> GibLab .project yuklash
                  </Button>
                )}
                <input
                  ref={fileInputRef} type="file" accept=".project,.xml,.zip" className="hidden"
                  onChange={handleGiblabFile}
                />
              </div>
            }
          >
            {giblabStatus === "idle" && (
              <p className="text-xs text-(--ink-soft)">
                Mahsulot nomi, soni va detallarni avtomatik to'ldirish uchun GibLab <code>.project</code> faylini yuklashingiz mumkin, yoki quyida qo'lda kiriting.
              </p>
            )}

            {giblabStatus === "validating" && (
              <div className="flex items-center gap-2 text-sm text-(--ink-soft)">
                <Loader2 size={16} className="animate-spin" /> Fayl tekshirilmoqda...
              </div>
            )}

            {giblab && giblabStatus !== "validating" && (
              <div className="space-y-2.5 rounded-lg border border-(--border-subtle) bg-(--surface-muted) p-3">
                <div className="flex flex-wrap items-center gap-2">
                  {giblab.is_valid ? (
                    <Badge tone="green" dot>Fayl tayyor</Badge>
                  ) : (
                    <Badge tone="red" dot>Xatoliklar mavjud</Badge>
                  )}
                  {giblab.file?.name && <Badge tone="gray">{giblab.file.name}</Badge>}
                  {giblab.file?.version && <Badge tone="gray">GibLab v{giblab.file.version}</Badge>}
                </div>

                {giblab.errors?.length > 0 && (
                  <div className="rounded-lg border border-status-red/30 bg-status-red-bg px-3 py-2 text-xs text-status-red">
                    <p className="mb-1 flex items-center gap-1.5 font-semibold">
                      <XCircle size={14} /> Xatoliklar ({giblab.errors.length})
                    </p>
                    <ul className="max-h-32 list-inside list-disc space-y-0.5 overflow-y-auto">
                      {giblab.errors.map((err, idx) => (
                        <li key={idx}>{err.message}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {giblab.warnings?.length > 0 && (
                  <div className="rounded-lg border border-status-yellow/30 bg-status-yellow-bg px-3 py-2 text-xs text-status-yellow">
                    <p className="mb-1 flex items-center gap-1.5 font-semibold">
                      <TriangleAlert size={14} /> Ogohlantirishlar ({giblab.warnings.length})
                    </p>
                    <ul className="max-h-32 list-inside list-disc space-y-0.5 overflow-y-auto">
                      {giblab.warnings.map((warn, idx) => (
                        <li key={idx}>{warn.message}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {!giblab.is_valid && (
                  <Button type="button" variant="secondary" size="sm" onClick={() => fileInputRef.current?.click()}>
                    <UploadCloud size={14} /> Boshqa fayl yuklash
                  </Button>
                )}
              </div>
            )}

            <Field label="Mahsulot nomi" required>
              <Input
                required
                disabled={giblabActive}
                value={form.product_name}
                onChange={(e) => setForm({ ...form, product_name: e.target.value })}
              />
            </Field>
            <Field
              label="Mahsulot soni" required
              hint={giblabActive ? "GibLab fayldan olindi" : "Nechta bir xil shkaf buyurtma qilinmoqda"}
            >
              <Input
                type="number"
                required
                min="1"
                step="1"
                disabled={giblabActive}
                value={form.product_quantity}
                onChange={(e) => setForm({ ...form, product_quantity: e.target.value })}
              />
            </Field>
            <div>
              <Label>Detallar</Label>
              <EditableDetailsTable
                rows={giblabActive ? [...giblabDetailRows, ...details] : details}
                onCreate={addLocalDetail}
                onUpdate={updateLocalDetail}
                onDelete={removeLocalDetail}
                productQuantity={Number(form.product_quantity) || 1}
                emptyMessage="Detallar yo'q — qo'lda qo'shing"
              />
              {giblabActive && (
                <p className="mt-1.5 text-xs text-(--ink-soft)">
                  GibLab'dan import qilingan detallar tahrirlanmaydi. Qo'shimcha detal (masalan, aksessuar) qo'shishingiz mumkin.
                </p>
              )}
            </div>
          </SectionCard>
        </div>

        <div className="flex flex-wrap justify-end gap-2 border-t border-(--border-subtle) pt-4">
          <Button type="button" variant="secondary" onClick={() => navigate("/orders")} disabled={saving}>
            <X size={16} /> Bekor qilish
          </Button>
          <Button type="submit" disabled={saving || giblabStatus === "validating"} loading={saving}>
            <Save size={16} /> Buyurtmani saqlash
          </Button>
        </div>
      </form>
    </div>
  );
}
