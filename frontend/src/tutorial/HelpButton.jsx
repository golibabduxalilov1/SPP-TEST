import { HelpCircle } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useTutorial } from "./TutorialContext";
import { TUTORIAL_PAGES, pageKeyForPath } from "./content";
import Button from "../components/ui/Button";

export default function HelpButton() {
  const location = useLocation();
  const { start } = useTutorial();
  const pageKey = pageKeyForPath(location.pathname);
  const page = pageKey ? TUTORIAL_PAGES[pageKey] : null;

  if (!page) return null;

  return (
    <Button
      type="button"
      variant="primary"
      size="icon"
      magnetic={false}
      onClick={() => start(pageKey, page.steps)}
      aria-label="Sahifa bo'yicha yordam"
      title="Sahifa bo'yicha yordam"
      className="fixed! bottom-4 right-4 z-(--z-sticky) h-12! w-12! rounded-full! border-[color-mix(in_srgb,var(--accent-strong)_45%,transparent)]! bg-[linear-gradient(135deg,var(--accent-bright),var(--accent))]! text-white! shadow-(--shadow-accent)! hover:bg-[linear-gradient(135deg,var(--accent),var(--accent-strong))]! sm:bottom-6 sm:right-6"
    >
      <HelpCircle size={22} />
    </Button>
  );
}
