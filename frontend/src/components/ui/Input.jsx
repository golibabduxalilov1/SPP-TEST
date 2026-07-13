import { forwardRef, isValidElement, cloneElement } from "react";
import clsx from "clsx";
import { Check, AlertCircle, ChevronDown } from "lucide-react";

const FIELD_BASE =
  "w-full rounded-lg border bg-[var(--surface)] px-3.5 py-2.5 text-sm text-[var(--ink)] " +
  "shadow-[inset_0_1px_2px_rgba(74,50,35,0.05)] " +
  "placeholder:text-[var(--ink-faint)] transition-[border-color,box-shadow,background-color] duration-[220ms] ease-out " +
  "focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:!border-[var(--border-strong)]";

const STATE_CLASSES = {
  default:
    "border-[var(--border-strong)] hover:border-[var(--ink-faint)] " +
    "focus:border-[var(--accent)] focus:shadow-[inset_0_1px_2px_rgba(74,50,35,0.05),0_0_0_3px_color-mix(in_srgb,var(--accent)_16%,transparent)]",
  error:
    "border-status-red hover:border-status-red field-shake " +
    "focus:border-status-red focus:shadow-[inset_0_1px_2px_rgba(74,50,35,0.05),0_0_0_3px_color-mix(in_srgb,var(--color-status-red)_16%,transparent)]",
  success:
    "border-status-green hover:border-status-green " +
    "focus:border-status-green focus:shadow-[inset_0_1px_2px_rgba(74,50,35,0.05),0_0_0_3px_color-mix(in_srgb,var(--color-status-green)_16%,transparent)]",
};

function StateIcon({ state }) {
  if (state !== "error" && state !== "success") return null;
  return (
    <span
      aria-hidden
      className={clsx(
        "check-pop pointer-events-none absolute right-3 top-1/2 -translate-y-1/2",
        state === "error" ? "text-status-red" : "text-status-green"
      )}
    >
      {state === "error" ? <AlertCircle size={16} /> : <Check size={16} />}
    </span>
  );
}

export function Label({ children, className, required }) {
  return (
    <label className={clsx("block text-sm font-semibold text-(--ink) mb-1.5", className)}>
      {children}
      {required && <span className="ml-0.5 text-status-red">*</span>}
    </label>
  );
}

export const Input = forwardRef(function Input({ className, state = "default", ...props }, ref) {
  const showIcon = state === "error" || state === "success";
  return (
    <div className="relative">
      <input
        ref={ref}
        aria-invalid={state === "error" || undefined}
        className={clsx(FIELD_BASE, STATE_CLASSES[state] || STATE_CLASSES.default, showIcon && "pr-10", className)}
        {...props}
      />
      <StateIcon state={state} />
    </div>
  );
});

export function Select({ className, children, state = "default", ...props }) {
  return (
    <div className="relative">
      <select
        aria-invalid={state === "error" || undefined}
        className={clsx(
          FIELD_BASE,
          STATE_CLASSES[state] || STATE_CLASSES.default,
          "cursor-pointer appearance-none pr-9",
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden
        size={16}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-(--ink-soft) transition-transform duration-200"
      />
    </div>
  );
}

export function Textarea({ className, state = "default", ...props }) {
  return (
    <div className="relative">
      <textarea
        aria-invalid={state === "error" || undefined}
        className={clsx(FIELD_BASE, STATE_CLASSES[state] || STATE_CLASSES.default, className)}
        {...props}
      />
    </div>
  );
}

export function Field({ label, children, hint, error, success, required }) {
  const state = error ? "error" : success ? "success" : "default";
  const child = isValidElement(children) && state !== "default" ? cloneElement(children, { state }) : children;

  return (
    <div>
      {label && <Label required={required}>{label}</Label>}
      {child}
      {error ? (
        <p className="mt-1.5 flex items-center gap-1 text-xs font-medium text-status-red">
          <AlertCircle size={13} className="shrink-0" /> {error}
        </p>
      ) : success ? (
        <p className="mt-1.5 flex items-center gap-1 text-xs font-medium text-status-green">
          <Check size={13} className="shrink-0" /> {success}
        </p>
      ) : (
        hint && <p className="mt-1 text-xs text-(--ink-soft)">{hint}</p>
      )}
    </div>
  );
}
