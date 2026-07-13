import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, Table2, Factory, Users, AlertTriangle,
  Warehouse, BarChart3, LogOut, Tags, Hexagon,
} from "lucide-react";
import { motion } from "framer-motion";
import { useAuthStore } from "../store/authStore";
import Button from "../components/ui/Button";
import clsx from "clsx";
import { TutorialProvider } from "../tutorial/TutorialContext";
import TutorialOverlay from "../tutorial/TutorialOverlay";
import HelpButton from "../tutorial/HelpButton";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/orders", label: "Buyurtmalar", icon: ClipboardList },
  { to: "/tablo", label: "Ishlab chiqarish tablosi", icon: Table2 },
  { to: "/labels", label: "QR / Birka", icon: Tags },
  { to: "/machines", label: "Tsex va stanoklar", icon: Factory },
  { to: "/employees", label: "Xodimlar", icon: Users },
  { to: "/conflicts", label: "Konfliktlar", icon: AlertTriangle, roles: ["super_admin", "director", "manager", "master"] },
  { to: "/warehouse", label: "Tayyor ombor", icon: Warehouse, extra: "Qadoqlash" },
  { to: "/reports", label: "Hisobotlar", icon: BarChart3 },
];

function initials(user) {
  return `${user?.first_name?.[0] || ""}${user?.last_name?.[0] || ""}`.toUpperCase() || "U";
}

export default function AdminLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <TutorialProvider>
    <div className="min-h-dvh bg-transparent lg:flex lg:h-dvh lg:items-stretch lg:overflow-hidden">
      <aside className="brand-shell grain relative flex flex-col border-b border-white/8 elevation-lg lg:h-dvh lg:w-72 lg:shrink-0 lg:self-stretch lg:border-b-0 lg:border-r lg:border-r-white/8">
        <div className="flex flex-col lg:h-dvh">
          <div className="flex items-center justify-between gap-4 border-b border-white/8 px-5 py-5">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] p-2.5 text-white shadow-(--shadow-accent)">
                <Hexagon size={20} />
              </div>
              <div>
                <p className="font-display font-semibold leading-tight tracking-wide text-white">SPP</p>
                <p className="text-[11px] leading-tight text-white/45">Silknode Production Platform</p>
              </div>
            </div>
          </div>

          <nav className="flex gap-2 overflow-x-auto scrollbar-thin px-3 py-3 lg:flex-1 lg:flex-col lg:gap-1 lg:overflow-visible">
            {NAV.filter((item) => !item.roles || user?.is_superuser || user?.role === "super_admin" || item.roles.includes(user?.role)).map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  clsx(
                    "focus-ring group relative flex shrink-0 items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors duration-300",
                    "min-h-11 lg:w-full",
                    isActive ? "text-white!" : "text-white/80! hover:text-white!"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="nav-active-pill"
                        transition={{ type: "spring", stiffness: 380, damping: 32 }}
                        className="absolute inset-0 z-0 rounded-xl bg-[linear-gradient(120deg,var(--accent),var(--accent-bright))] shadow-(--shadow-accent)"
                      />
                    )}
                    <span className="relative z-10 flex items-center gap-3">
                      <Icon size={18} className="shrink-0" />
                      <span className="whitespace-nowrap">{label}</span>
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-white/8 p-3">
            <div className="mb-1 flex items-center gap-3 px-2 py-2">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-bold text-white ring-1 ring-white/15">
                {initials(user)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="truncate text-xs text-white/45">{user?.role_display}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="md"
              magnetic={false}
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="min-h-11! w-full justify-start! rounded-xl! border-transparent! bg-transparent! text-white/80! hover:bg-white/8! hover:text-white!"
            >
              <LogOut size={16} /> Chiqish
            </Button>
          </div>
        </div>
      </aside>

      <main data-lenis-prevent className="min-w-0 flex-1 lg:h-dvh lg:overflow-y-auto">
        <div className="mx-auto max-w-360 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>

      <HelpButton />
      <TutorialOverlay />
    </div>
    </TutorialProvider>
  );
}
