import clsx from "clsx";

// progress = (bajarilgan / jami_reja) * 100, clamped to 0–100. A missing or
// zero total (division-by-zero) resolves to 0% instead of NaN/Infinity.
export function computeProgressPercent(completed, total) {
  const numerator = Number(completed);
  const denominator = Number(total);
  if (!denominator || denominator <= 0 || !Number.isFinite(numerator)) return 0;
  const pct = (numerator / denominator) * 100;
  if (!Number.isFinite(pct)) return 0;
  return Math.min(100, Math.max(0, pct));
}

// 0–30% to'q sariq, 31–70% sariq, 71–99% ko'k, 100% yashil.
function fillColorClass(percent) {
  if (percent >= 100) return "bg-status-green";
  if (percent > 70) return "bg-status-blue";
  if (percent > 30) return "bg-status-yellow";
  return "bg-status-orange";
}

// Compact "amount ... percent%" header over a color-coded fill track — reacts
// to prop changes on its own, so re-rendering the parent with fresh data is
// enough to animate the bar without a page reload.
export default function ProgressBar({ percent, amountLabel, className }) {
  const pct = Math.min(100, Math.max(0, Math.round(percent) || 0));
  return (
    <div className={clsx("w-full", className)}>
      <div className="mb-1 flex items-center justify-between gap-1 text-[10px] font-semibold tabular leading-tight">
        {amountLabel != null && <span className="truncate opacity-80">{amountLabel}</span>}
        <span className="shrink-0">{pct}%</span>
      </div>
      <div
        className="h-1.5 w-full min-w-[2.5rem] overflow-hidden rounded-full bg-status-gray-bg"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={clsx("h-full rounded-full transition-[width] duration-500 ease-out", fillColorClass(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
