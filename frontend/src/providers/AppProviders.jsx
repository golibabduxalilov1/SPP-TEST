import LenisProvider from "../motion/LenisProvider";
import CustomCursor from "../components/cursor/CustomCursor";

/**
 * Global presentation shell (mounted inside BrowserRouter).
 * - LenisProvider: inertial smooth-scroll, auto-off on terminal + reduced-motion
 * - CustomCursor: bespoke desktop pointer, auto-off on touch/terminal/reduced-motion
 */
export default function AppProviders({ children }) {
  return (
    <LenisProvider>
      <CustomCursor />
      {children}
    </LenisProvider>
  );
}
