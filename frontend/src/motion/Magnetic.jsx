import { motion } from "framer-motion";
import { useMagnetic } from "./useMagnetic";

/**
 * Wraps children in a magnetic-hover container.
 * <Magnetic strength={0.4}><button>…</button></Magnetic>
 */
export default function Magnetic({ children, strength = 0.35, className, as = "div" }) {
  const magnetic = useMagnetic(strength);
  const Comp = motion[as] || motion.div;
  return (
    <Comp
      ref={magnetic.ref}
      style={{ ...magnetic.style, display: "inline-flex" }}
      {...magnetic.handlers}
      className={className}
    >
      {children}
    </Comp>
  );
}
