import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

const TutorialCtx = createContext(null);

export function TutorialProvider({ children }) {
  const [state, setState] = useState({ pageKey: null, steps: [], stepIndex: 0 });
  const triggerRef = useRef(null);
  const location = useLocation();
  const pathRef = useRef(location.pathname);

  const reset = useCallback(() => {
    setState({ pageKey: null, steps: [], stepIndex: 0 });
  }, []);

  // Closing must hand focus back to whatever triggered the tutorial (the
  // Tutorial tile button) — never leaves focus stranded on a removed element.
  const close = useCallback(() => {
    reset();
    const trigger = triggerRef.current;
    requestAnimationFrame(() => {
      if (trigger && document.contains(trigger)) trigger.focus();
    });
  }, [reset]);

  const start = useCallback((pageKey, steps) => {
    if (!steps?.length) return;
    triggerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setState({ pageKey, steps, stepIndex: 0 });
  }, []);

  // A route change must never leave a previous page's tutorial lingering on
  // the new page — this is a silent reset, not a user-triggered close, so it
  // skips the focus-restore side effect.
  useEffect(() => {
    if (pathRef.current === location.pathname) return;
    pathRef.current = location.pathname;
    reset();
  }, [location.pathname, reset]);

  const next = useCallback(() => {
    setState((s) => {
      if (!s.pageKey || s.stepIndex >= s.steps.length - 1) return s;
      return { ...s, stepIndex: s.stepIndex + 1 };
    });
  }, []);

  const prev = useCallback(() => {
    setState((s) => (s.pageKey ? { ...s, stepIndex: Math.max(0, s.stepIndex - 1) } : s));
  }, []);

  const value = {
    isActive: !!state.pageKey,
    pageKey: state.pageKey,
    steps: state.steps,
    stepIndex: state.stepIndex,
    start,
    next,
    prev,
    close,
    skip: close,
    finish: close,
  };

  return <TutorialCtx.Provider value={value}>{children}</TutorialCtx.Provider>;
}

export function useTutorial() {
  const ctx = useContext(TutorialCtx);
  if (!ctx) throw new Error("useTutorial must be used within TutorialProvider");
  return ctx;
}
