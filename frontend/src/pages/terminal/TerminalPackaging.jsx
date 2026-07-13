import { useEffect, useRef, useState } from "react";
import { CheckCircle2, PackageCheck, ScanLine, XCircle } from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";
import { terminalApi } from "../../api/client";
import { useTerminalStore } from "../../store/terminalStore";
import { addPendingScan } from "../../lib/db";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Input, Field } from "../../components/ui/Input";
import Button from "../../components/ui/Button";

const ERROR_MESSAGES = {
  invalid_qr: "QR topilmadi",
  wrong_order: "Xatolik: bu detal ushbu buyurtmaga tegishli emas",
  duplicate: "Bu detal qadoqlashda avval skanerlangan",
  not_ready: "Xatolik: detalning oldingi bosqichlari tugamagan",
};

export default function TerminalPackaging() {
  const { online, refreshPendingCount } = useTerminalStore();
  const [orderNo, setOrderNo] = useState("");
  const [pkg, setPkg] = useState(null);
  const [value, setValue] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (pkg) inputRef.current?.focus();
  }, [pkg, lastResult]);

  async function startOrder(e) {
    e.preventDefault();
    try {
      const { data: orders } = await terminalApi.get("/orders/", { params: { search: orderNo } });
      const order = (orders.results || orders)[0];
      if (!order) return toast.error("Buyurtma topilmadi");
      const { data } = await terminalApi.post("/packaging/start", { order_id: order.id });
      setPkg(data);
    } catch {
      toast.error("Buyurtma topilmadi yoki offline");
    }
  }

  async function scan(e) {
    e.preventDefault();
    const qrToken = value.trim();
    if (!qrToken) return;
    setValue("");
    const clientScanId = crypto.randomUUID();

    if (online) {
      try {
        await terminalApi.post("/packaging/scan", { package_id: pkg.id, qr_token: qrToken });
        setLastResult({ status: "ok", qrToken });
        setPkg((p) => ({ ...p, items_count: p.items_count + 1 }));
        return;
      } catch (err) {
        const errorCode = err.response?.data?.error_code;
        if (errorCode) {
          setLastResult({ status: "error", qrToken, errorCode });
          return;
        }
      }
    }

    await addPendingScan({
      client_scan_id: clientScanId,
      qr_token: qrToken,
      kind: "packaging",
      payload: { package_id: pkg.id },
      scanned_at_client: new Date().toISOString(),
    });
    await refreshPendingCount();
    setLastResult({ status: "pending", qrToken });
  }

  async function complete() {
    try {
      await terminalApi.post("/packaging/complete", { package_id: pkg.id });
      toast.success("Qadoq yakunlandi");
      setPkg(null);
      setOrderNo("");
    } catch (err) {
      toast.error(err.response?.data?.message || "Qadoqlash to'liq emas");
    }
  }

  if (!pkg) {
    return (
      <div className="max-w-md mx-auto">
        <Card>
          <CardHeader title="Qadoqlash" subtitle="Buyurtma raqamini kiriting" />
          <CardBody>
            <form onSubmit={startOrder} className="space-y-4">
              <Field label="Buyurtma raqami">
                <Input value={orderNo} onChange={(e) => setOrderNo(e.target.value)} autoFocus className="terminal-tap" />
              </Field>
              <Button type="submit" size="xl" className="w-full">Boshlash</Button>
            </form>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <Card>
        <CardHeader title={`Qadoq: ${pkg.package_no}`} subtitle={`Buyurtma #${pkg.order_no} — ${pkg.items_count} ta detal skanerlangan`} />
        <CardBody>
          <form onSubmit={scan}>
            <div className="relative">
              <ScanLine size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--ink-soft)]" />
              <Input ref={inputRef} autoFocus value={value} onChange={(e) => setValue(e.target.value)} placeholder="Detal QR kodini skanerlang..." className="pl-11 text-lg py-4 terminal-tap" />
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
                {lastResult.status === "ok" && "Detal qadoqlandi"}
                {lastResult.status === "pending" && "Saqlandi, sinxronizatsiya kutilmoqda"}
                {lastResult.status === "error" && (ERROR_MESSAGES[lastResult.errorCode] || "Xatolik")}
              </p>
            </div>
          )}

          <Button className="w-full mt-4" size="lg" variant="success" onClick={complete}>
            <PackageCheck size={18} /> Qadoqni yakunlash
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
