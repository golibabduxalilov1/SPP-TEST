import { useRef } from "react";
import { useMotionValue, useSpring, useReducedMotion } from "framer-motion";

/**
 * Magnetic hover — element is pulled toward the cursor while it's near.
 * Returns a ref, motion style {x, y}, and pointer handlers to spread onto a
 * `motion.*` element. No-op under reduced motion.
 *
 *   const magnetic = useMagnetic(0.35);
 *   <motion.button {...magnetic.handlers} ref={magnetic.ref} style={magnetic.style} />
 */
export function useMagnetic(strength = 0.35) {
  const ref = useRef(null);
  const reduce = useReducedMotion();
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, { stiffness: 220, damping: 18, mass: 0.4 });
  const y = useSpring(my, { stiffness: 220, damping: 18, mass: 0.4 });

  const onMouseMove = (e) => {
    if (reduce || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const relX = e.clientX - (rect.left + rect.width / 2);
    const relY = e.clientY - (rect.top + rect.height / 2);
    mx.set(relX * strength);
    my.set(relY * strength);
  };
  const onMouseLeave = () => {
    mx.set(0);
    my.set(0);
  };

  return {
    ref,
    style: reduce ? {} : { x, y },
    handlers: { onMouseMove, onMouseLeave },
  };
}

export default useMagnetic;
