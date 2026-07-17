import clsx from "clsx";
import { motion, useReducedMotion } from "framer-motion";

export default function Toggle({ checked, onChange, disabled, label, className, ...props }) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <label
      className={clsx(
        "inline-flex select-none items-center gap-2.5",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <span className="relative inline-flex h-11 w-11 shrink-0 items-center -my-2.5">
        <input
          type="checkbox"
          role="switch"
          aria-checked={checked}
          checked={checked}
          onChange={onChange}
          disabled={disabled}
          className="peer absolute inset-0 !h-full !w-full cursor-pointer appearance-none focus:outline-none"
          {...props}
        />
        <span
          aria-hidden
          className={clsx(
            "pointer-events-none h-6 w-11 rounded-full border transition-colors duration-300 ease-out",
            "shadow-[inset_0_1px_2px_rgba(74,50,35,0.10)]",
            "peer-focus-visible:shadow-[inset_0_1px_2px_rgba(74,50,35,0.10),0_0_0_3px_color-mix(in_srgb,var(--accent)_25%,transparent)]",
            checked
              ? "border-transparent bg-[var(--accent)]"
              : "border-[var(--border-strong)] bg-[var(--surface-muted)]"
          )}
        />
        <motion.span
          aria-hidden
          className="pointer-events-none absolute left-0.5 h-5 w-5 rounded-full bg-white shadow-[0_1px_3px_rgba(74,50,35,0.30),0_1px_1px_rgba(74,50,35,0.18)]"
          animate={{ x: checked ? 20 : 0 }}
          transition={prefersReducedMotion ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 32 }}
        />
      </span>
      {label && <span className="text-sm font-medium text-[var(--ink)]">{label}</span>}
    </label>
  );
}
