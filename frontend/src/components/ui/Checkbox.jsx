import { forwardRef } from "react";
import clsx from "clsx";
import { Check } from "lucide-react";

export const Checkbox = forwardRef(function Checkbox({ className, label, checked, ...props }, ref) {
  return (
    <label
      className={clsx(
        "inline-flex select-none items-center gap-2.5",
        props.disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <span className="relative inline-flex h-11 w-11 shrink-0 items-center justify-center -m-3">
        <input
          ref={ref}
          type="checkbox"
          checked={checked}
          className="peer absolute inset-0 !h-full !w-full cursor-pointer appearance-none focus:outline-none"
          {...props}
        />
        <span
          aria-hidden
          className={clsx(
            "pointer-events-none flex h-5 w-5 items-center justify-center rounded-lg border transition-all duration-200",
            "shadow-[inset_0_1px_2px_rgba(74,50,35,0.05)]",
            "peer-focus-visible:shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_25%,transparent)]",
            checked
              ? "border-[var(--accent)] bg-[var(--accent)]"
              : "border-[var(--border-strong)] bg-[var(--surface)] peer-hover:border-[var(--ink-faint)]"
          )}
        >
          {checked && <Check size={13} strokeWidth={3} className="check-pop text-white" />}
        </span>
      </span>
      {label && <span className="text-sm font-medium text-[var(--ink)]">{label}</span>}
    </label>
  );
});

export const Radio = forwardRef(function Radio({ className, label, checked, ...props }, ref) {
  return (
    <label
      className={clsx(
        "inline-flex select-none items-center gap-2.5",
        props.disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <span className="relative -m-3 inline-flex h-11 w-11 shrink-0 items-center justify-center">
        <input
          ref={ref}
          type="radio"
          checked={checked}
          className="peer absolute inset-0 !h-full !w-full cursor-pointer appearance-none focus:outline-none"
          {...props}
        />
        <span
          aria-hidden
          className={clsx(
            "pointer-events-none flex h-5 w-5 items-center justify-center rounded-full border transition-all duration-200",
            "shadow-[inset_0_1px_2px_rgba(74,50,35,0.05)]",
            "peer-focus-visible:shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_25%,transparent)]",
            checked
              ? "border-[var(--accent)] bg-[var(--surface)]"
              : "border-[var(--border-strong)] bg-[var(--surface)] peer-hover:border-[var(--ink-faint)]"
          )}
        >
          {checked && (
            <span className="check-pop h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
          )}
        </span>
      </span>
      {label && <span className="text-sm font-medium text-[var(--ink)]">{label}</span>}
    </label>
  );
});
