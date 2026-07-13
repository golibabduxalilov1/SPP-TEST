import { Suspense, lazy } from "react";
import { useDeviceCapability } from "../hooks/useDeviceCapability";
import LowPowerFallback from "./LowPowerFallback";

// Heavy WebGL scene split into its own async chunk — never in the main bundle.
const HeroCanvas = lazy(() => import("./HeroCanvas"));

/**
 * Drop-in decorative 3D hero. Renders the WebGL scene only when the device can
 * afford it; otherwise a static CSS gradient. Always non-interactive backdrop.
 */
export default function Hero3D({ variant = "light", className = "", subtle = false }) {
  const { canRender3D } = useDeviceCapability();

  if (!canRender3D) {
    return <LowPowerFallback variant={variant} className={className} />;
  }

  return (
    <Suspense fallback={<LowPowerFallback variant={variant} className={className} />}>
      <HeroCanvas variant={variant} className={className} subtle={subtle} />
    </Suspense>
  );
}
