import { motion, useReducedMotion } from "framer-motion";
import { Book } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useTutorial } from "./TutorialContext";
import { TUTORIAL_PAGES, pageKeyForPath } from "./content";

export default function HelpButton() {
  const location = useLocation();
  const { start } = useTutorial();
  const prefersReducedMotion = useReducedMotion();
  const pageKey = pageKeyForPath(location.pathname);
  const page = pageKey ? TUTORIAL_PAGES[pageKey] : null;

  if (!page) return null;

  return (
    <motion.button
      type="button"
      onClick={() => start(pageKey, page.steps)}
      aria-label="Tutorialni boshlash"
      title="Tutorialni boshlash"
      whileHover={prefersReducedMotion ? undefined : { y: -2 }}
      whileTap={prefersReducedMotion ? undefined : { y: 0, scale: 0.95 }}
      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
      className="focus-ring fixed bottom-4 right-4 z-(--z-sticky) flex min-h-11 w-11 items-center justify-center rounded-xl border border-[color-mix(in_srgb,var(--accent-strong)_45%,transparent)] bg-[linear-gradient(135deg,var(--accent-bright),var(--accent))] text-white shadow-(--shadow-accent) transition-[background,box-shadow,filter] duration-300 ease-out hover:bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))] active:brightness-90 sm:bottom-6 sm:right-6"
    >
      <Book size={19} strokeWidth={2.2} aria-hidden="true" />
    </motion.button>
  );
}
