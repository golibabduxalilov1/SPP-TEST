import { HelpCircle } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useTutorial } from "./TutorialContext";
import { TUTORIAL_PAGES, pageKeyForPath } from "./content";

export default function HelpButton() {
  const location = useLocation();
  const { start } = useTutorial();
  const pageKey = pageKeyForPath(location.pathname);
  const page = pageKey ? TUTORIAL_PAGES[pageKey] : null;

  if (!page) return null;

  return (
    <button
      type="button"
      onClick={() => start(pageKey, page.steps)}
      aria-label="Sahifa bo'yicha yordam"
      title="Sahifa bo'yicha yordam"
      className="focus-ring fixed bottom-6 right-6 z-[var(--z-sticky)] flex h-12 w-12 items-center justify-center rounded-full border border-[color-mix(in_srgb,var(--accent-strong)_45%,transparent)] bg-[linear-gradient(135deg,var(--accent-bright),var(--accent))] text-white shadow-[var(--shadow-accent)] transition-transform duration-200 hover:scale-105 hover:bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))]"
    >
      <HelpCircle size={22} />
    </button>
  );
}
