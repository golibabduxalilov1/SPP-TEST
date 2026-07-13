import { createContext, useCallback, useContext, useRef, useState } from "react";
import { useAuthStore } from "../store/authStore";
import { isTutorialSeen, markTutorialSeen } from "./storage";

const AUTO_START_DELAY = 400;

const TutorialCtx = createContext(null);

export function TutorialProvider({ children }) {
  const [state, setState] = useState({ pageKey: null, steps: [], stepIndex: 0 });
  const stateRef = useRef(state);
  stateRef.current = state;
  const userId = useAuthStore((s) => s.user?.id ?? "anon");

  const close = useCallback(() => {
    setState({ pageKey: null, steps: [], stepIndex: 0 });
  }, []);

  const start = useCallback((pageKey, steps) => {
    if (!steps?.length) return;
    setState({ pageKey, steps, stepIndex: 0 });
  }, []);

  const registerAndAutoStart = useCallback(
    (pageKey, steps) => {
      if (!steps?.length) return undefined;
      // A previous page's tutorial (never explicitly closed, e.g. navigated away via the nav
      // menu instead of Skip/Finish) must not linger once a different page has mounted.
      if (stateRef.current.pageKey && stateRef.current.pageKey !== pageKey) {
        close();
      }
      const id = setTimeout(() => {
        if (stateRef.current.pageKey === pageKey) return;
        if (isTutorialSeen(userId, pageKey)) return;
        markTutorialSeen(userId, pageKey);
        start(pageKey, steps);
      }, AUTO_START_DELAY);
      return () => clearTimeout(id);
    },
    [userId, start, close]
  );

  const next = useCallback(() => {
    setState((s) => {
      if (!s.pageKey) return s;
      if (s.stepIndex >= s.steps.length - 1) return { pageKey: null, steps: [], stepIndex: 0 };
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
    registerAndAutoStart,
    next,
    prev,
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
