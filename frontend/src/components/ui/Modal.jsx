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
          className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4"
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
            className={`wood-panel w-full ${widths[size]} rounded-[14px] border border-[var(--border)] bg-[var(--surface-raised)] elevation-lg`}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border-subtle)]">
              <h3 className="font-display text-base font-semibold tracking-tight text-[var(--ink)]">{title}</h3>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                magnetic={false}
                onClick={onClose}
                aria-label="Yopish"
                className="!min-h-9 !min-w-9 !rounded-full !text-[var(--ink-soft)] hover:!text-[var(--ink)]"
              >
                <X size={18} />
              </Button>
            </div>
            <div className="p-5 max-h-[70vh] overflow-y-auto scrollbar-thin">{children}</div>
            {footer && (
              <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[var(--border-subtle)]">
                {footer}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
