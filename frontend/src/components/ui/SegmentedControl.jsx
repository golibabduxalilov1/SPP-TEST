import { useId } from "react";
import clsx from "clsx";
import { motion } from "framer-motion";

export default function SegmentedControl({ options, value, onChange, className }) {
  const groupId = useId();

  return (
    <div
      className={clsx(
        "flex w-fit max-w-full flex-wrap gap-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-muted)] p-1",
        "shadow-[inset_0_1px_2px_rgba(74,50,35,0.06)]",
        className
      )}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            aria-pressed={active}
            className={clsx(
              "focus-ring relative min-h-9 rounded-lg px-4 py-1.5 text-sm font-medium transition-colors duration-200",
              active ? "text-[var(--ink)]" : "text-[var(--ink-soft)] hover:bg-black/[0.03] hover:text-[var(--ink)]"
            )}
          >
            {active && (
              <motion.span
                layoutId={`${groupId}-active-pill`}
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
                className="absolute inset-0 -z-0 rounded-lg bg-[var(--surface)] elevation-sm"
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
