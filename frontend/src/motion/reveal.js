/**
 * Shared motion language. Organic easing only, per brief:
 *   enter → cubic-bezier(0.16, 1, 0.3, 1)
 *   hover → cubic-bezier(0.4, 0, 0.2, 1)
 * Reveals 600–800ms, stagger 80–120ms.
 */
export const EASE_REVEAL = [0.16, 1, 0.3, 1];
export const EASE_HOVER = [0.4, 0, 0.2, 1];
export const EASE_SPRING = [0.34, 1.56, 0.64, 1];

export const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.72, delay: i * 0.09, ease: EASE_REVEAL },
  }),
};

export const fadeIn = {
  hidden: { opacity: 0 },
  visible: (i = 0) => ({
    opacity: 1,
    transition: { duration: 0.6, delay: i * 0.08, ease: EASE_REVEAL },
  }),
};

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.94, y: 16 },
  visible: (i = 0) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.68, delay: i * 0.09, ease: EASE_REVEAL },
  }),
};

export const staggerContainer = {
  hidden: {},
  visible: (stagger = 0.09) => ({
    transition: { staggerChildren: stagger, delayChildren: 0.05 },
  }),
};

/** Standard whileInView props for scroll reveals. */
export const inViewProps = {
  initial: "hidden",
  whileInView: "visible",
  viewport: { once: true, margin: "-60px" },
};
