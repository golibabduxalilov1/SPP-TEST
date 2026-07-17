import { useId } from "react";
import clsx from "clsx";
import { motion } from "framer-motion";
import Button from "./Button";

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
          <Button
            key={opt.value}
            type="button"
            variant="ghost"
            size="sm"
            magnetic={false}
            onClick={() => onChange(opt.value)}
            aria-pressed={active}
            className={clsx(
              "relative !min-h-11 !rounded-lg !border-transparent !px-[18px] !py-2.5 !text-sm !font-medium",
              active
                ? "!text-[var(--ink)] hover:!bg-transparent"
                : "!text-[var(--ink-soft)] hover:!bg-black/[0.03] hover:!text-[var(--ink)]"
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
          </Button>
        );
      })}
    </div>
  );
}
