import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Delete, Hexagon, Wifi, WifiOff } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { terminalApi } from "../../api/client";
import { useTerminalStore } from "../../store/terminalStore";
import Button from "../../components/ui/Button";
import { Select, Field } from "../../components/ui/Input";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "back"];

export default function TerminalLogin() {
  const [workstations, setWorkstations] = useState([]);
  const [workstationId, setWorkstationId] = useState("");
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const loginWithPin = useTerminalStore((s) => s.loginWithPin);
  const navigate = useNavigate();

  useEffect(() => {
    terminalApi.get("/terminal/workstations").then(({ data }) => {
      setWorkstations(data);
      if (data[0]) setWorkstationId(String(data[0].id));
    }).catch(() => {});
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
    if (pin.length >= 6) return;
    setPin((p) => p + key);
  }

  async function submit() {
    const ws = workstations.find((w) => String(w.id) === workstationId);
    setLoading(true);
    try {
      await loginWithPin(pin, ws);
      const target = ws?.operation_code === "QADOQLASH" ? "packaging" : ws?.operation_code === "OMBOR" ? "warehouse" : "scan";
      navigate(`/terminal/${target}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "PIN noto'g'ri");
      setPin("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="brand-shell grain relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-4 py-10 text-white">
      <div className="blob-decor blob-accent h-[24rem] w-[24rem] -left-28 -top-20" />
      <div className="blob-decor blob-signal h-[20rem] w-[20rem] -right-20 bottom-0" />

      <div className="relative mb-6 flex items-center gap-2.5">
        <div className="rounded-xl bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] p-2 text-white shadow-[var(--shadow-accent)]">
          <Hexagon size={22} />
        </div>
        <span className="font-display text-xl font-semibold">SPP Terminal</span>
        {online ? (
          <span className="ml-3 flex items-center gap-1 rounded-full border border-status-green/20 bg-status-green-bg px-2 py-1 text-xs font-semibold text-status-green"><Wifi size={14} /> Online</span>
        ) : (
          <span className="ml-3 flex items-center gap-1 rounded-full border border-status-red/20 bg-status-red-bg px-2 py-1 text-xs font-semibold text-status-red"><WifiOff size={14} /> Offline</span>
        )}
      </div>

      <div className="glass-dark relative w-full max-w-xs rounded-3xl p-6 elevation-lg">
        <Field label={<span className="text-white/70">Post</span>}>
          <Select
            value={workstationId}
            onChange={(e) => setWorkstationId(e.target.value)}
            className="border-white/15 bg-white/10 text-white [&>option]:text-[var(--ink)]"
          >
            {workstations.length === 0 && <option>Postlar yuklanmoqda...</option>}
            {workstations.map((w) => (
              <option key={w.id} value={w.id}>{w.name} — {w.tsex}</option>
            ))}
          </Select>
        </Field>

        <div className="my-5 text-center">
          <div className="flex items-center justify-center gap-2.5">
            {Array.from({ length: 6 }).map((_, i) => (
              <span
                key={i}
                className={clsx(
                  "h-3.5 w-3.5 rounded-full border-2 transition-all duration-200",
                  i < pin.length
                    ? "border-[var(--accent-bright)] bg-[var(--accent-bright)] shadow-[0_0_0_4px_rgba(99,102,241,0.28)]"
                    : "border-white/25"
                )}
              />
            ))}
          </div>
          <p className="mt-2 text-xs text-white/50">PIN kodni kiriting</p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {KEYS.map((k, i) => (
            <button
              key={i}
              onClick={() => press(k)}
              disabled={k === ""}
              className={clsx(
                "focus-ring terminal-tap rounded-2xl border text-lg font-semibold transition-[background-color,border-color,transform] duration-150 active:scale-95",
                k === "" ? "invisible" : "border-white/10 bg-white/10 text-white hover:border-[var(--accent-bright)] hover:bg-[color-mix(in_srgb,var(--accent)_45%,transparent)]",
                k === "back" && "!bg-white/5 text-white/70 hover:!bg-status-red/40 hover:text-white"
              )}
            >
              {k === "back" ? <Delete className="mx-auto" size={20} /> : k}
            </button>
          ))}
        </div>

        <Button className="mt-4 w-full" size="xl" magnetic={false} disabled={pin.length < 4 || loading} loading={loading} onClick={submit}>
          Kirish
        </Button>
      </div>
      <p className="relative mt-6 text-xs text-white/45">Demo PIN: usta 1002, qadoqchi 1003, omborchi 1004, master 1001</p>
    </div>
  );
}
