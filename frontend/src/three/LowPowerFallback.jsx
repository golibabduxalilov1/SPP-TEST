/**
 * Static, GPU-cheap stand-in for the 3D hero. Shown on low-power / touch /
 * reduced-motion devices. Pure CSS gradient mesh — no WebGL, no JS animation.
 */
export default function LowPowerFallback({ variant = "light", className = "" }) {
  const light = variant === "light";
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      style={{
        background: light
          ? "radial-gradient(38rem 30rem at 22% 18%, rgba(176,141,87,0.18), transparent 60%), radial-gradient(34rem 28rem at 82% 72%, rgba(107,68,35,0.14), transparent 60%), var(--canvas)"
          : "radial-gradient(40rem 32rem at 20% 20%, rgba(176,141,87,0.24), transparent 60%), radial-gradient(34rem 28rem at 84% 78%, rgba(107,68,35,0.24), transparent 60%), linear-gradient(175deg,#3F2A1B,#180F09)",
      }}
    >
      <div className="absolute inset-0 surface-noise opacity-40" />
    </div>
  );
}
