import { useEffect, useState } from "react";

/**
 * Detects whether the device can afford heavy WebGL/3D + scroll choreography.
 * Gates the whole spectacle layer: low-power / touch-only / reduced-motion
 * devices fall back to static gradients and plain fades.
 */
function detectWebGL() {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

function read() {
  if (typeof window === "undefined") {
    return { reducedMotion: false, isTouch: false, isLowPower: false, hasWebGL: false, canRender3D: false };
  }
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isTouch = window.matchMedia("(pointer: coarse)").matches;
  const cores = navigator.hardwareConcurrency || 8;
  const mem = navigator.deviceMemory || 8;
  const isLowPower = cores <= 4 || mem <= 4;
  const hasWebGL = detectWebGL();
  const canRender3D = hasWebGL && !reducedMotion && !isLowPower;
  return { reducedMotion, isTouch, isLowPower, hasWebGL, canRender3D };
}

export function useDeviceCapability() {
  const [caps, setCaps] = useState(read);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setCaps(read());
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);

  return caps;
}

export default useDeviceCapability;
