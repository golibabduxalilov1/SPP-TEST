import { useId } from "react";
import clsx from "clsx";
import { motion, useReducedMotion } from "framer-motion";
import Button from "./Button";

export default function SegmentedControl({ options, value, onChange, className }) {
  const groupId = useId();
  const prefersReducedMotion = useReducedMotion();

  return (
    <div
      className={clsx(
        "flex w-fit max-w-full flex-wrap gap-1 rounded-[10px] border border-(--border-subtle) bg-(--surface-muted) p-0.75",
        "shadow-[inset_0_1px_2px_rgb(0_0_0/0.04)]",
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
              "relative min-h-8.25! rounded-lg! border-transparent! px-3.5! py-1.5! text-[0.8125rem]!",
              active
                ? "text-(--ink)! font-semibold! hover:bg-transparent!"
                : "text-(--ink-soft)! font-medium! hover:bg-black/2! hover:text-(--ink)!"
            )}
          >
            {active && (
              <motion.span
                layoutId={`${groupId}-active-pill`}
                transition={prefersReducedMotion ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 35 }}
                className="absolute inset-0 -z-0 rounded-lg bg-(--surface) elevation-sm"
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </Button>
        );
      })}
    </div>
  );
}
