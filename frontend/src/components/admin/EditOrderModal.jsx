import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import Button from "../ui/Button";
import { Field, Input, Select, Textarea } from "../ui/Input";
import Modal from "../ui/Modal";
import { formatUzPhone, normalizeUzPhone, isValidUzPhone } from "../../lib/phone";

const PRIORITY_LABELS = { low: "Past", normal: "Oddiy", high: "Yuqori", urgent: "Shoshilinch" };

export default function EditOrderModal({ open, order, onClose, onSaved }) {
  const [form, setForm] = useState(null);
  const [productTypes, setProductTypes] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open || !order) return;
    setForm({
      customer_name: order.customer_name || "",
      customer_phone: order.customer_phone ? formatUzPhone(order.customer_phone) : "+998 ",
      product_name: order.product_name || "",
      product_type: order.product_type ?? "",
      deadline: order.deadline || "",
      priority: order.priority,
      notes: order.notes || "",
    });
    adminApi.get("/product-types/").then(({ data }) => setProductTypes(data.results || data)).catch(() => {});
  }, [open, order]);

  async function submit(e) {
    e.preventDefault();
    if (form.customer_phone.trim() !== "" && !isValidUzPhone(form.customer_phone)) {
      toast.error("Telefon raqamini to'liq kiriting");
      return;
    }
    setSaving(true);
    try {
      await adminApi.patch(`/orders/${order.id}/`, {
        ...form,
        customer_phone: isValidUzPhone(form.customer_phone) ? normalizeUzPhone(form.customer_phone) : "",
        product_type: form.product_type || null,
        deadline: form.deadline || null,
      });
      toast.success("Buyurtma yangilandi");
      await onSaved();
      onClose();
    } catch {
      toast.error("Buyurtmani yangilashda xatolik yuz berdi");
    } finally {
      setSaving(false);
    }
  }

  if (!order || !form) return null;

  return (
    <Modal open={open} onClose={onClose} title={`Buyurtmani tahrirlash — #${order.order_no}`}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Telefon raqami">
          <Input
            value={form.customer_phone}
            onChange={(e) => setForm({ ...form, customer_phone: formatUzPhone(e.target.value) })}
            placeholder="+998 90 123 45 67"
          />
        </Field>
        <Field label="Ism familiya">
          <Input value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} placeholder="Mijoz ismi" />
        </Field>
        <Field label="Mahsulot nomi" required>
          <Input required value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
        </Field>
        <Field label="Mahsulot turi">
          <Select value={form.product_type} onChange={(e) => setForm({ ...form, product_type: e.target.value })}>
            <option value="">Tanlanmagan</option>
            {productTypes.map((pt) => (
              <option key={pt.id} value={pt.id}>{pt.name}</option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Yetkazib berish muddati">
            <Input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
          </Field>
          <Field label="Prioritet">
            <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              {Object.entries(PRIORITY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Izoh">
          <Textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Qo'shimcha izoh..." />
        </Field>
        <Button type="submit" className="w-full" disabled={saving} loading={saving}>
          Saqlash
        </Button>
      </form>
    </Modal>
  );
}
