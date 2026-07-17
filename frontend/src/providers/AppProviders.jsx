import LenisProvider from "../motion/LenisProvider";

/**
 * Global presentation shell (mounted inside BrowserRouter).
 * - LenisProvider: inertial smooth-scroll, auto-off on terminal + reduced-motion
 */
export default function AppProviders({ children }) {
  return (
    <LenisProvider>
      {children}
    </LenisProvider>
  );
}
