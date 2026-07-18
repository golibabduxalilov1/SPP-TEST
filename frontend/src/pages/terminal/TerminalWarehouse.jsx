import { useEffect, useRef, useState } from "react";
import { CheckCircle2, ScanLine, XCircle } from "lucide-react";
import clsx from "clsx";
import { terminalApi } from "../../api/client";
import { useTerminalStore } from "../../store/terminalStore";
import { addPendingScan } from "../../lib/db";
import { uuid } from "../../lib/uuid";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import QrCameraScanner from "../../components/terminal/QrCameraScanner";

export default function TerminalWarehouse() {
  const { online, refreshPendingCount } = useTerminalStore();
  const [value, setValue] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [cameraError, setCameraError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [lastResult]);

  async function handleManualSubmit(e) {
    e.preventDefault();
    const qrToken = value.trim();
    if (!qrToken) return;
    setValue("");
    await processToken(qrToken);
  }

  async function processToken(qrToken) {
    const clientScanId = uuid();

    if (online) {
      try {
        const { data } = await terminalApi.post("/warehouse/receive", { qr_token: qrToken });
        setLastResult({ status: "ok", qrToken, packageNo: data.package_no });
        return;
      } catch (err) {
        setLastResult({ status: "error", qrToken, message: err.response?.data?.detail || "Xatolik" });
        return;
      }
    }

    await addPendingScan({
      client_scan_id: clientScanId,
      qr_token: qrToken,
      kind: "warehouse_receive",
      scanned_at_client: new Date().toISOString(),
    });
    await refreshPendingCount();
    setLastResult({ status: "pending", qrToken });
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <Card>
        <CardHeader title="Tayyor ombor" subtitle="Qadoq QR kodini skanerlang" />
        <CardBody>
          <div className="relative mx-auto aspect-square w-full max-w-xs overflow-hidden rounded-2xl border-2 border-[var(--border-strong)] bg-black [&>div>video]:h-full [&>div>video]:w-full [&>div>video]:object-cover">
            <QrCameraScanner onDecode={processToken} onError={() => setCameraError("Kameraga ruxsat berilmadi yoki kamera topilmadi. QR tokenni qo'lda kiriting.")} className="h-full w-full" />
          </div>
          {cameraError && <p className="mt-3 text-center text-sm text-status-red">{cameraError}</p>}

          <form onSubmit={handleManualSubmit} className="mt-4">
            <div className="relative">
              <ScanLine size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--ink-soft)]" />
              <Input ref={inputRef} autoFocus value={value} onChange={(e) => setValue(e.target.value)} placeholder="Qadoq QR kodi..." className="pl-11 text-lg py-4 terminal-tap" />
            </div>
          </form>

          {lastResult && (
            <div className={clsx(
              "mt-4 rounded-2xl border p-4 flex items-center gap-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]",
              lastResult.status === "ok" && "bg-status-green-bg text-status-green border-status-green/15",
              lastResult.status === "pending" && "bg-status-yellow-bg text-status-yellow border-status-yellow/15",
              lastResult.status === "error" && "bg-status-red-bg text-status-red border-status-red/15"
            )}>
              {lastResult.status === "ok" && <CheckCircle2 size={22} />}
              {lastResult.status === "error" && <XCircle size={22} />}
              <p className="font-semibold text-sm">
                {lastResult.status === "ok" && `Qabul qilindi: ${lastResult.packageNo}`}
                {lastResult.status === "pending" && "Saqlandi, sinxronizatsiya kutilmoqda"}
                {lastResult.status === "error" && lastResult.message}
              </p>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
