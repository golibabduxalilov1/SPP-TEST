import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import Lenis from "lenis";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * Global inertial smooth-scroll, driven by the GSAP ticker so ScrollTrigger
 * stays perfectly in sync. Disabled on the shop-floor terminal (scan/scroll
 * speed is sacred) and whenever the user prefers reduced motion.
 */
export default function LenisProvider({ children }) {
  const { pathname } = useLocation();

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isTerminal = pathname.startsWith("/terminal");
    if (reduce || isTerminal) return undefined;

    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.6,
    });

    lenis.on("scroll", ScrollTrigger.update);
    const onTick = (time) => lenis.raf(time * 1000);
    gsap.ticker.add(onTick);
    gsap.ticker.lagSmoothing(0);

    // Fresh measurements after route content mounts.
    const refresh = requestAnimationFrame(() => ScrollTrigger.refresh());

    return () => {
      cancelAnimationFrame(refresh);
      gsap.ticker.remove(onTick);
      lenis.destroy();
    };
  }, [pathname]);

  return children;
}
