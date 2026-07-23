import clsx from "clsx";
import { motion, useReducedMotion } from "framer-motion";
import { EASE_REVEAL } from "../../motion/reveal";

const TONES = {
  accent: "text-white bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] shadow-(--shadow-accent)",
  wood: "text-white bg-[linear-gradient(135deg,var(--accent),var(--accent-bright))] shadow-(--shadow-accent)", // legacy alias
  signal: "text-white bg-[linear-gradient(135deg,var(--accent-2),var(--accent-2-bright))] shadow-[0_8px_22px_rgba(71,93,53,0.30)]",
  green: "text-status-green bg-status-green-bg",
  red: "text-status-red bg-status-red-bg",
  orange: "text-status-orange bg-status-orange-bg",
  blue: "text-status-blue bg-status-blue-bg",
};

export default function StatCard({ icon: Icon, label, value, hint, tone = "accent", index = 0, className }) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      initial={prefersReducedMotion ? undefined : { opacity: 0, y: 24 }}
      animate={prefersReducedMotion ? undefined : { opacity: 1, y: 0 }}
      transition={{ duration: 0.62, delay: index * 0.08, ease: EASE_REVEAL }}
      whileHover={prefersReducedMotion ? undefined : { y: -5 }}
      className={clsx("group h-full", className)}
    >
      <div className="surface-panel h-full rounded-2xl p-5 flex items-start gap-4 transition-shadow duration-300 group-hover:elevation-lg">
        <div className={clsx("rounded-2xl p-3 transition-transform duration-300 group-hover:scale-105", TONES[tone] || TONES.accent)}>
          {Icon && <Icon size={22} />}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-(--ink-soft)">{label}</p>
          <p className="mt-0.5 truncate font-display text-2xl font-semibold tracking-tight text-(--ink) tabular">{value}</p>
          {hint && <p className="text-xs text-(--ink-soft) mt-1">{hint}</p>}
        </div>
      </div>
    </motion.div>
  );
}
