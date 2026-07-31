import { useState } from "react";
import { Check, Pencil, Plus, QrCode, Trash2, X } from "lucide-react";
import toast from "react-hot-toast";
import Button from "../ui/Button";
import { Input } from "../ui/Input";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../ui/Table";

const EMPTY_DRAFT = { name: "", length_mm: "", width_mm: "", thickness_mm: "", quantity: "1", material_type: "" };

function cleanNumber(value) {
  return value === "" || value === null || value === undefined ? null : value;
}

function toDraft(row) {
  return {
    name: row.name || "",
    length_mm: row.length_mm ?? "",
    width_mm: row.width_mm ?? "",
    thickness_mm: row.thickness_mm ?? "",
    quantity: row.quantity ?? "1",
    material_type: row.material_type || "",
  };
}

function getErrorMessage(error) {
  const data = error?.response?.data;
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const firstError = Object.values(data).flat()[0];
    if (typeof firstError === "string") return firstError;
  }
  return "Xatolik yuz berdi";
}

/**
 * Editable detail-rows table (nomi, o'lcham, miqdor, material) shared by the
 * New Order form's manual details list and the Order detail page's
 * "Detallar" section. `onCreate/onUpdate/onDelete` may hit a real endpoint
 * or just mutate local state — the table doesn't care.
 */
export default function EditableDetailsTable({ rows, onCreate, onUpdate, onDelete, onShowQr, productQuantity = 1, emptyMessage = "Detallar yo'q" }) {
  const showTotalColumn = productQuantity > 1;
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);

  function startAdd() {
    setDraft(EMPTY_DRAFT);
    setEditingId("new");
  }

  function startEdit(row) {
    setDraft(toDraft(row));
    setEditingId(row.id);
  }

  function cancel() {
    setEditingId(null);
    setDraft(EMPTY_DRAFT);
  }

  async function save() {
    if (!draft.name.trim()) {
      toast.error("Detal nomini kiriting");
      return;
    }
    const payload = {
      name: draft.name,
      length_mm: cleanNumber(draft.length_mm),
      width_mm: cleanNumber(draft.width_mm),
      thickness_mm: cleanNumber(draft.thickness_mm),
      quantity: draft.quantity || 1,
      material_type: draft.material_type,
    };
    setBusy(true);
    try {
      if (editingId === "new") await onCreate(payload);
      else await onUpdate(editingId, payload);
      cancel();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function remove(row) {
    setBusy(true);
    try {
      await onDelete(row.id);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <Table>
        <Thead>
          <tr>
            <Th>Nomi</Th>
            <Th>Uzunlik</Th>
            <Th>Kenglik</Th>
            <Th>Qalinlik</Th>
            <Th>Miqdor (1 mahsulot uchun)</Th>
            {showTotalColumn && <Th>Jami (barcha mahsulotlar uchun)</Th>}
            <Th>Material</Th>
            <Th className="text-right">Amallar</Th>
          </tr>
        </Thead>
        <Tbody>
          {rows.length === 0 && editingId !== "new" && <EmptyRow colSpan={showTotalColumn ? 8 : 7} message={emptyMessage} />}
          {rows.map((row) =>
            editingId === row.id ? (
              <EditRow key={row.id} draft={draft} setDraft={setDraft} busy={busy} onSave={save} onCancel={cancel} showTotalColumn={showTotalColumn} />
            ) : (
              <Tr key={row.id}>
                <Td className="font-medium">
                  {row.name}
                  {row.editable === false && (
                    <span className="ml-2 rounded-full bg-(--accent-soft) px-2 py-0.5 text-[10px] font-semibold tracking-wide text-(--accent-strong) uppercase">
                      GibLab
                    </span>
                  )}
                </Td>
                <Td>{row.length_mm ?? "—"}</Td>
                <Td>{row.width_mm ?? "—"}</Td>
                <Td>{row.thickness_mm ?? "—"}</Td>
                <Td>{row.quantity}</Td>
                {showTotalColumn && <Td className="font-semibold">{(row.quantity || 0) * productQuantity} dona</Td>}
                <Td>{row.material_type || "—"}</Td>
                <Td>
                  <div className="ml-auto flex w-fit items-center gap-1.5">
                    {onShowQr && row.qr_token && (
                      <Button
                        type="button" variant="ghost" size="sm" magnetic={false}
                        disabled={busy || editingId !== null} onClick={() => onShowQr(row)}
                        aria-label={`${row.name} QR kodi`} title="QR kodi"
                        className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
                      >
                        <QrCode size={14} strokeWidth={2.2} />
                      </Button>
                    )}
                    {row.editable !== false && (
                      <>
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          disabled={busy || editingId !== null} onClick={() => startEdit(row)}
                          aria-label={`${row.name} tahrirlash`} title="Tahrirlash"
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--accent-strong)! hover:bg-(--accent-soft)!"
                        >
                          <Pencil size={14} strokeWidth={2.2} />
                        </Button>
                        <Button
                          type="button" variant="ghost" size="sm" magnetic={false}
                          disabled={busy || editingId !== null} onClick={() => remove(row)}
                          aria-label={`${row.name} o'chirish`} title="O'chirish"
                          className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-status-red! hover:bg-(--color-status-red-bg)!"
                        >
                          <Trash2 size={14} strokeWidth={2.2} />
                        </Button>
                      </>
                    )}
                  </div>
                </Td>
              </Tr>
            )
          )}
          {editingId === "new" && (
            <EditRow draft={draft} setDraft={setDraft} busy={busy} onSave={save} onCancel={cancel} showTotalColumn={showTotalColumn} />
          )}
        </Tbody>
      </Table>
      {rows.length > 0 && (
        <p className="text-xs font-medium text-(--ink-soft)">
          Buyurtma bo'yicha jami detal soni:{" "}
          <span className="font-semibold text-(--ink)">
            {rows.reduce((sum, row) => sum + (Number(row.quantity) || 0) * productQuantity, 0)} dona
          </span>
        </p>
      )}
      {editingId === null && (
        <Button type="button" variant="secondary" size="sm" onClick={startAdd}>
          <Plus size={15} /> Qo'shimcha detal qo'shish
        </Button>
      )}
    </div>
  );
}

function EditRow({ draft, setDraft, busy, onSave, onCancel, showTotalColumn }) {
  return (
    <Tr>
      <Td>
        <Input autoFocus value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Nomi" className="min-h-9!" />
      </Td>
      <Td>
        <Input type="number" step="0.1" min="0" value={draft.length_mm} onChange={(e) => setDraft({ ...draft, length_mm: e.target.value })} className="min-h-9! w-20!" />
      </Td>
      <Td>
        <Input type="number" step="0.1" min="0" value={draft.width_mm} onChange={(e) => setDraft({ ...draft, width_mm: e.target.value })} className="min-h-9! w-20!" />
      </Td>
      <Td>
        <Input type="number" step="0.1" min="0" value={draft.thickness_mm} onChange={(e) => setDraft({ ...draft, thickness_mm: e.target.value })} className="min-h-9! w-20!" />
      </Td>
      <Td>
        <Input type="number" min="1" value={draft.quantity} onChange={(e) => setDraft({ ...draft, quantity: e.target.value })} className="min-h-9! w-16!" />
      </Td>
      {showTotalColumn && <Td className="text-(--ink-faint)">—</Td>}
      <Td>
        <Input value={draft.material_type} onChange={(e) => setDraft({ ...draft, material_type: e.target.value })} placeholder="LDSP" className="min-h-9! w-24!" />
      </Td>
      <Td>
        <div className="ml-auto flex w-fit items-center gap-1.5">
          <Button
            type="button" variant="ghost" size="sm" magnetic={false} loading={busy} onClick={onSave}
            aria-label="Saqlash" title="Saqlash"
            className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-emerald-600! hover:bg-(--surface-muted)!"
          >
            <Check size={14} strokeWidth={2.4} />
          </Button>
          <Button
            type="button" variant="ghost" size="sm" magnetic={false} disabled={busy} onClick={onCancel}
            aria-label="Bekor qilish" title="Bekor qilish"
            className="min-h-9! min-w-9! rounded-lg! border-(--border-strong)! px-0! text-(--ink-soft)! hover:bg-(--surface-muted)!"
          >
            <X size={14} strokeWidth={2.4} />
          </Button>
        </div>
      </Td>
    </Tr>
  );
}
