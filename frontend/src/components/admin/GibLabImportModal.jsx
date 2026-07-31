import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, FileUp, TriangleAlert, UploadCloud, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import Badge from "../ui/Badge";

function formatFileSize(bytes) {
  if (!bytes) return "0 KB";
  const kb = bytes / 1024;
  return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(2)} MB`;
}

const STAT_LABELS = {
  products: "Mahsulotlar",
  product_quantity: "Mahsulot soni",
  part_definitions: "Detal turlari",
  total_physical_parts: "Jami detallar (dona)",
  sheet_materials: "Plita materiallari",
  edge_band_materials: "Kromka materiallari",
  linear_materials: "Chiziqli materiallar",
  parts_with_edge_band: "Kromkali detallar",
  edge_band_items: "Kromka BOM qatorlari",
  parts_with_xnc: "XNC (CNC) detallar",
  outer_operations: "Jami operatsiyalar",
  cutting_operations: "Kesish (CS)",
  edge_operations: "Kromka (EL)",
  linear_cutting_operations: "Chiziqli kesish (CL)",
  xnc_operations: "XNC operatsiyalar",
};

export default function GibLabImportModal({ open, onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [validating, setValidating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [conflict, setConflict] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  function reset() {
    setFile(null);
    setPreview(null);
    setConflict(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleClose() {
    reset();
    onClose();
  }

  function handleFileChange(e) {
    const picked = e.target.files?.[0] || null;
    setFile(picked);
    setPreview(null);
    setConflict(null);
  }

  async function validateFile() {
    if (!file) return;
    setValidating(true);
    setConflict(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await adminApi.post("/giblab-imports/validate/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreview(data);
      if (!data.is_valid) {
        toast.error("Faylda xatoliklar topildi, pastda ko'ring");
      }
    } catch (err) {
      const data = err.response?.data;
      if (err.response?.status === 409 && data?.code) {
        setConflict(data);
      } else {
        toast.error(data?.message || "Faylni tekshirishda xatolik yuz berdi");
      }
    } finally {
      setValidating(false);
    }
  }

  async function importFile() {
    if (!file) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await adminApi.post("/giblab-imports/import/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("GibLab fayli muvaffaqiyatli import qilindi");
      onImported?.();
      handleClose();
      navigate(`/orders/${data.order_id}`);
    } catch (err) {
      const data = err.response?.data;
      if (err.response?.status === 409 && data?.code) {
        setConflict(data);
      } else if (data?.errors) {
        toast.error("Import bekor qilindi: fayl tasdiqlanmadi");
        setPreview({ is_valid: false, errors: data.errors, warnings: data.warnings || [], statistics: {}, operation_mapping: [] });
      } else {
        toast.error(data?.message || "Import qilishda xatolik yuz berdi");
      }
    } finally {
      setImporting(false);
    }
  }

  const busy = validating || importing;

  return (
    <Modal open={open} onClose={busy ? () => {} : handleClose} title="GibLab import" size="lg">
      <div className="space-y-4">
        <div
          className="focus-ring flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-(--border-strong) bg-(--surface) px-4 py-8 text-center transition-colors duration-200 hover:border-(--accent) hover:bg-(--accent-soft)"
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud size={26} className="text-(--ink-soft)" />
          <p className="text-sm font-semibold text-(--ink)">
            {file ? file.name : "GibLab .project faylini tanlang yoki shu yerga tashlang"}
          </p>
          {file && <p className="text-xs text-(--ink-soft)">{formatFileSize(file.size)}</p>}
          <input
            ref={inputRef}
            type="file"
            accept=".project,.xml,.zip"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {conflict && (
          <div className="flex items-start gap-2 rounded-lg border border-status-orange/30 bg-status-orange-bg px-3 py-2.5 text-sm text-status-orange">
            <TriangleAlert size={16} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">{conflict.code === "DUPLICATE_IMPORT" ? "Fayl allaqachon import qilingan" : "Ushbu loyiha allaqachon boshqa fayl bilan import qilingan"}</p>
              <p className="text-status-orange/90">{conflict.message}</p>
            </div>
          </div>
        )}

        {preview && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {preview.is_valid ? (
                <Badge tone="green" dot>Fayl tayyor</Badge>
              ) : (
                <Badge tone="red" dot>Xatoliklar mavjud</Badge>
              )}
              {preview.project?.version && <Badge tone="gray">GibLab v{preview.project.version}</Badge>}
            </div>

            {preview.statistics && Object.keys(preview.statistics).length > 0 && (
              <div className="grid grid-cols-2 gap-2 rounded-lg border border-(--border-subtle) bg-(--surface) p-3 sm:grid-cols-3">
                {Object.entries(preview.statistics)
                  .filter(([, value]) => value !== null && value !== undefined)
                  .map(([key, value]) => (
                    <div key={key} className="text-xs">
                      <p className="text-(--ink-soft)">{STAT_LABELS[key] || key}</p>
                      <p className="font-semibold text-(--ink)">{value}</p>
                    </div>
                  ))}
              </div>
            )}

            {preview.operation_mapping?.some((row) => !row.mes_code) && (
              <div className="rounded-lg border border-status-orange/30 bg-status-orange-bg px-3 py-2.5 text-xs text-status-orange">
                <p className="mb-1 flex items-center gap-1.5 font-semibold">
                  <TriangleAlert size={14} /> MES operatsiya mappingi aniqlanmagan qismlar
                </p>
                <ul className="list-inside list-disc space-y-0.5">
                  {preview.operation_mapping
                    .filter((row) => !row.mes_code)
                    .map((row) => (
                      <li key={row.giblab_type}>{row.giblab_type}: {row.part_count} ta detal</li>
                    ))}
                </ul>
              </div>
            )}

            {preview.errors?.length > 0 && (
              <div className="rounded-lg border border-status-red/30 bg-status-red-bg px-3 py-2.5 text-xs text-status-red">
                <p className="mb-1 flex items-center gap-1.5 font-semibold">
                  <XCircle size={14} /> Xatoliklar ({preview.errors.length})
                </p>
                <ul className="max-h-32 list-inside list-disc space-y-0.5 overflow-y-auto">
                  {preview.errors.map((err, idx) => (
                    <li key={idx}>{err.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {preview.warnings?.length > 0 && (
              <div className="rounded-lg border border-status-yellow/30 bg-status-yellow-bg px-3 py-2.5 text-xs text-status-yellow">
                <p className="mb-1 flex items-center gap-1.5 font-semibold">
                  <TriangleAlert size={14} /> Ogohlantirishlar ({preview.warnings.length})
                </p>
                <ul className="max-h-32 list-inside list-disc space-y-0.5 overflow-y-auto">
                  {preview.warnings.map((warn, idx) => (
                    <li key={idx}>{warn.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {preview.is_valid && (
              <div className="flex items-center gap-2 text-xs text-status-green">
                <CheckCircle2 size={14} /> Fayl import qilishga tayyor
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-5 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={handleClose} disabled={busy}>
          Bekor qilish
        </Button>
        <Button type="button" variant="secondary" onClick={validateFile} disabled={!file || busy} loading={validating}>
          <FileUp size={16} /> Tekshirish
        </Button>
        <Button
          type="button"
          onClick={importFile}
          disabled={!file || !preview?.is_valid || busy}
          loading={importing}
        >
          Import qilish
        </Button>
      </div>
    </Modal>
  );
}
