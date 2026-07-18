import { useEffect, useRef, useState } from "react";
import { CheckCircle2, ScanLine, XCircle, Clock } from "lucide-react";
import clsx from "clsx";
import { terminalApi } from "../../api/client";
import { useTerminalStore } from "../../store/terminalStore";
import { addPendingScan } from "../../lib/db";
import { uuid } from "../../lib/uuid";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import Badge from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/Misc";

const ERROR_MESSAGES = {
  invalid_qr: "QR topilmadi",
  wrong_operation: "Xatolik: bu bosqich ushbu detal uchun emas",
  previous_not_completed: "Xatolik: oldingi bosqich tugamagan",
  duplicate_scan: "Bu detal bu bosqichda avval skanerlangan",
  order_closed: "Buyurtma yopilgan",
  device_not_allowed: "Bu qurilma ushbu postga ruxsat etilmagan",
  review_required: "Tekshirish talab qilinadi — masterga murojaat qiling",
};

export default function TerminalScan() {
  const { workstation, parts, online, refreshBootstrap, refreshPendingCount } = useTerminalStore();
  const [value, setValue] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [lastResult]);

  async function handleScan(e) {
    e.preventDefault();
    const qrToken = value.trim();
    if (!qrToken) return;
    setValue("");

    const clientScanId = uuid();
    const scannedAtClient = new Date().toISOString();
    const operationCode = workstation.operation_code;

    if (online) {
      try {
        await terminalApi.post("/terminal/scan", {
          client_scan_id: clientScanId,
          qr_token: qrToken,
          operation_code: operationCode,
          workstation_id: workstation.id,
          scanned_at_client: scannedAtClient,
        });
        setLastResult({ status: "synced", qrToken });
        refreshBootstrap();
        return;
      } catch (err) {
        if (err.response) {
          const errorCode = err.response.data?.error_code;
          setLastResult({ status: "conflict", qrToken, errorCode });
          return;
        }
        // fall through to offline queueing on network failure
      }
    }

    await addPendingScan({
      client_scan_id: clientScanId,
      qr_token: qrToken,
      operation_code: operationCode,
      scanned_at_client: scannedAtClient,
      kind: "route",
    });
    await refreshPendingCount();
    setLastResult({ status: "pending", qrToken });
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <Card>
        <CardHeader title={workstation?.name} subtitle={`Bosqich: ${workstation?.operation_name}`} />
        <CardBody>
          <form onSubmit={handleScan}>
            <div className="relative">
              <ScanLine size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--ink-soft)]" />
              <Input
                ref={inputRef}
                autoFocus
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="QR kodni skanerlang yoki kiriting..."
                className="pl-11 text-lg py-4 terminal-tap"
              />
            </div>
          </form>

          {lastResult && (
            <div
              className={clsx(
                "mt-4 rounded-2xl border p-4 flex items-start gap-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]",
                lastResult.status === "synced" && "bg-status-green-bg text-status-green border-status-green/15",
                lastResult.status === "pending" && "bg-status-yellow-bg text-status-yellow border-status-yellow/15",
                lastResult.status === "conflict" && "bg-status-red-bg text-status-red border-status-red/15"
              )}
            >
              {lastResult.status === "synced" && <CheckCircle2 size={22} className="shrink-0" />}
              {lastResult.status === "pending" && <Clock size={22} className="shrink-0" />}
              {lastResult.status === "conflict" && <XCircle size={22} className="shrink-0" />}
              <div className="min-w-0">
                <p className="font-mono text-xs truncate">{lastResult.qrToken}</p>
                <p className="font-semibold text-sm mt-0.5">
                  {lastResult.status === "synced" && "Skan qabul qilindi"}
                  {lastResult.status === "pending" && "Skan saqlandi, sinxronizatsiya kutilmoqda"}
                  {lastResult.status === "conflict" && (ERROR_MESSAGES[lastResult.errorCode] || "Konflikt: master tekshirishi kerak")}
                </p>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Navbatdagi vazifalar" subtitle={`${parts.length} ta detal`} />
        <CardBody className="p-0">
          {parts.length === 0 ? (
            <EmptyState title="Navbatda detal yo'q" />
          ) : (
            <ul className="divide-y divide-[var(--border-subtle)] max-h-96 overflow-y-auto scrollbar-thin">
              {parts.map((p) => (
                <li key={p.id} className="px-5 py-3 flex items-center justify-between gap-3 transition-colors hover:bg-[var(--accent-soft)]">
                  <div className="min-w-0">
                    <p className="font-medium text-sm truncate">{p.code} — {p.name}</p>
                    <p className="text-xs text-[var(--ink-faint)]">{p.order_no} · {p.quantity} dona</p>
                  </div>
                  <Badge tone={p.status === "in_progress" ? "yellow" : "gray"}>{p.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
