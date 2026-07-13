import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import ShaderBackground from "./ShaderBackground";
import ParticleField from "./ParticleField";

const PRESETS = {
  light: { base: "#F7F1E8", a: "#B08D57", b: "#8B6544", particle: "#C6A473", bloom: 0.36, shape1: "#6B4423", shape2: "#B08D57" },
  dark: { base: "#2A1D14", a: "#B08D57", b: "#8B6544", particle: "#D8BB86", bloom: 0.72, shape1: "#C6A473", shape2: "#B08D57" },
};

/** Mouse-parallax camera. */
function Rig({ intensity = 1 }) {
  useFrame((state) => {
    state.camera.position.x += (state.pointer.x * 0.7 * intensity - state.camera.position.x) * 0.04;
    state.camera.position.y += (state.pointer.y * 0.45 * intensity - state.camera.position.y) * 0.04;
    state.camera.lookAt(0, 0, 0);
  });
  return null;
}

function FloatingShapes({ c1, c2, subtle }) {
  const s = subtle ? 0.15 : 1;
  return (
    <>
      <Float speed={1.4 * s} rotationIntensity={1.1 * s} floatIntensity={1.7 * s}>
        <mesh position={[-1.9, 0.6, 0]}>
          <icosahedronGeometry args={[1.15, 6]} />
          <MeshDistortMaterial color={c1} distort={subtle ? 0.15 : 0.36} speed={1.5 * s} roughness={0.22} metalness={0.2} />
        </mesh>
      </Float>
      {!subtle && (
        <Float speed={1.1} rotationIntensity={1.4} floatIntensity={1.3}>
          <mesh position={[2.1, -0.5, -0.5]}>
            <torusKnotGeometry args={[0.62, 0.2, 160, 32]} />
            <MeshDistortMaterial color={c2} distort={0.28} speed={1.2} roughness={0.18} metalness={0.35} />
          </mesh>
        </Float>
      )}
      {!subtle && (
        <Float speed={1.7} rotationIntensity={0.8} floatIntensity={2}>
          <mesh position={[0.6, 1.5, -1.5]}>
            <dodecahedronGeometry args={[0.42, 0]} />
            <MeshDistortMaterial color={c1} distort={0.2} speed={2} roughness={0.3} metalness={0.1} />
          </mesh>
        </Float>
      )}
    </>
  );
}

/**
 * Interactive 3D hero: shader gradient, particle depth, floating distorted
 * geometry with real lighting, bloom, and mouse-parallax camera.
 * Lazy-loaded (own chunk) and only mounted when the device can afford it.
 * `subtle` trims shape count/motion and parallax for calmer, less busy scenes (e.g. login).
 */
export default function HeroCanvas({ variant = "light", className = "", subtle = false }) {
  const p = PRESETS[variant] || PRESETS.light;
  return (
    <div className={`absolute inset-0 ${className}`}>
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0, 0, 6], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ position: "absolute", inset: 0 }}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[4, 6, 5]} intensity={1.5} color="#ffffff" />
        <pointLight position={[-5, -3, 2]} intensity={2.2} color={p.b} />
        <pointLight position={[5, 3, -2]} intensity={1.4} color={p.a} />

        <ShaderBackground colorA={p.a} colorB={p.b} base={p.base} />
        <ParticleField color={p.particle} count={variant === "dark" ? (subtle ? 220 : 1100) : (subtle ? 150 : 700)} />
        <FloatingShapes c1={p.shape1} c2={p.shape2} subtle={subtle} />
        <Rig intensity={subtle ? 0.12 : 1} />

        <EffectComposer disableNormalPass>
          <Bloom intensity={subtle ? p.bloom * 0.35 : p.bloom} luminanceThreshold={0.25} luminanceSmoothing={0.9} mipmapBlur radius={0.7} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
