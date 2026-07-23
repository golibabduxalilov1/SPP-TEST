import { useEffect } from "react";
import { X } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import Button from "./Button";

export default function Modal({ open, onClose, title, children, footer, size = "md" }) {
  const prefersReducedMotion = useReducedMotion();
  const widths = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" };

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-(--z-modal) flex items-center justify-center p-3 sm:p-4"
          style={{ background: "rgba(42,29,20,0.34)", backdropFilter: "blur(3px)", WebkitBackdropFilter: "blur(3px)" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={typeof title === "string" ? title : undefined}
            initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className={`wood-panel flex max-h-[calc(100dvh-1.5rem)] w-full flex-col ${widths[size]} rounded-[14px] border border-(--border) bg-(--surface-raised) elevation-lg sm:max-h-[calc(100dvh-2rem)]`}
          >
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-(--border-subtle) px-4 py-3 sm:px-5 sm:py-4">
              <h3 className="min-w-0 wrap-break-word font-display text-base font-semibold tracking-tight text-(--ink)">{title}</h3>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                magnetic={false}
                onClick={onClose}
                aria-label="Yopish"
                className="min-h-11! min-w-11! rounded-lg! text-(--ink-soft)! hover:text-(--ink)!"
              >
                <X size={18} />
              </Button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4 scrollbar-thin sm:p-5">{children}</div>
            {footer && (
              <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-(--border-subtle) px-4 py-3 sm:px-5 sm:py-4">
                {footer}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
