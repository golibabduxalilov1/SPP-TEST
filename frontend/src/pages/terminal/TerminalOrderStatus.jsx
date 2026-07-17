import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";
import toast from "react-hot-toast";
import { terminalApi } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { StatusBadge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/Misc";

const READER_ID = "order-qr-reader";

export default function TerminalOrderStatus() {
  const [order, setOrder] = useState(null);
  const [cameraError, setCameraError] = useState("");
  const [manualToken, setManualToken] = useState("");
  const [flash, setFlash] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const scannerRef = useRef(null);
  const lookingUpRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const scanner = new Html5Qrcode(READER_ID);
    scannerRef.current = scanner;

    scanner
      .start(
        { facingMode: "environment" },
        {
          fps: 10,
          qrbox: (viewfinderWidth, viewfinderHeight) => {
            const size = Math.floor(Math.min(viewfinderWidth, viewfinderHeight) * 0.7);
            return { width: size, height: size };
          },
        },
        (decodedText) => handleDecoded(decodedText),
        () => {} // per-frame "no QR found" — expected while aiming, ignored
      )
      .catch(() => {
        if (!cancelled) setCameraError("Kameraga ruxsat berilmadi yoki kamera topilmadi. QR tokenni qo'lda kiriting.");
      });

    return () => {
      cancelled = true;
      try {
        Promise.resolve(scanner.stop())
          .then(() => scanner.clear())
          .catch(() => {});
      } catch {
        // In StrictMode cleanup may run before camera startup has completed.
        try {
          scanner.clear();
        } catch {
          // The reader may already be cleared; nothing else to release.
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function safePause() {
    try {
      scannerRef.current?.pause(true);
    } catch {
      // scanner may never have started successfully (e.g. no camera) — safe to ignore
    }
  }

  function safeResume() {
    try {
      scannerRef.current?.resume();
    } catch {
      // same as above
    }
  }

  async function handleDecoded(token) {
    if (lookingUpRef.current) return;
    lookingUpRef.current = true;
    setFlash(true);
    safePause();
    await lookup(token);
    setTimeout(() => setFlash(false), 700);
    lookingUpRef.current = false;
  }

  async function lookup(token) {
    setBusy(true);
    try {
      const { data } = await terminalApi.post("/terminal/order-qr/lookup", { qr_token: token });
      setOrder({ ...data, qr_token: token });
    } catch (err) {
      toast.error(err.response?.data?.detail || "QR kod topilmadi");
      safeResume();
    } finally {
      setBusy(false);
    }
  }

  function resumeScanning() {
    setOrder(null);
    setConfirmingCancel(false);
    safeResume();
  }

  async function applyStatus(newStatus) {
    if (!order) return;
    setBusy(true);
    try {
      const { data } = await terminalApi.post("/terminal/order-qr/update-status", {
        qr_token: order.qr_token,
        new_status: newStatus,
      });
      toast.success(`Status yangilandi: ${data.status_display}`);
      resumeScanning();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Status yangilanmadi");
    } finally {
      setBusy(false);
    }
  }

  async function submitManual(e) {
    e.preventDefault();
    const token = manualToken.trim();
    if (!token) return;
    setManualToken("");
    await lookup(token);
  }

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <Card className="overflow-hidden">
        <CardHeader title="Buyurtma statusi" subtitle="Buyurtma QR kodini kameraga tuting" />
        <CardBody>
          <div className="relative mx-auto aspect-square w-full max-w-sm overflow-hidden rounded-2xl border-2 border-[var(--border-strong)] bg-black [&>div>video]:h-full [&>div>video]:w-full [&>div>video]:object-cover">
            <div id={READER_ID} className="h-full w-full" />
            <AnimatePresence>
              {flash && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 flex items-center justify-center border-4 border-status-green bg-status-green/25"
                >
                  <CheckCircle2 size={64} className="text-white drop-shadow" />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {cameraError && <p className="mt-3 text-center text-sm text-status-red">{cameraError}</p>}

          <form onSubmit={submitManual} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <Input
              value={manualToken}
              onChange={(e) => setManualToken(e.target.value)}
              placeholder="Yoki QR tokenni qo'lda kiriting..."
              containerClassName="min-w-0 flex-1"
              className="min-w-0"
            />
            <Button type="submit" size="lg" variant="secondary" disabled={busy || !manualToken.trim()} className="w-full sm:w-auto">
              Qidirish
            </Button>
          </form>
        </CardBody>
      </Card>

      {order && (
        <Card>
          <CardHeader
            title={`#${order.order_no}`}
            subtitle={order.product_name}
            actions={<StatusBadge status={order.status} labels={{ [order.status]: order.status_display }} />}
          />
          <CardBody className="space-y-4">
            <div>
              <p className="text-xs uppercase font-semibold text-[var(--ink-soft)]">Mijoz</p>
              <p className="font-medium">{order.customer_name || "—"}</p>
            </div>

            {order.next_statuses.length === 0 ? (
              <EmptyState title="Bu buyurtma yakunlangan" subtitle="Keyingi status mavjud emas" />
            ) : confirmingCancel ? (
              <div className="rounded-xl border border-status-red/20 bg-status-red-bg p-4">
                <p className="mb-3 text-sm font-semibold text-status-red">Buyurtmani bekor qilishni tasdiqlaysizmi?</p>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button variant="danger" size="lg" className="flex-1" loading={busy} onClick={() => applyStatus("cancelled")}>
                    Ha, bekor qilish
                  </Button>
                  <Button variant="secondary" size="lg" className="flex-1" onClick={() => setConfirmingCancel(false)}>
                    Yo'q
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {order.next_statuses.map((opt) => (
                  <Button
                    key={opt.value}
                    size="lg"
                    variant={opt.value === "cancelled" ? "danger" : "primary"}
                    loading={busy}
                    className="w-full sm:w-auto"
                    onClick={() => (opt.value === "cancelled" ? setConfirmingCancel(true) : applyStatus(opt.value))}
                  >
                    {opt.value === "cancelled" ? "Bekor qilish" : opt.label}
                  </Button>
                ))}
              </div>
            )}

            <Button variant="ghost" size="lg" className="w-full" onClick={resumeScanning}>
              Yana skanerlash
            </Button>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
