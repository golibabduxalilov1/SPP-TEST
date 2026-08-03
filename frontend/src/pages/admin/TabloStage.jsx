import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, History, RotateCcw, ScanLine } from "lucide-react";
import toast from "react-hot-toast";
import { adminApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td } from "../../components/ui/Table";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import { PageLoader, EmptyState } from "../../components/ui/Misc";
import { StatusBadge } from "../../components/ui/Badge";
import { format } from "date-fns";

// Mirrors frontend/src/pages/terminal/TerminalScan.jsx's ERROR_MESSAGES —
// same error_code vocabulary (see terminalapp/services.py::_reject), adapted
// here for the admin-facing "Tarix" panel rather than the terminal UI.
const ERROR_MESSAGES = {
  invalid_qr: "QR topilmadi",
  wrong_operation: "Xatolik: bu bosqich ushbu detal uchun emas",
  previous_not_completed: "Xatolik: oldingi bosqich tugamagan",
  duplicate_scan: "Bu detal bu bosqichda avval skanerlangan",
  order_closed: "Buyurtma yopilgan",
  device_not_allowed: "Bu dastgoh ushbu bosqichga ruxsat etilmagan",
  review_required: "Tekshirish talab qilinadi — masterga murojaat qiling",
};

const HISTORY_STATUS_LABELS = { accepted: "Qabul qilindi", conflict: "Muammoli holat", undone: "Bekor qilindi" };

function historyReason(item) {
  if (item.status === "conflict") return ERROR_MESSAGES[item.error_code] || item.error_code || "Noma'lum xatolik";
  return null;
}

export default function TabloStage() {
  const { code } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [onlyErrors, setOnlyErrors] = useState(false);
  const [undoing, setUndoing] = useState(false);

  async function load(showLoader = true) {
    if (showLoader) setLoading(true);
    try {
      const { data } = await adminApi.get(`/production/table/${code}`);
      setData(data);
      setNotFound(false);
    } catch (error) {
      if (error.response?.status === 404) setNotFound(true);
      else if (showLoader) toast.error("Ma'lumotlarni yuklashda xatolik yuz berdi");
    } finally {
      if (showLoader) setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(() => load(false), 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  async function undoLastScan() {
    if (!data?.last_scan) return;
    setUndoing(true);
    try {
      await adminApi.post(`/terminal/scan/${data.last_scan.id}/undo`);
      toast.success("Skan bekor qilindi");
      await load(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Bekor qilishda xatolik yuz berdi");
    } finally {
      setUndoing(false);
    }
  }

  if (loading) return <PageLoader />;

  if (notFound) {
    return (
      <div className="space-y-6">
        <Link to="/tablo" className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-semibold text-(--accent-strong) hover:text-(--ink)">
          <ArrowLeft size={15} /> Tablo'ga qaytish
        </Link>
        <EmptyState title="Bosqich topilmadi" subtitle="Bu bosqich mavjud emas yoki faol emas." />
      </div>
    );
  }

  const history = onlyErrors ? data.history.filter((item) => item.status === "conflict") : data.history;

  return (
    <div className="space-y-6">
      <Link to="/tablo" className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-semibold text-(--accent-strong) hover:text-(--ink)">
        <ArrowLeft size={15} /> Tablo'ga qaytish
      </Link>

      <PageHeader eyebrow="Bosqich" title={data.operation.name} subtitle={`Kod: ${data.operation.code}`} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Navbatdagi detallar" subtitle={`${data.parts.length} ta detal`} />
          <CardBody className="p-0">
            {data.parts.length === 0 ? (
              <EmptyState title="Navbatda detal yo'q" subtitle="Barcha detallar bu bosqichdan o'tgan." />
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Nomi</Th>
                    <Th>O'lchamlari</Th>
                    <Th>Qoldiq</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {data.parts.map((part) => (
                    <Tr key={part.id}>
                      <Td>
                        <p className="font-medium">{part.code} — {part.name}</p>
                        <p className="text-xs text-(--ink-faint)">#{part.order_no}</p>
                      </Td>
                      <Td className="whitespace-nowrap">
                        {part.length_mm && part.width_mm ? `${part.length_mm} x ${part.width_mm}` : "—"}
                      </Td>
                      <Td>{part.quantity}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </CardBody>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Oxirgi skan"
              actions={
                <Button
                  size="sm"
                  variant="danger"
                  disabled={!data.last_scan}
                  loading={undoing}
                  onClick={undoLastScan}
                >
                  <RotateCcw size={14} /> Bekor qilish
                </Button>
              }
            />
            <CardBody>
              {data.last_scan ? (
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-(--accent-soft) text-(--accent-strong)">
                    <ScanLine size={18} />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-(--ink)">
                      {data.last_scan.part_code} — {data.last_scan.part_name}
                    </p>
                    <p className="text-xs text-(--ink-faint)">
                      {data.last_scan.employee_name || "—"} · {format(new Date(data.last_scan.received_at), "dd.MM.yyyy HH:mm:ss")}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="py-2 text-center text-sm text-(--ink-faint)">- - -</p>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Tarix"
              actions={
                <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-medium text-(--ink-soft)">
                  <input
                    type="checkbox"
                    checked={onlyErrors}
                    onChange={(e) => setOnlyErrors(e.target.checked)}
                    className="h-4 w-4 rounded border-(--border-strong) accent-(--accent)"
                  />
                  Faqat xatolar
                </label>
              }
            />
            <CardBody className="p-0">
              {history.length === 0 ? (
                <EmptyState icon={History} title="Tarix bo'sh" />
              ) : (
                <Table>
                  <Thead>
                    <tr>
                      <Th>Vaqt</Th>
                      <Th>Detal</Th>
                      <Th>Xodim</Th>
                      <Th>Holat</Th>
                    </tr>
                  </Thead>
                  <Tbody>
                    {history.map((item) => (
                      <Tr key={item.id}>
                        <Td className="text-xs whitespace-nowrap">{format(new Date(item.received_at), "dd.MM HH:mm:ss")}</Td>
                        <Td className="text-xs">{item.part_code || "—"}</Td>
                        <Td className="text-xs">{item.employee_name || "—"}</Td>
                        <Td>
                          <StatusBadge status={item.status} labels={HISTORY_STATUS_LABELS} />
                          {historyReason(item) && <p className="mt-1 text-xs text-status-red">{historyReason(item)}</p>}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
