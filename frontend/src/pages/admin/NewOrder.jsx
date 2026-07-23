import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Save, Search, Truck, User, PackageSearch, X } from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import Button from "../../components/ui/Button";
import { Field, Input, Select, Textarea, Label } from "../../components/ui/Input";
import EditableDetailsTable from "../../components/admin/EditableDetailsTable";
import { formatUzPhone, normalizeUzPhone, isValidUzPhone } from "../../lib/phone";

const PRIORITY_LABELS = { low: "Past", normal: "Oddiy", high: "Yuqori", urgent: "Shoshilinch" };

let tempDetailIdCounter = 0;
function nextTempDetailId() {
  tempDetailIdCounter -= 1;
  return tempDetailIdCounter;
}

function SectionCard({ icon: Icon, tone, title, subtitle, children, className }) {
  return (
    <div className={clsx("rounded-xl border border-(--border-subtle) bg-(--surface) p-4 sm:p-5", className)}>
      <div className="mb-4 flex items-center gap-3">
        <span className={clsx("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", tone)}>
          <Icon size={17} />
        </span>
        <div className="min-w-0">
          <p className="font-display text-sm font-semibold text-(--ink)">{title}</p>
          {subtitle && <p className="text-xs text-(--ink-soft)">{subtitle}</p>}
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

export default function NewOrder() {
  const navigate = useNavigate();
  const emptyForm = {
    customer_name: "", customer_phone: "+998 ", delivery_address: "",
    product_name: "", product_type: "", deadline: "", priority: "normal", notes: "",
  };
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [productTypes, setProductTypes] = useState([]);
  const [details, setDetails] = useState([]);

  useEffect(() => {
    adminApi.get("/product-types/").then(({ data }) => setProductTypes(data.results || data)).catch(() => {});
  }, []);

  async function handleProductTypeChange(value) {
    setForm((f) => ({ ...f, product_type: value }));
    if (!value) {
      setDetails([]);
      return;
    }
    try {
      const { data } = await adminApi.get(`/product-types/${value}/details/`);
      setDetails(data.map((d) => ({ ...d, id: nextTempDetailId() })));
    } catch {
      toast.error("Standart detallarni yuklashda xatolik");
    }
  }

  async function addLocalDetail(payload) {
    setDetails((d) => [...d, { ...payload, id: nextTempDetailId() }]);
  }

  async function updateLocalDetail(id, payload) {
    setDetails((d) => d.map((row) => (row.id === id ? { ...payload, id } : row)));
  }

  async function removeLocalDetail(id) {
    setDetails((d) => d.filter((row) => row.id !== id));
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
    if (!form.product_type) {
      toast.error("Mahsulot turini tanlang");
      return;
    }
    setSaving(true);
    try {
      await adminApi.post("/orders/", {
        ...form,
        customer_phone: isValidUzPhone(form.customer_phone) ? normalizeUzPhone(form.customer_phone) : "",
        product_type: form.product_type || null,
        deadline: form.deadline || null,
        details: details.map(({ id, ...rest }) => rest),
      });
      toast.success("Buyurtma yaratildi");
      navigate("/orders");
    } catch {
      toast.error("Xatolik yuz berdi");
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

          <SectionCard className="lg:col-span-2" icon={PackageSearch} tone="bg-(--accent-soft) text-(--accent-strong)" title="Mebel parametrlari" subtitle="Mahsulot turi va detallar ma'lumotlari">
            <Field label="Mahsulot nomi" required>
              <Input required value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
            </Field>
            <Field label="Mahsulot turi" required hint="Tanlansa, standart detallar avtomatik to'ldiriladi">
              <Select required value={form.product_type} onChange={(e) => handleProductTypeChange(e.target.value)}>
                <option value="">Tanlanmagan</option>
                {productTypes.map((pt) => (
                  <option key={pt.id} value={pt.id}>{pt.name}</option>
                ))}
              </Select>
            </Field>
            <div>
              <Label>Detallar</Label>
              <EditableDetailsTable
                rows={details}
                onCreate={addLocalDetail}
                onUpdate={updateLocalDetail}
                onDelete={removeLocalDetail}
                emptyMessage="Detallar yo'q — mahsulot turini tanlang yoki qo'lda qo'shing"
              />
            </div>
          </SectionCard>
        </div>

        <div className="flex flex-wrap justify-end gap-2 border-t border-(--border-subtle) pt-4">
          <Button type="button" variant="secondary" onClick={() => navigate("/orders")} disabled={saving}>
            <X size={16} /> Bekor qilish
          </Button>
          <Button type="submit" disabled={saving} loading={saving}>
            <Save size={16} /> Buyurtmani saqlash
          </Button>
        </div>
      </form>
    </div>
  );
}
