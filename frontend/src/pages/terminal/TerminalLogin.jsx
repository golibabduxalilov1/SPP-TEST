import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Delete, Hexagon, Wifi, WifiOff } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { terminalApi } from "../../api/client";
import { useTerminalStore } from "../../store/terminalStore";
import Button from "../../components/ui/Button";
import { Select, Field } from "../../components/ui/Input";
import { getSavedWorkstationId, saveWorkstationId } from "../../lib/device";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "back"];

function targetRoute(ws) {
  return ws?.operation_code === "QADOQLASH" ? "packaging" : ws?.operation_code === "OMBOR" ? "warehouse" : "scan";
}

export default function TerminalLogin() {
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  // step: "pin" (numpad only) -> "stage-picker" (multi-stage employee, choose one)
  // or "fallback-post" (no stage assigned yet — legacy manual post picker).
  const [step, setStep] = useState("pin");
  const [lookup, setLookup] = useState(null); // { employee, workstations }
  const [allWorkstations, setAllWorkstations] = useState([]);
  const [fallbackWorkstationId, setFallbackWorkstationId] = useState("");
  const lookupPin = useTerminalStore((s) => s.lookupPin);
  const loginWithPin = useTerminalStore((s) => s.loginWithPin);
  const navigate = useNavigate();

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  function press(key) {
    if (key === "back") return setPin((p) => p.slice(0, -1));
    if (key === "") return;
    setPin((p) => (p.length >= 4 ? p : p + key));
  }

  async function goToWorkstation(ws) {
    setLoading(true);
    try {
      await loginWithPin(pin, ws);
      saveWorkstationId(ws?.id);
      navigate(`/terminal/${targetRoute(ws)}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Kirishda xatolik yuz berdi");
      resetToPin();
    } finally {
      setLoading(false);
    }
  }

  function resetToPin() {
    setStep("pin");
    setLookup(null);
    setPin("");
  }

  async function submitPin() {
    setLoading(true);
    try {
      const data = await lookupPin(pin);
      const workstations = data.workstations || [];
      if (workstations.length === 1) {
        await goToWorkstation(workstations[0]);
        return;
      }
      if (workstations.length > 1) {
        setLookup(data);
        setStep("stage-picker");
        setLoading(false);
        return;
      }
      // No stage assigned to this employee yet — fall back to manual post selection.
      const { data: stations } = await terminalApi.get("/terminal/workstations");
      setAllWorkstations(stations);
      const saved = getSavedWorkstationId();
      const remembered = saved && stations.some((w) => String(w.id) === saved);
      setFallbackWorkstationId(remembered ? saved : String(stations[0]?.id || ""));
      setLookup(data);
      setStep("fallback-post");
      setLoading(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "PIN noto'g'ri");
      setPin("");
      setLoading(false);
    }
  }

  async function submitFallback() {
    const ws = allWorkstations.find((w) => String(w.id) === fallbackWorkstationId);
    await goToWorkstation(ws);
  }

  return (
    <div className="brand-shell grain relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-4 py-10 text-white">
      <div className="blob-decor blob-accent h-[24rem] w-[24rem] -left-28 -top-20" />
      <div className="blob-decor blob-signal h-[20rem] w-[20rem] -right-20 bottom-0" />

      <div className="relative mb-6 flex items-center gap-2.5">
        <div className="rounded-xl bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] p-2 text-white shadow-(--shadow-accent)">
          <Hexagon size={22} />
        </div>
        <span className="font-display text-xl font-semibold">SPP Terminal</span>
        {online ? (
          <span className="ml-3 flex items-center gap-1 rounded-full border border-status-green/20 bg-status-green-bg px-2 py-1 text-xs font-semibold text-status-green"><Wifi size={14} /> Online</span>
        ) : (
          <span className="ml-3 flex items-center gap-1 rounded-full border border-status-red/20 bg-status-red-bg px-2 py-1 text-xs font-semibold text-status-red"><WifiOff size={14} /> Offline</span>
        )}
      </div>

      {step === "pin" && (
        <div className="glass-dark relative w-full max-w-xs rounded-3xl p-6 elevation-lg">
          <div className="my-1 text-center">
            <div className="flex items-center justify-center gap-2.5">
              {Array.from({ length: 4 }).map((_, i) => (
                <span
                  key={i}
                  className={clsx(
                    "h-3.5 w-3.5 rounded-full border-2 transition-all duration-200",
                    i < pin.length
                      ? "border-(--accent-bright) bg-(--accent-bright) shadow-[0_0_0_4px_rgba(99,102,241,0.28)]"
                      : "border-white/25"
                  )}
                />
              ))}
            </div>
            <p className="mt-2 text-xs text-white/50">PIN kodni kiriting</p>
          </div>

          <div className="mt-5 grid grid-cols-3 gap-2">
            {KEYS.map((k, i) => (
              <Button
                key={i}
                type="button"
                variant="ghost"
                size="xl"
                magnetic={false}
                onClick={() => press(k)}
                disabled={k === ""}
                className={clsx(
                  "min-h-14! rounded-[10px]! text-[15px]! font-semibold!",
                  k === "" ? "invisible" : "border-white/10! bg-white/10! text-white! hover:border-(--accent-bright)! hover:bg-[color-mix(in_srgb,var(--accent)_45%,transparent)]!",
                  k === "back" && "bg-white/5! text-white/70 hover:bg-status-red/40! hover:text-white"
                )}
              >
                {k === "back" ? <Delete className="mx-auto" size={20} /> : k}
              </Button>
            ))}
          </div>

          <Button className="mt-4 w-full" size="xl" magnetic={false} disabled={pin.length !== 4 || loading} loading={loading} onClick={submitPin}>
            Kirish
          </Button>
        </div>
      )}

      {step === "stage-picker" && lookup && (
        <div className="glass-dark relative w-full max-w-sm rounded-3xl p-6 elevation-lg">
          <button
            type="button"
            onClick={resetToPin}
            className="focus-ring mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-white/60 hover:text-white"
          >
            <ArrowLeft size={15} /> Orqaga
          </button>
          <p className="mb-4 text-center text-base font-semibold">
            Salom, {lookup.employee.first_name}! Bosqichni tanlang:
          </p>
          <div className="space-y-2.5">
            {lookup.workstations.map((ws) => (
              <button
                key={ws.id}
                type="button"
                disabled={loading}
                onClick={() => goToWorkstation(ws)}
                className="focus-ring flex min-h-16 w-full flex-col items-start justify-center rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-left transition-colors duration-200 hover:border-(--accent-bright) hover:bg-[color-mix(in_srgb,var(--accent)_35%,transparent)] disabled:pointer-events-none disabled:opacity-50"
              >
                <span className="font-display text-base font-semibold">{ws.operation_name}</span>
                <span className="text-xs text-white/55">{ws.name} — {ws.tsex}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === "fallback-post" && (
        <div className="glass-dark relative w-full max-w-xs rounded-3xl p-6 elevation-lg">
          <button
            type="button"
            onClick={resetToPin}
            className="focus-ring mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-white/60 hover:text-white"
          >
            <ArrowLeft size={15} /> Orqaga
          </button>
          <p className="mb-4 text-sm text-white/70">
            Sizga hali bosqich tayinlanmagan — postni qo'lda tanlang.
          </p>
          <Field label={<span className="text-white/70">Post</span>}>
            <Select
              value={fallbackWorkstationId}
              onChange={(e) => setFallbackWorkstationId(e.target.value)}
              className="border-white/15 bg-white/10 text-white [&>option]:text-(--ink)"
            >
              {allWorkstations.length === 0 && <option>Postlar yuklanmoqda...</option>}
              {allWorkstations.map((w) => (
                <option key={w.id} value={w.id}>{w.name} — {w.tsex}</option>
              ))}
            </Select>
          </Field>
          <Button className="mt-4 w-full" size="xl" magnetic={false} disabled={loading || !fallbackWorkstationId} loading={loading} onClick={submitFallback}>
            Kirish
          </Button>
        </div>
      )}

      <p className="relative mt-6 text-xs text-white/45">Demo PIN: usta 1002, qadoqchi 1003, omborchi 1004, master 1001</p>
    </div>
  );
}
