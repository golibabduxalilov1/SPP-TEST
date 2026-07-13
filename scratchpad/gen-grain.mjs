// Generates hand-drawn-style wood-grain line-art SVGs for the SPP frontend.
//   -> frontend/public/wood-grain.svg        (page background tile, 240x480)
//   -> frontend/public/wood-grain-dense.svg  (dark shells / cards, 200x360)
//   -> frontend/public/wood-knot.svg         (single decorative knot mark)
//
// Lines are vertical, gently wavy, with occasional oval knots that the fibres
// bow around — mimicking real timber. Waves use sine components whose periods
// divide the tile height, so the pattern tiles SEAMLESSLY top-to-bottom.
// Colour is deep walnut (#4A3223); CSS applies it at ~5% opacity, so strokes
// here are drawn solid and let the low opacity do the softening.
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, "../frontend/public");
mkdirSync(OUT, { recursive: true });

const INK = "#4A3223";

// tiny deterministic PRNG so regenerating gives the same texture
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

const round = (n) => Math.round(n * 100) / 100;

// A single wavy vertical fibre from y=0 to y=H. Bows sideways around any knots
// whose x is near this line. Vertically seamless: sine periods divide H.
function fibre(x0, H, waves, knots, rand) {
  const steps = 48;
  // per-line wave params — periods = H / k so sin(0)=sin(H)=0 (seamless)
  const comps = waves.map(({ k, amp }) => ({
    k,
    amp: amp * (0.6 + rand() * 0.8),
    phase: rand() * Math.PI * 2,
  }));
  const pts = [];
  for (let i = 0; i <= steps; i++) {
    const y = (H * i) / steps;
    let x = x0;
    for (const c of comps) {
      // phase kept 0 at endpoints via a window so seams stay exact
      x += c.amp * Math.sin((2 * Math.PI * c.k * y) / H);
    }
    // bow around nearby knots
    for (const kn of knots) {
      const dy = y - kn.cy;
      const within = Math.abs(dy) < kn.ry * 1.9;
      if (within) {
        const dx = x0 - kn.cx;
        const dist = Math.abs(dx) + 0.001;
        if (dist < kn.rx * 2.4) {
          const push = (kn.rx * 1.5 - dist) * Math.cos((dy / (kn.ry * 1.9)) * (Math.PI / 2));
          if (push > 0) x += Math.sign(dx || 1) * push;
        }
      }
    }
    pts.push([round(x), round(y)]);
  }
  // smooth polyline -> path with quadratic-ish segments
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 1; i < pts.length; i++) {
    const [px, py] = pts[i - 1];
    const [cx, cy] = pts[i];
    const mx = round((px + cx) / 2);
    const my = round((py + cy) / 2);
    d += ` Q${px} ${py} ${mx} ${my}`;
  }
  d += ` L${pts[pts.length - 1][0]} ${pts[pts.length - 1][1]}`;
  const w = round(0.4 + rand() * 0.7);
  const op = round(0.55 + rand() * 0.45);
  return `<path d="${d}" stroke="${INK}" stroke-width="${w}" fill="none" stroke-linecap="round" opacity="${op}"/>`;
}

// Concentric oval knot with a couple of rings, slightly irregular.
function knot(cx, cy, rx, ry, rand) {
  const parts = [];
  const rings = 2 + Math.floor(rand() * 2);
  for (let r = 0; r < rings; r++) {
    const f = 1 - r * (0.34 + rand() * 0.08);
    const rrx = round(rx * f);
    const rry = round(ry * f);
    const w = round(0.5 + rand() * 0.5);
    const wob = round((rand() - 0.5) * rx * 0.12);
    parts.push(
      `<ellipse cx="${round(cx + wob)}" cy="${round(cy)}" rx="${rrx}" ry="${rry}" ` +
        `stroke="${INK}" stroke-width="${w}" fill="none" opacity="${round(0.6 + rand() * 0.4)}"/>`
    );
  }
  // dark centre pip
  parts.push(
    `<ellipse cx="${round(cx)}" cy="${round(cy)}" rx="${round(rx * 0.12)}" ry="${round(ry * 0.14)}" fill="${INK}" opacity="0.75"/>`
  );
  return parts.join("");
}

function tile({ w, h, spacing, waves, knotSpecs, seed }) {
  const rand = rng(seed);
  const knots = (knotSpecs || []).map((k) => ({
    cx: k.cx,
    cy: k.cy,
    rx: k.rx,
    ry: k.ry,
  }));
  const fibres = [];
  for (let x = spacing * 0.5; x < w; x += spacing) {
    const jitter = (rand() - 0.5) * spacing * 0.4;
    fibres.push(fibre(round(x + jitter), h, waves, knots, rand));
  }
  const knotEls = knots.map((k) => knot(k.cx, k.cy, k.rx, k.ry, rand));
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` +
    fibres.join("") +
    knotEls.join("") +
    `</svg>`
  );
}

// --- page background: airy, one knot high, one low (both interior) ---
writeFileSync(
  resolve(OUT, "wood-grain.svg"),
  tile({
    w: 240,
    h: 480,
    spacing: 8,
    waves: [
      { k: 1, amp: 3.2 },
      { k: 2, amp: 1.6 },
      { k: 4, amp: 0.8 },
    ],
    knotSpecs: [
      { cx: 70, cy: 150, rx: 10, ry: 20 },
      { cx: 176, cy: 340, rx: 12, ry: 24 },
    ],
    seed: 20240710,
  })
);

// --- dense: tighter, thinner fibres for dark shells & card accents ---
writeFileSync(
  resolve(OUT, "wood-grain-dense.svg"),
  tile({
    w: 200,
    h: 360,
    spacing: 5,
    waves: [
      { k: 1, amp: 2.4 },
      { k: 2, amp: 1.3 },
      { k: 4, amp: 0.7 },
    ],
    knotSpecs: [{ cx: 132, cy: 210, rx: 9, ry: 18 }],
    seed: 99887766,
  })
);

// --- single knot mark for empty / loading states ---
{
  const rand = rng(1234567);
  const w = 120,
    h = 160;
  const knots = [{ cx: 60, cy: 80, rx: 26, ry: 46 }];
  const fibres = [];
  for (let x = 6; x < w; x += 9) {
    fibres.push(fibre(x, h, [{ k: 1, amp: 2.2 }, { k: 2, amp: 1.1 }], knots, rand));
  }
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` +
    fibres.join("") +
    knot(60, 80, 26, 46, rand) +
    `</svg>`;
  writeFileSync(resolve(OUT, "wood-knot.svg"), svg);
}

console.log("wrote wood-grain.svg, wood-grain-dense.svg, wood-knot.svg to", OUT);
