import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, Table2, Factory, Users, AlertTriangle,
  Warehouse, BarChart3, LogOut, Tags, Hexagon, Menu, X, BookOpen,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useAuthStore } from "../store/authStore";
import Button from "../components/ui/Button";
import clsx from "clsx";
import { TutorialProvider } from "../tutorial/TutorialContext";
import TutorialOverlay from "../tutorial/TutorialOverlay";
import HelpButton from "../tutorial/HelpButton";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/orders", label: "Buyurtmalar", icon: ClipboardList },
  { to: "/customers", label: "Mijozlar", icon: Users },
  { to: "/tablo", label: "Ishlab chiqarish tablosi", icon: Table2 },
  { to: "/labels", label: "QR / Birka", icon: Tags },
  { to: "/machines", label: "Tsex va stanoklar", icon: Factory },
  { to: "/references", label: "Справочники", icon: BookOpen, roles: ["super_admin", "admin"] },
  { to: "/employees", label: "Xodimlar", icon: Users },
  { to: "/conflicts", label: "Konfliktlar", icon: AlertTriangle, roles: ["super_admin", "director", "manager", "master"] },
  { to: "/warehouse", label: "Tayyor ombor", icon: Warehouse, extra: "Qadoqlash" },
  { to: "/reports", label: "Hisobotlar", icon: BarChart3 },
];

function initials(user) {
  return `${user?.first_name?.[0] || ""}${user?.last_name?.[0] || ""}`.toUpperCase() || "U";
}

function MobileMenuIcon({ open }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={open ? "close" : "menu"}
        initial={{ opacity: 0, rotate: open ? -45 : 45, scale: 0.8 }}
        animate={{ opacity: 1, rotate: 0, scale: 1 }}
        exit={{ opacity: 0, rotate: open ? 45 : -45, scale: 0.8 }}
        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
        className="inline-flex"
      >
        {open ? <X size={22} /> : <Menu size={24} />}
      </motion.span>
    </AnimatePresence>
  );
}

export default function AdminLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (!navOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setNavOpen(false);
    };
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [navOpen]);

  return (
    <TutorialProvider>
    <div className="min-h-dvh bg-transparent lg:flex lg:h-dvh lg:items-stretch lg:overflow-hidden">
      <header className={clsx("brand-shell grain flex items-center justify-between gap-4 border-b border-white/8 px-4 py-4 lg:hidden", navOpen && "invisible")}>
        <div className="flex min-w-0 items-center gap-3">
          <div className="shrink-0 rounded-2xl bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] p-2.5 text-white shadow-(--shadow-accent)">
            <Hexagon size={20} />
          </div>
          <div className="min-w-0">
            <p className="font-display font-semibold leading-tight tracking-wide text-white">SPP</p>
            <p className="truncate text-[11px] leading-tight text-white/45">Silknode Production Platform</p>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          magnetic={false}
          onClick={() => setNavOpen(true)}
          aria-label="Menyuni ochish"
          aria-expanded={navOpen}
          aria-controls="admin-navigation"
          className="shrink-0 !rounded-xl !border-transparent !bg-transparent !text-white/80 hover:!bg-transparent hover:!text-white"
        >
          <MobileMenuIcon open={false} />
        </Button>
      </header>

      {navOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setNavOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        id="admin-navigation"
        className={clsx(
          "brand-shell !fixed inset-y-0 left-0 z-50 flex h-dvh w-72 max-w-[85vw] flex-col overflow-hidden border-r border-r-white/8 elevation-lg transition-[transform,visibility] duration-300 ease-in-out",
          navOpen ? "visible translate-x-0 delay-0" : "invisible -translate-x-full delay-300",
          "lg:visible lg:!static lg:h-dvh lg:w-64 lg:max-w-none lg:shrink-0 lg:translate-x-0 lg:self-stretch lg:delay-0 xl:w-72"
        )}
      >
        <div className="flex h-full flex-col lg:h-dvh">
          <div className="flex items-center justify-between gap-4 border-b border-white/8 px-5 py-5">
            <div className="flex min-w-0 items-center gap-3">
              <div className="shrink-0 rounded-2xl bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] p-2.5 text-white shadow-(--shadow-accent)">
                <Hexagon size={20} />
              </div>
              <div className="min-w-0">
                <p className="font-display font-semibold leading-tight tracking-wide text-white">SPP</p>
                <p className="truncate text-[11px] leading-tight text-white/45">Silknode Production Platform</p>
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              magnetic={false}
              onClick={() => setNavOpen(false)}
              aria-label="Menyuni yopish"
              className="shrink-0 !rounded-xl !border-transparent !bg-transparent !text-white/70 hover:!bg-transparent hover:!text-white lg:hidden"
            >
              <MobileMenuIcon open />
            </Button>
          </div>

          <nav className="flex flex-1 flex-col gap-1 overflow-x-hidden overflow-y-auto px-3 py-3">
            {NAV.filter((item) => !item.roles || user?.is_superuser || user?.role === "super_admin" || item.roles.includes(user?.role)).map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={() => setNavOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    "focus-ring group relative flex shrink-0 items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors duration-300",
                    "min-h-11 w-full",
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
        <div className="px-4 py-5 sm:px-6 lg:px-6 lg:py-8 xl:px-8">
          <Outlet />
        </div>
      </main>

      <HelpButton />
      <TutorialOverlay />
    </div>
    </TutorialProvider>
  );
}
