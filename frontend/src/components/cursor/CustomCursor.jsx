import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { motion, useMotionValue, useSpring } from "framer-motion";

/**
 * Bespoke pointer: a lagging accent ring + a crisp dot. The ring swells and
 * turns to a soft accent wash over interactive elements (via [data-cursor] or
 * native a/button). Rendered only on fine-pointer, motion-friendly desktops;
 * never on touch, the terminal, or reduced-motion.
 */
export default function CustomCursor() {
  const { pathname } = useLocation();
  const [enabled, setEnabled] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [down, setDown] = useState(false);

  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const ringX = useSpring(x, { stiffness: 320, damping: 30, mass: 0.5 });
  const ringY = useSpring(y, { stiffness: 320, damping: 30, mass: 0.5 });
  const dotX = useSpring(x, { stiffness: 900, damping: 40 });
  const dotY = useSpring(y, { stiffness: 900, damping: 40 });

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ok = fine && !reduce && !pathname.startsWith("/terminal");
    setEnabled(ok);
    document.body.classList.toggle("cursor-none", ok);
    return () => document.body.classList.remove("cursor-none");
  }, [pathname]);

  useEffect(() => {
    if (!enabled) return undefined;
    const move = (e) => {
      x.set(e.clientX);
      y.set(e.clientY);
      const t = e.target;
      const interactive = t?.closest?.("a,button,[role='button'],input,select,textarea,label,[data-cursor]");
      setHovering(!!interactive);
    };
    const down = () => setDown(true);
    const up = () => setDown(false);
    window.addEventListener("mousemove", move);
    window.addEventListener("mousedown", down);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mousedown", down);
      window.removeEventListener("mouseup", up);
    };
  }, [enabled, x, y]);

  if (!enabled) return null;

  const ringSize = hovering ? 52 : 30;

  return (
    <>
      <motion.div
        aria-hidden
        style={{ translateX: ringX, translateY: ringY, zIndex: "var(--z-cursor)" }}
        className="pointer-events-none fixed left-0 top-0"
      >
        <motion.div
          animate={{
            width: ringSize,
            height: ringSize,
            opacity: hovering ? 0.9 : 0.55,
            scale: down ? 0.8 : 1,
            backgroundColor: hovering ? "rgba(107,68,35,0.14)" : "rgba(107,68,35,0)",
          }}
          transition={{ type: "spring", stiffness: 260, damping: 22 }}
          style={{ x: "-50%", y: "-50%", borderRadius: 9999, border: "1.5px solid rgba(107,68,35,0.7)" }}
        />
      </motion.div>
      <motion.div
        aria-hidden
        style={{ translateX: dotX, translateY: dotY, zIndex: "var(--z-cursor)" }}
        className="pointer-events-none fixed left-0 top-0"
      >
        <motion.div
          animate={{ scale: hovering ? 0 : 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 26 }}
          style={{ x: "-50%", y: "-50%", width: 6, height: 6, borderRadius: 9999, background: "var(--accent)" }}
        />
      </motion.div>
    </>
  );
}
