import { useRef, useMemo } from "react";
import * as THREE from "three";
import { extend, useFrame, useThree } from "@react-three/fiber";
import { shaderMaterial } from "@react-three/drei";

/** Flowing brass/forest mesh-gradient with subtle value noise. */
const GradientMaterial = shaderMaterial(
  {
    uTime: 0,
    uColorA: new THREE.Color("#6B4423"),
    uColorB: new THREE.Color("#B08D57"),
    uBase: new THREE.Color("#F7F1E8"),
    uMouse: new THREE.Vector2(0, 0),
  },
  /* glsl vertex */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  /* glsl fragment */ `
    uniform float uTime;
    uniform vec3 uColorA;
    uniform vec3 uColorB;
    uniform vec3 uBase;
    uniform vec2 uMouse;
    varying vec2 vUv;

    float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    float noise(vec2 p){
      vec2 i = floor(p); vec2 f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1,0)), u.x),
                 mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), u.x), u.y);
    }

    void main() {
      vec2 uv = vUv;
      float t = uTime * 0.05;
      vec2 mo = uMouse * 0.12;
      vec2 p1 = vec2(0.30 + 0.22 * sin(t * 1.3), 0.34 + 0.20 * cos(t * 1.1)) + mo;
      vec2 p2 = vec2(0.72 + 0.20 * cos(t * 0.9), 0.62 + 0.22 * sin(t * 1.4)) - mo;
      float n = noise(uv * 3.0 + t * 2.0) * 0.12;
      float d1 = distance(uv, p1);
      float d2 = distance(uv, p2);
      vec3 col = uBase;
      col = mix(col, uColorA, clamp(smoothstep(0.62, 0.0, d1) + n, 0.0, 1.0));
      col = mix(col, uColorB, clamp(smoothstep(0.55, 0.0, d2) + n, 0.0, 1.0));
      col = mix(uBase, col, 0.55);
      gl_FragColor = vec4(col, 1.0);
    }
  `
);
extend({ GradientMaterial });

export default function ShaderBackground({ colorA = "#6B4423", colorB = "#B08D57", base = "#F7F1E8" }) {
  const ref = useRef();
  const { viewport, pointer } = useThree();
  const uniforms = useMemo(
    () => ({
      a: new THREE.Color(colorA),
      b: new THREE.Color(colorB),
      base: new THREE.Color(base),
    }),
    [colorA, colorB, base]
  );

  useFrame((state) => {
    if (!ref.current) return;
    ref.current.uTime = state.clock.elapsedTime;
    ref.current.uMouse.lerp({ x: pointer.x, y: pointer.y }, 0.05);
  });

  return (
    <mesh position={[0, 0, -6]} scale={[viewport.width * 2.2, viewport.height * 2.2, 1]}>
      <planeGeometry args={[1, 1]} />
      {/* eslint-disable-next-line react/no-unknown-property */}
      <gradientMaterial ref={ref} uColorA={uniforms.a} uColorB={uniforms.b} uBase={uniforms.base} />
    </mesh>
  );
}
