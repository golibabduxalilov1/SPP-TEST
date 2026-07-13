import { motion, useReducedMotion } from "framer-motion";
import { EASE_REVEAL } from "../../motion/reveal";

/**
 * Standard premium page header: eyebrow, big display title, subtitle, actions.
 * Animated reveal (respects reduced motion).
 */
export default function PageHeader({ eyebrow, title, subtitle, actions, className = "" }) {
  const reduce = useReducedMotion();
  const anim = (i) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 16 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay: i * 0.06, ease: EASE_REVEAL },
        };

  return (
    <div className={`flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between ${className}`}>
      <div className="min-w-0">
        {eyebrow && (
          <motion.p
            {...anim(0)}
            className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]"
          >
            <span className="h-1 w-6 rounded-full bg-[linear-gradient(90deg,var(--accent),var(--accent-2))]" />
            {eyebrow}
          </motion.p>
        )}
        <motion.h1 {...anim(1)} className="page-title text-[clamp(1.7rem,3vw,2.4rem)] font-semibold leading-tight text-[var(--ink)]">
          {title}
        </motion.h1>
        {subtitle && (
          <motion.p {...anim(2)} className="mt-1.5 text-sm text-[var(--ink-soft)]">
            {subtitle}
          </motion.p>
        )}
      </div>
      {actions && (
        <motion.div {...anim(2)} className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </motion.div>
      )}
    </div>
  );
}
