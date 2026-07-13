import { useMemo } from "react";
import clsx from "clsx";
import { motion, useReducedMotion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { useMagnetic } from "../../motion/useMagnetic";

const motionComponentCache = new Map();
function getMotionComponent(Component) {
  if (!motionComponentCache.has(Component)) {
    motionComponentCache.set(Component, motion.create(Component));
  }
  return motionComponentCache.get(Component);
}

const VARIANTS = {
  primary:
    "text-white border-[color-mix(in_srgb,var(--accent-strong)_45%,transparent)] bg-[linear-gradient(135deg,var(--accent-bright),var(--accent))] shadow-[var(--shadow-accent)] hover:bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))]",
  secondary:
    "bg-[var(--surface)] hover:bg-[var(--surface-muted)] text-[var(--ink)] border-[var(--border-strong)] elevation-sm",
  outline:
    "bg-transparent hover:bg-[var(--accent-soft)] text-[var(--accent-strong)] border-[color-mix(in_srgb,var(--accent)_40%,transparent)]",
  danger:
    "bg-status-red hover:brightness-105 text-white border-transparent shadow-[0_2px_8px_rgba(220,38,38,0.22)]",
  success:
    "bg-status-green hover:brightness-105 text-white border-transparent shadow-[0_2px_8px_rgba(21,128,61,0.22)]",
  ghost:
    "bg-transparent hover:bg-[var(--surface-muted)] text-[var(--ink)] border-transparent",
};

const SIZES = {
  sm: "text-sm px-3.5 py-2 rounded-lg min-h-9",
  md: "text-sm px-5 py-2.5 rounded-lg min-h-10",
  lg: "text-[15px] px-6 py-3 rounded-lg min-h-11",
  xl: "text-lg px-8 py-4 rounded-xl terminal-tap",
  icon: "min-h-10 min-w-10 rounded-lg p-0",
};

export default function Button({
  variant = "primary",
  size = "md",
  className,
  as: Component = "button",
  magnetic = true,
  loading = false,
  disabled = false,
  children,
  ...props
}) {
  const prefersReducedMotion = useReducedMotion();
  const MotionComponent = useMemo(() => getMotionComponent(Component), [Component]);
  const mag = useMagnetic(size === "sm" ? 0.12 : 0.2);
  const useMag = magnetic && !prefersReducedMotion && size !== "sm" && !loading;
  const isDisabled = disabled || loading;

  return (
    <MotionComponent
      ref={useMag ? mag.ref : undefined}
      onMouseMove={useMag ? mag.handlers.onMouseMove : undefined}
      onMouseLeave={useMag ? mag.handlers.onMouseLeave : undefined}
      style={useMag ? mag.style : undefined}
      whileHover={prefersReducedMotion || isDisabled ? undefined : { y: -1 }}
      whileTap={prefersReducedMotion || isDisabled ? undefined : { y: 0, scale: 0.98 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={clsx(
        "group relative isolate inline-flex items-center justify-center gap-2 overflow-hidden border font-medium tracking-normal",
        "transition-[background,border-color,color,box-shadow,filter] duration-200 ease-out",
        "focus-ring disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {variant === "primary" && !prefersReducedMotion && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 translate-x-[-120%] bg-[linear-gradient(110deg,transparent,rgba(255,255,255,0.22),transparent)] transition-transform duration-700 ease-reveal group-hover:translate-x-[120%]"
        />
      )}
      <span className={clsx("inline-flex items-center justify-center gap-2", loading && "opacity-0")}>
        {children}
      </span>
      {loading && (
        <span aria-hidden className="absolute inset-0 flex items-center justify-center">
          <Loader2 size={size === "sm" ? 15 : 17} className="animate-spin" />
        </span>
      )}
    </MotionComponent>
  );
}
