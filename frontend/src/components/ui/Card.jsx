import { useRef } from "react";
import clsx from "clsx";
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from "framer-motion";
import { EASE_REVEAL } from "../../motion/reveal";

/**
 * Card. Optional scroll-reveal (animate) and pointer-driven 3D tilt (tilt).
 * Glass surface with layered soft shadow.
 */
export function Card({ className, children, animate = false, tilt = false, index = 0, ...props }) {
  const prefersReducedMotion = useReducedMotion();
  const ref = useRef(null);

  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const rx = useSpring(useTransform(py, [-0.5, 0.5], [6, -6]), { stiffness: 200, damping: 20 });
  const ry = useSpring(useTransform(px, [-0.5, 0.5], [-6, 6]), { stiffness: 200, damping: 20 });

  const enableTilt = tilt && !prefersReducedMotion;

  const handleMove = (e) => {
    if (!enableTilt || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    px.set((e.clientX - r.left) / r.width - 0.5);
    py.set((e.clientY - r.top) / r.height - 0.5);
  };
  const handleLeave = () => {
    px.set(0);
    py.set(0);
  };

  const base = "surface-panel rounded-2xl";

  if (!animate && !enableTilt) {
    return (
      <div className={clsx(base, "transition-shadow duration-300", className)} {...props}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={enableTilt ? handleMove : undefined}
      onMouseLeave={enableTilt ? handleLeave : undefined}
      initial={animate && !prefersReducedMotion ? { opacity: 0, y: 28 } : false}
      whileInView={animate && !prefersReducedMotion ? { opacity: 1, y: 0 } : undefined}
      viewport={animate ? { once: true, margin: "-60px" } : undefined}
      transition={{ duration: 0.7, delay: index * 0.08, ease: EASE_REVEAL }}
      style={enableTilt ? { rotateX: rx, rotateY: ry, transformPerspective: 900 } : undefined}
      className={clsx(base, "transition-shadow duration-300", className)}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function CardHeader({ title, subtitle, actions, className, ...props }) {
  return (
    <div
      className={clsx(
        "flex flex-col items-start justify-between gap-4 px-5 py-4 border-b border-[var(--border-subtle)] sm:flex-row sm:items-center",
        className
      )}
      {...props}
    >
      <div className="min-w-0">
        <h2 className="font-display text-base font-semibold tracking-tight text-[var(--ink)]">{title}</h2>
        {subtitle && <p className="text-sm text-[var(--ink-soft)] mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex w-full items-center gap-2 sm:w-auto">{actions}</div>}
    </div>
  );
}

export function CardBody({ className, children, ...props }) {
  return (
    <div className={clsx("p-5", className)} {...props}>
      {children}
    </div>
  );
}
