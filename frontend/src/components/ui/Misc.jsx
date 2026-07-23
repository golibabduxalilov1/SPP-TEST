import { Loader2, PackageOpen } from "lucide-react";

export function Spinner({ size = 18, className = "" }) {
  return <Loader2 size={size} className={`animate-spin text-(--accent) ${className}`} />;
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="glass-panel flex items-center gap-3 rounded-2xl px-5 py-4 elevation-sm">
        <Spinner size={24} />
        <span className="text-sm font-medium text-(--ink-soft)">Yuklanmoqda...</span>
      </div>
    </div>
  );
}

export function EmptyState({ title = "Hech narsa topilmadi", subtitle, icon: Icon = PackageOpen }) {
  return (
    <div className="relative flex flex-col items-center justify-center px-6 py-16 text-center text-(--ink-soft)">
      {/* Decorative wood-knot mark — faint, doesn't pull focus */}
      <div aria-hidden className="wood-knot pointer-events-none absolute top-8 h-28 w-28 opacity-[0.12]" />
      <div className="relative mb-4 rounded-2xl border border-[color-mix(in_srgb,var(--accent)_20%,transparent)] bg-(--accent-soft) p-4 text-(--accent-strong)">
        <Icon size={34} />
      </div>
      <p className="font-semibold text-(--ink)">{title}</p>
      {subtitle && <p className="text-sm mt-1 max-w-sm leading-6">{subtitle}</p>}
    </div>
  );
}
