import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import Button from "../components/ui/Button";
import { useTutorial } from "./TutorialContext";

const GAP = 14;
const PADDING = 8;
const VIEWPORT_MARGIN = 12;
const MAX_LOOKUP_ATTEMPTS = 180;

function computePlacement(target, size) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const candidates = [
    { side: "bottom", top: target.bottom + GAP, left: target.left + target.width / 2 - size.width / 2 },
    { side: "top", top: target.top - GAP - size.height, left: target.left + target.width / 2 - size.width / 2 },
    { side: "right", top: target.top + target.height / 2 - size.height / 2, left: target.right + GAP },
    { side: "left", top: target.top + target.height / 2 - size.height / 2, left: target.left - GAP - size.width },
  ];
  const fits = (c) =>
    c.top >= VIEWPORT_MARGIN &&
    c.top + size.height <= vh - VIEWPORT_MARGIN &&
    c.left >= VIEWPORT_MARGIN &&
    c.left + size.width <= vw - VIEWPORT_MARGIN;

  const best = candidates.find(fits) || candidates[0];
  return {
    top: Math.min(Math.max(best.top, VIEWPORT_MARGIN), vh - size.height - VIEWPORT_MARGIN),
    left: Math.min(Math.max(best.left, VIEWPORT_MARGIN), vw - size.width - VIEWPORT_MARGIN),
  };
}

export default function TutorialOverlay() {
  const { isActive, steps, stepIndex, next, prev, skip, finish } = useTutorial();
  const step = isActive ? steps[stepIndex] : null;
  const prefersReducedMotion = useReducedMotion();

  const [rect, setRect] = useState(null);
  const [placement, setPlacement] = useState({ top: -9999, left: -9999, ready: false });
  const tooltipRef = useRef(null);

  useEffect(() => {
    if (!step) {
      setRect(null);
      return undefined;
    }

    let cancelled = false;
    let attempts = 0;
    setPlacement((p) => ({ ...p, ready: false }));

    function measure() {
      const el = document.querySelector(`[data-tutorial="${step.target}"]`);
      if (!el) {
        attempts += 1;
        if (attempts > MAX_LOOKUP_ATTEMPTS) {
          if (!cancelled) next();
          return;
        }
        requestAnimationFrame(measure);
        return;
      }
      if (attempts === 0) {
        el.scrollIntoView({ block: "center", inline: "nearest", behavior: prefersReducedMotion ? "auto" : "smooth" });
      }
      if (!cancelled) setRect(el.getBoundingClientRect());
    }

    measure();

    function onReflow() {
      const el = document.querySelector(`[data-tutorial="${step.target}"]`);
      if (el && !cancelled) setRect(el.getBoundingClientRect());
    }

    window.addEventListener("resize", onReflow);
    document.addEventListener("scroll", onReflow, true);
    const ro = new ResizeObserver(onReflow);
    ro.observe(document.body);

    return () => {
      cancelled = true;
      window.removeEventListener("resize", onReflow);
      document.removeEventListener("scroll", onReflow, true);
      ro.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step?.target]);

  useLayoutEffect(() => {
    if (!rect || !tooltipRef.current) return;
    const ttRect = tooltipRef.current.getBoundingClientRect();
    setPlacement({ ...computePlacement(rect, { width: ttRect.width, height: ttRect.height }), ready: true });
  }, [rect]);

  useEffect(() => {
    if (!isActive) return undefined;
    function onKey(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        skip();
      } else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        next();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prev();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isActive, next, prev, skip]);

  if (!isActive || !step || !rect) return null;

  const isFirst = stepIndex === 0;
  const isLast = stepIndex === steps.length - 1;

  const spotlightTop = Math.max(0, rect.top - PADDING);
  const spotlightLeft = Math.max(0, rect.left - PADDING);
  const spotlightStyle = {
    top: spotlightTop,
    left: spotlightLeft,
    width: Math.min(rect.width + PADDING * 2, window.innerWidth - spotlightLeft),
    height: Math.min(rect.height + PADDING * 2, window.innerHeight - spotlightTop),
  };

  const tooltipStyle = {
    top: placement.top,
    left: placement.left,
    opacity: placement.ready ? 1 : 0,
  };

  return createPortal(
    <div className="fixed inset-0" style={{ zIndex: "var(--z-tutorial)" }}>
      <div className="tutorial-spotlight pointer-events-none fixed rounded-2xl" style={spotlightStyle} />

      <div
        ref={tooltipRef}
        role="dialog"
        aria-modal="true"
        aria-label={step.title}
        className="tutorial-tooltip surface-panel fixed w-[92vw] max-w-[340px] rounded-2xl p-5"
        style={tooltipStyle}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--accent-strong)]">
            {stepIndex + 1}/{steps.length}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            magnetic={false}
            onClick={skip}
            aria-label="Yopish"
            className="!-m-2.5 !rounded-lg !border-transparent !bg-transparent !text-[var(--ink-faint)] hover:!bg-transparent hover:!text-[var(--ink)]"
          >
            <X size={16} />
          </Button>
        </div>

        <h3 className="font-display text-base font-semibold text-[var(--ink)]">{step.title}</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-[var(--ink-soft)]">{step.content}</p>

        <div className="mt-4 flex items-center gap-1.5">
          {steps.map((_, i) => (
            <span
              key={i}
              className="h-1.5 flex-1 rounded-full transition-colors duration-300"
              style={{ background: i <= stepIndex ? "var(--accent)" : "var(--border)" }}
            />
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            magnetic={false}
            onClick={skip}
            className="!rounded-lg !border-transparent !bg-transparent !px-2 !text-xs !font-medium !text-[var(--ink-faint)] hover:!bg-transparent hover:!text-[var(--ink-soft)]"
          >
            O'tkazib yuborish
          </Button>
          <div className="flex items-center gap-2">
            {!isFirst && (
              <Button size="sm" variant="outline" magnetic={false} onClick={prev}>
                <ChevronLeft size={14} /> Oldingi
              </Button>
            )}
            <Button size="sm" magnetic={false} onClick={isLast ? finish : next}>
              {isLast ? (
                "Tugatish"
              ) : (
                <>
                  Keyingi <ChevronRight size={14} />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
