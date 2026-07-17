import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, QrCode, RefreshCw, Wifi, WifiOff } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";
import { useTerminalStore } from "../store/terminalStore";
import { PageLoader } from "../components/ui/Misc";
import Button from "../components/ui/Button";

const AUTO_SYNC_INTERVAL_MS = 15 * 60 * 1000;
const IDLE_TIMEOUT_MS = 5 * 60 * 1000;
const IDLE_EVENTS = ["pointerdown", "keydown", "touchstart"];

// Roles that may open /terminal/order-status — mirrors accounts.permissions.CanScanOrderStatus
// on the backend, restricted here to the roles that actually log into the terminal.
const ORDER_STATUS_ROLES = ["master", "packaging", "warehouse"];

export default function TerminalLayout() {
  const { employee, workstation, ready, online, pendingCount, lastSyncAt, init, logout, sync, refreshPendingCount } = useTerminalStore();
  const navigate = useNavigate();
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    init();
    refreshPendingCount();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      if (navigator.onLine) {
        sync().catch(() => {});
      }
    }, AUTO_SYNC_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Idle-timeout: after inactivity, drop back to the PIN screen so the next
  // employee at this terminal doesn't inherit the previous session.
  useEffect(() => {
    if (!employee) return undefined;
    let timer;
    const reset = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        logout();
        navigate("/terminal/login");
      }, IDLE_TIMEOUT_MS);
    };
    IDLE_EVENTS.forEach((evt) => window.addEventListener(evt, reset));
    reset();
    return () => {
      clearTimeout(timer);
      IDLE_EVENTS.forEach((evt) => window.removeEventListener(evt, reset));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employee]);

  async function handleSync() {
    setSyncing(true);
    try {
      const res = await sync();
      if (res.skipped) {
        toast("Yuboriladigan skan yo'q", { icon: null });
      } else {
        toast.success(`${res.accepted} ta skan serverga yuborildi`);
      }
    } catch {
      toast.error("Sinxronizatsiya muvaffaqiyatsiz, keyinroq qayta urinib ko'ring");
    } finally {
      setSyncing(false);
    }
  }

  if (!ready) return <PageLoader />;
  if (!employee) return <Navigate to="/terminal/login" replace />;

  return (
    <div className="min-h-screen bg-(--canvas) flex flex-col">
      <header className="brand-shell flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-4 py-3 text-white elevation-lg sm:px-6">
        <div className="min-w-0">
          <p className="truncate font-display text-sm font-semibold tracking-wide">{workstation?.name || "Post"}</p>
          <p className="truncate text-xs text-white/50">{employee.first_name} {employee.last_name} — {employee.role_display}</p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:gap-3">
          <span className={clsx("flex min-h-8 items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold", online ? "bg-status-green-bg text-status-green border-status-green/15" : "bg-status-red-bg text-status-red border-status-red/15")}>
            {online ? <Wifi size={13} /> : <WifiOff size={13} />} {online ? "Online" : "Offline"}
          </span>
          {pendingCount > 0 && (
            <span className="min-h-8 rounded-full border border-status-orange/15 bg-status-orange-bg px-2.5 py-1 text-xs font-semibold text-status-orange">
              Pending: {pendingCount}
            </span>
          )}
          {ORDER_STATUS_ROLES.includes(employee.role) && (
            <NavLink
              to="/terminal/order-status"
              className={({ isActive }) =>
                clsx(
                  "focus-ring flex min-h-11 items-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors duration-300",
                  isActive
                    ? "border-transparent bg-[linear-gradient(120deg,var(--accent),var(--accent-bright))] text-white"
                    : "border-white/15 bg-white/10 text-white/80 hover:bg-white/15 hover:text-white"
                )
              }
            >
              <QrCode size={14} /> Buyurtma statusi
            </NavLink>
          )}
          <Button
            onClick={handleSync}
            loading={syncing}
            magnetic={false}
            size="sm"
            className="min-h-11!"
          >
            <RefreshCw size={13} /> Sinxronizatsiya
          </Button>
          <Button
            variant="ghost"
            size="icon"
            magnetic={false}
            onClick={() => {
              logout();
              navigate("/terminal/login");
            }}
            aria-label="Chiqish"
            className="min-h-11! min-w-11! border-transparent! bg-transparent! text-white/55! hover:bg-white/8! hover:text-white!"
          >
            <LogOut size={16} />
          </Button>
        </div>
      </header>
      {lastSyncAt && (
        <div className="bg-(--accent-soft) text-(--accent-strong) text-xs px-4 py-2 text-center border-b border-(--border-subtle)">
          Oxirgi sync: {new Date(lastSyncAt).toLocaleTimeString()}
        </div>
      )}
      <main className="flex-1 p-4 sm:p-6">
        <Outlet />
      </main>
    </div>
  );
}
