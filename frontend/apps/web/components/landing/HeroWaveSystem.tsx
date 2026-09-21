'use client';

import React, { useEffect, useRef } from 'react';
import { useReducedMotion } from 'framer-motion';

export interface RibbonStrandConfig {
  id: number;
  y0: number;
  drapeSlope: number;
  drapeCurve: number;
  amp1: number;
  k1: number;
  amp2: number;
  k2: number;
  phase1: number;
  phase2: number;
  speed: number;
  strokeWidth: number;
  opacity: number;
  tier: 'hairline' | 'secondary' | 'primary' | 'ambient';
  gradType: 'subtle' | 'primary' | 'secondary' | 'accent';
}

// ==========================================================
// SHARED WAVE MOTION & GEOMETRY (SOURCE OF TRUTH: DARK MODE)
// Both Light and Dark modes share the exact same strand counts,
// origin points, endpoints, phases, amplitudes, speeds, and bundles.
// ==========================================================
const DESKTOP_STRAND_COUNT = 22;
const TABLET_STRAND_COUNT = 16;
const MOBILE_STRAND_COUNT = 10;
const HERO_CENTER_X = 720;

function buildSharedRibbonStrands(side: 'left' | 'right'): RibbonStrandConfig[] {
  const isLeft = side === 'left';
  const strands: RibbonStrandConfig[] = [];

  for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
    let y0 = 530;
    let drapeSlope = 0;
    let drapeCurve = 0;
    let amp1 = 45;
    let k1 = 1.6;
    let amp2 = 20;
    let k2 = 2.8;
    let phase1 = i * 0.75 + (isLeft ? 0 : 1.95);
    let phase2 = i * 1.1 + (isLeft ? 1.2 : 0.45);
    let speed = 0.75 + (i % 4) * 0.12;
    let strokeWidth = 0.65;
    let opacity = 0.25;
    let tier: RibbonStrandConfig['tier'] = 'hairline';
    let gradType: RibbonStrandConfig['gradType'] = 'subtle';

    if (i < 5) {
      // BUNDLE 1: Upper bundle (Strands 0-4)
      const u = i / 4;
      y0 = isLeft ? 510 - u * 25 : 515 - u * 25;
      drapeSlope = isLeft ? -220 - u * 60 : -200 - u * 70;
      drapeCurve = isLeft ? -40 + u * 20 : -35 + u * 20;
      amp1 = 40 + u * 15;
      k1 = 1.4 + u * 0.3;
      amp2 = 18 + u * 8;
      k2 = 2.6 + u * 0.4;

      if (i === 2) {
        strokeWidth = 1.45;
        opacity = 0.58;
        tier = 'primary';
        gradType = 'accent';
      } else if (i === 3) {
        strokeWidth = 0.92;
        opacity = 0.40;
        tier = 'secondary';
        gradType = 'primary';
      } else {
        strokeWidth = 0.62;
        opacity = 0.25;
        tier = 'hairline';
        gradType = 'subtle';
      }
    } else if (i < 14) {
      // BUNDLE 2: Middle ribbon (Strands 5-13)
      const u = (i - 5) / 8;
      y0 = isLeft ? 530 + (u - 0.5) * 45 : 525 + (u - 0.5) * 45;
      const isEven = (i - 5) % 2 === 0;
      drapeSlope = isEven ? -40 - u * 30 : 50 + u * 30;
      drapeCurve = isEven ? 30 : -30;
      amp1 = 55 + u * 20;
      k1 = 1.75 + (isEven ? 0.2 : -0.2);
      amp2 = 24;
      k2 = 3.2;
      phase1 = (i - 5) * 0.9 + (isEven ? 0 : Math.PI);
      phase2 = (i - 5) * 1.3 + (isEven ? Math.PI * 0.5 : -Math.PI * 0.5);

      if (i === 7) {
        strokeWidth = 1.5;
        opacity = 0.60;
        tier = 'primary';
        gradType = 'primary';
      } else if (i === 11) {
        strokeWidth = 1.4;
        opacity = 0.54;
        tier = 'primary';
        gradType = 'secondary';
      } else if (i === 6) {
        strokeWidth = 1.0;
        opacity = 0.42;
        tier = 'secondary';
        gradType = 'secondary';
      } else if (i === 9 || i === 13) {
        strokeWidth = 0.92;
        opacity = 0.38;
        tier = 'secondary';
        gradType = 'primary';
      } else {
        strokeWidth = 0.65;
        opacity = 0.26;
        tier = 'hairline';
        gradType = 'subtle';
      }
    } else if (i < 19) {
      // BUNDLE 3: Lower bundle (Strands 14-18)
      const u = (i - 14) / 4;
      y0 = isLeft ? 550 + u * 20 : 545 + u * 20;
      drapeSlope = isLeft ? 200 + u * 50 : 210 + u * 55;
      drapeCurve = isLeft ? 40 - u * 15 : 45 - u * 15;
      amp1 = 45 + u * 12;
      k1 = 1.5 + u * 0.25;
      amp2 = 20;
      k2 = 2.7;

      if (i === 16) {
        strokeWidth = 1.35;
        opacity = 0.52;
        tier = 'primary';
        gradType = 'accent';
      } else if (i === 17) {
        strokeWidth = 0.88;
        opacity = 0.38;
        tier = 'secondary';
        gradType = 'primary';
      } else {
        strokeWidth = 0.65;
        opacity = 0.25;
        tier = 'hairline';
        gradType = 'subtle';
      }
    } else {
      // Ambient strands (Strands 19-21)
      const u = (i - 19) / 2;
      y0 = u === 0 ? 490 : u === 1 ? 570 : 530;
      drapeSlope = u === 0 ? -380 : u === 1 ? 340 : -140;
      drapeCurve = 0;
      amp1 = 20;
      k1 = 1.2;
      amp2 = 10;
      k2 = 2.0;
      strokeWidth = 0.52;
      opacity = 0.22;
      tier = 'ambient';
      gradType = 'subtle';
    }

    strands.push({
      id: i,
      y0,
      drapeSlope,
      drapeCurve,
      amp1,
      k1,
      amp2,
      k2,
      phase1,
      phase2,
      speed,
      strokeWidth,
      opacity,
      tier,
      gradType,
    });
  }

  return strands;
}

const leftStrands = buildSharedRibbonStrands('left');
const rightStrands = buildSharedRibbonStrands('right');

// ==========================================================
// LIGHT MODE VISUAL SPECIFICATIONS (Per-strand styling)
// Applied strictly AFTER geometry is calculated.
// Hierarchy:
// - Hero strands (~18%): 1.50-1.70px, opacity 0.78-0.86
// - Medium strands (~23%): 1.20-1.28px, opacity 0.62-0.68
// - Subtle strands (~59%): 0.80-0.90px, opacity 0.48-0.54
// Colors: Periwinkle (#6F86E8), Cyan (#45C4DB), Lavender (#9B7DE3),
//         Soft Blue (#6FA9ED), Subtle Ice (#9EAFD4)
// ==========================================================
interface LightVisualConfig {
  grad: 'periwinkle_1' | 'periwinkle_2' | 'blue' | 'cyan_1' | 'cyan_2' | 'lavender_1' | 'lavender_2' | 'ice';
  width: number;
  opacity: number;
}

const LEFT_LIGHT_VISUALS: LightVisualConfig[] = [
  { grad: 'ice', width: 0.85, opacity: 0.50 },          // 0: Subtle Ice
  { grad: 'periwinkle_1', width: 0.90, opacity: 0.54 }, // 1: Primary Periwinkle
  { grad: 'cyan_1', width: 1.65, opacity: 0.84 },       // 2: HERO Pastel Cyan (Shine A)
  { grad: 'periwinkle_2', width: 1.25, opacity: 0.66 }, // 3: Medium Secondary Periwinkle
  { grad: 'blue', width: 0.85, opacity: 0.50 },         // 4: Subtle Soft Blue
  { grad: 'periwinkle_1', width: 0.90, opacity: 0.54 }, // 5: Subtle Primary Periwinkle
  { grad: 'blue', width: 1.25, opacity: 0.65 },         // 6: Medium Soft Blue
  { grad: 'periwinkle_1', width: 1.70, opacity: 0.86 }, // 7: HERO Primary Periwinkle (Shine B)
  { grad: 'ice', width: 0.85, opacity: 0.48 },          // 8: Subtle Ice
  { grad: 'lavender_1', width: 1.20, opacity: 0.64 },   // 9: Medium Lavender
  { grad: 'periwinkle_2', width: 0.88, opacity: 0.52 }, // 10: Subtle Secondary Periwinkle
  { grad: 'lavender_1', width: 1.55, opacity: 0.80 },   // 11: HERO Pastel Lavender
  { grad: 'blue', width: 0.85, opacity: 0.50 },         // 12: Subtle Soft Blue
  { grad: 'cyan_2', width: 1.20, opacity: 0.64 },       // 13: Medium Secondary Cyan
  { grad: 'ice', width: 0.85, opacity: 0.48 },          // 14: Subtle Ice
  { grad: 'periwinkle_1', width: 0.90, opacity: 0.54 }, // 15: Subtle Primary Periwinkle
  { grad: 'cyan_1', width: 1.50, opacity: 0.78 },       // 16: HERO Pastel Cyan
  { grad: 'lavender_2', width: 1.20, opacity: 0.62 },   // 17: Medium Secondary Lavender
  { grad: 'periwinkle_2', width: 0.85, opacity: 0.48 }, // 18: Subtle Secondary Periwinkle
  { grad: 'ice', width: 0.80, opacity: 0.48 },          // 19: Ambient Ice
  { grad: 'blue', width: 0.85, opacity: 0.50 },         // 20: Ambient Soft Blue
  { grad: 'ice', width: 0.80, opacity: 0.48 },          // 21: Ambient Ice
];

const RIGHT_LIGHT_VISUALS: LightVisualConfig[] = [
  { grad: 'lavender_2', width: 0.90, opacity: 0.54 },   // 0: Subtle Secondary Lavender
  { grad: 'lavender_1', width: 1.28, opacity: 0.68 },   // 1: Medium Lavender
  { grad: 'lavender_1', width: 1.70, opacity: 0.86 },   // 2: HERO Signature Lavender Bloom (Shine A)
  { grad: 'cyan_1', width: 1.60, opacity: 0.82 },       // 3: HERO Pastel Cyan
  { grad: 'periwinkle_1', width: 0.90, opacity: 0.54 }, // 4: Subtle Primary Periwinkle
  { grad: 'ice', width: 0.85, opacity: 0.48 },          // 5: Subtle Ice
  { grad: 'periwinkle_1', width: 0.90, opacity: 0.54 }, // 6: Subtle Primary Periwinkle
  { grad: 'cyan_2', width: 1.65, opacity: 0.84 },       // 7: HERO Secondary Cyan (Shine B)
  { grad: 'blue', width: 1.25, opacity: 0.66 },         // 8: Medium Soft Blue
  { grad: 'periwinkle_2', width: 0.90, opacity: 0.54 }, // 9: Subtle Secondary Periwinkle
  { grad: 'lavender_1', width: 1.20, opacity: 0.62 },   // 10: Medium Lavender
  { grad: 'periwinkle_1', width: 1.55, opacity: 0.80 }, // 11: HERO Primary Periwinkle
  { grad: 'blue', width: 0.85, opacity: 0.50 },         // 12: Subtle Soft Blue
  { grad: 'periwinkle_2', width: 1.20, opacity: 0.64 }, // 13: Medium Secondary Periwinkle
  { grad: 'cyan_1', width: 1.25, opacity: 0.66 },       // 14: Medium Pastel Cyan
  { grad: 'periwinkle_1', width: 0.90, opacity: 0.54 }, // 15: Subtle Primary Periwinkle
  { grad: 'blue', width: 1.50, opacity: 0.78 },         // 16: HERO Soft Blue
  { grad: 'lavender_2', width: 1.20, opacity: 0.62 },   // 17: Medium Secondary Lavender
  { grad: 'periwinkle_2', width: 0.85, opacity: 0.48 }, // 18: Subtle Secondary Periwinkle
  { grad: 'ice', width: 0.80, opacity: 0.48 },          // 19: Ambient Ice
  { grad: 'blue', width: 0.85, opacity: 0.50 },         // 20: Ambient Soft Blue
  { grad: 'ice', width: 0.80, opacity: 0.48 },          // 21: Ambient Ice
];

// Precompute CSS rules for all 22 strands (zero runtime string allocation in RAF)
function generatePrecomputedStrandCSS(): string {
  const lines: string[] = [];

  for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
    const lDark = leftStrands[i];
    const lLight = LEFT_LIGHT_VISUALS[i];
    lines.push(`
      .strand-left-${i} {
        stroke: url(#leftLightGrad_${lLight.grad});
        stroke-width: ${lLight.width}px;
        stroke-opacity: ${lLight.opacity};
      }
      .dark .strand-left-${i} {
        stroke: url(#leftDarkGrad_${lDark.gradType});
        stroke-width: ${lDark.strokeWidth}px;
        stroke-opacity: ${lDark.opacity};
      }
    `);

    const rDark = rightStrands[i];
    const rLight = RIGHT_LIGHT_VISUALS[i];
    lines.push(`
      .strand-right-${i} {
        stroke: url(#rightLightGrad_${rLight.grad});
        stroke-width: ${rLight.width}px;
        stroke-opacity: ${rLight.opacity};
      }
      .dark .strand-right-${i} {
        stroke: url(#rightDarkGrad_${rDark.gradType});
        stroke-width: ${rDark.strokeWidth}px;
        stroke-opacity: ${rDark.opacity};
      }
    `);
  }

  return lines.join('\n');
}

const PRECOMPUTED_STRAND_CSS = generatePrecomputedStrandCSS();

// Fast evaluation points buffer (5 points)
const PTS_X = [0, 0, 0, 0, 0];
const PTS_Y = [0, 0, 0, 0, 0];
const STEPS = [0, 0.22, 0.48, 0.74, 1.0];

// THE SINGLE SOURCE OF TRUTH FOR WAVE PATHS (LOCKED DARK MODE MATHEMATICS)
// Originates at center (HERO_CENTER_X) behind the smartphone and flows outward.
function computeSharedRibbonPath(strand: RibbonStrandConfig, t: number, side: 'left' | 'right'): string {
  const isLeft = side === 'left';
  const startX = HERO_CENTER_X + (isLeft ? -15 : 15);
  const endX = isLeft ? -50 : 1490;
  const totalDx = endX - startX;

  for (let idx = 0; idx < 5; idx++) {
    const s = STEPS[idx];
    const x = startX + s * totalDx;
    const env = Math.pow(Math.sin(s * Math.PI * 0.5), 0.85);

    const w1 = Math.sin(s * strand.k1 * Math.PI * 2 + t * 0.0009 * strand.speed + strand.phase1);
    const w2 = Math.cos(s * strand.k2 * Math.PI * 2 - t * 0.0005 * strand.speed + strand.phase2);

    const drape = strand.drapeSlope * s + strand.drapeCurve * s * s;
    const y = strand.y0 + drape + (strand.amp1 * w1 + strand.amp2 * w2) * env;

    PTS_X[idx] = x;
    PTS_Y[idx] = y;
  }

  return buildBezierFromPoints();
}

function buildBezierFromPoints(): string {
  let d = `M ${PTS_X[0].toFixed(1)},${PTS_Y[0].toFixed(1)}`;
  for (let i = 0; i < 4; i++) {
    const p0x = i > 0 ? PTS_X[i - 1] : PTS_X[i];
    const p0y = i > 0 ? PTS_Y[i - 1] : PTS_Y[i];
    const p1x = PTS_X[i];
    const p1y = PTS_Y[i];
    const p2x = PTS_X[i + 1];
    const p2y = PTS_Y[i + 1];
    const p3x = i + 2 < 5 ? PTS_X[i + 2] : p2x;
    const p3y = i + 2 < 5 ? PTS_Y[i + 2] : p2y;

    const cp1x = p1x + (p2x - p0x) / 6;
    const cp1y = p1y + (p2y - p0y) / 6;
    const cp2x = p2x - (p3x - p1x) / 6;
    const cp2y = p2y - (p3y - p1y) / 6;

    d += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2x.toFixed(1)},${p2y.toFixed(1)}`;
  }
  return d;
}

interface ParticleConfig {
  cx: number;
  cy: number;
  r: number;
  delay: string;
  dur: string;
  type: 'normal' | 'secondary' | 'bright';
}

// SHARED PARTICLES (Identical positions, pulse timings, and cycles in both themes)
const SHARED_PARTICLES: ParticleConfig[] = [
  { cx: 340, cy: 350, r: 1.0, delay: '0s', dur: '4.2s', type: 'normal' },
  { cx: 180, cy: 260, r: 1.5, delay: '1.2s', dur: '4.9s', type: 'secondary' },
  { cx: 450, cy: 500, r: 1.0, delay: '2.5s', dur: '3.8s', type: 'normal' },
  { cx: 310, cy: 540, r: 1.5, delay: '0.8s', dur: '4.6s', type: 'secondary' },
  { cx: 180, cy: 490, r: 2.0, delay: '2.1s', dur: '3.9s', type: 'bright' },
  { cx: 380, cy: 660, r: 1.0, delay: '3.0s', dur: '4.5s', type: 'normal' },
  { cx: 220, cy: 750, r: 1.5, delay: '1.7s', dur: '3.6s', type: 'secondary' },
  { cx: 1100, cy: 340, r: 1.5, delay: '0.5s', dur: '4.8s', type: 'secondary' },
  { cx: 1260, cy: 260, r: 1.0, delay: '2.2s', dur: '3.9s', type: 'normal' },
  { cx: 990, cy: 500, r: 2.0, delay: '1.4s', dur: '4.4s', type: 'bright' },
  { cx: 1130, cy: 540, r: 1.5, delay: '3.1s', dur: '4.3s', type: 'secondary' },
  { cx: 1260, cy: 490, r: 1.0, delay: '0.9s', dur: '4.7s', type: 'normal' },
  { cx: 1060, cy: 660, r: 1.0, delay: '2.7s', dur: '4.1s', type: 'normal' },
  { cx: 1220, cy: 750, r: 1.5, delay: '1.9s', dur: '3.7s', type: 'secondary' },
];

export function HeroWaveSystem() {
  const shouldReduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);

  // Shared path refs — same DOM elements used in both Light and Dark themes
  const leftPathsRef = useRef<(SVGPathElement | null)[]>([]);
  const rightPathsRef = useRef<(SVGPathElement | null)[]>([]);
  const leftShinePathsRef = useRef<(SVGPathElement | null)[]>([]);
  const rightShinePathsRef = useRef<(SVGPathElement | null)[]>([]);

  const animationFrameRef = useRef<number | null>(null);
  const timeRef = useRef<number>(0);
  const lastFrameTimeRef = useRef<number>(0);
  const isVisibleRef = useRef<boolean>(true);
  const activeCountRef = useRef<number>(DESKTOP_STRAND_COUNT);

  useEffect(() => {
    const handleResize = () => {
      const w = window.innerWidth;
      if (w < 768) {
        activeCountRef.current = MOBILE_STRAND_COUNT;
      } else if (w < 1024) {
        activeCountRef.current = TABLET_STRAND_COUNT;
      } else {
        activeCountRef.current = DESKTOP_STRAND_COUNT;
      }

      const count = activeCountRef.current;
      for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
        const lEl = leftPathsRef.current[i];
        if (lEl) lEl.style.display = i < count ? 'block' : 'none';
        const rEl = rightPathsRef.current[i];
        if (rEl) rEl.style.display = i < count ? 'block' : 'none';
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    // Initial render of shared paths (static base at t = 1200)
    for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
      const lEl = leftPathsRef.current[i];
      if (lEl) {
        const dStr = computeSharedRibbonPath(leftStrands[i], 1200, 'left');
        lEl.setAttribute('d', dStr);
        if (i === 2 && leftShinePathsRef.current[0]) leftShinePathsRef.current[0]!.setAttribute('d', dStr);
        if (i === 7 && leftShinePathsRef.current[1]) leftShinePathsRef.current[1]!.setAttribute('d', dStr);
      }
      const rEl = rightPathsRef.current[i];
      if (rEl) {
        const dStr = computeSharedRibbonPath(rightStrands[i], 1200, 'right');
        rEl.setAttribute('d', dStr);
        if (i === 2 && rightShinePathsRef.current[0]) rightShinePathsRef.current[0]!.setAttribute('d', dStr);
        if (i === 7 && rightShinePathsRef.current[1]) rightShinePathsRef.current[1]!.setAttribute('d', dStr);
      }
    }

    if (shouldReduceMotion) {
      return () => {
        window.removeEventListener('resize', handleResize);
      };
    }

    // Target ~33 FPS (frame interval 30ms) for high performance without RAF churn
    const TARGET_INTERVAL = 30;

    const animate = (currentTime: number) => {
      if (!isVisibleRef.current) {
        animationFrameRef.current = null;
        return;
      }

      const delta = currentTime - lastFrameTimeRef.current;

      if (delta >= TARGET_INTERVAL) {
        lastFrameTimeRef.current = currentTime - (delta % TARGET_INTERVAL);
        timeRef.current += Math.min(delta, 64);
        const t = timeRef.current;

        // SINGLE ANIMATION LOOP FOR BOTH THEMES — continuous, seamless motion
        const count = activeCountRef.current;
        for (let idx = 0; idx < count; idx++) {
          const lStrand = leftStrands[idx];
          const lPath = leftPathsRef.current[idx];
          if (lPath) {
            const dStr = computeSharedRibbonPath(lStrand, t, 'left');
            lPath.setAttribute('d', dStr);
            if (idx === 2 && leftShinePathsRef.current[0]) leftShinePathsRef.current[0]!.setAttribute('d', dStr);
            if (idx === 7 && leftShinePathsRef.current[1]) leftShinePathsRef.current[1]!.setAttribute('d', dStr);
          }

          const rStrand = rightStrands[idx];
          const rPath = rightPathsRef.current[idx];
          if (rPath) {
            const dStr = computeSharedRibbonPath(rStrand, t, 'right');
            rPath.setAttribute('d', dStr);
            if (idx === 2 && rightShinePathsRef.current[0]) rightShinePathsRef.current[0]!.setAttribute('d', dStr);
            if (idx === 7 && rightShinePathsRef.current[1]) rightShinePathsRef.current[1]!.setAttribute('d', dStr);
          }
        }
      }

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    const startAnimation = () => {
      if (!animationFrameRef.current) {
        lastFrameTimeRef.current = performance.now();
        animationFrameRef.current = requestAnimationFrame(animate);
      }
    };

    const stopAnimation = () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          isVisibleRef.current = true;
          startAnimation();
        } else {
          isVisibleRef.current = false;
          stopAnimation();
        }
      },
      { threshold: 0.05 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    startAnimation();

    return () => {
      observer.disconnect();
      stopAnimation();
      window.removeEventListener('resize', handleResize);
    };
  }, [shouldReduceMotion]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 pointer-events-none overflow-hidden z-0 select-none"
      aria-hidden="true"
    >
      <svg
        className="w-full h-full min-w-[1024px] xl:min-w-full"
        viewBox="0 0 1440 950"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          {/* ==========================================================
              LIGHT MODE GRADIENTS: Strong, visible pastels with smooth center fade
              Full opacity across outer fields; fades to 0 behind phone (X: 570 -> 870)
              ========================================================== */}
          {/* Left Light Gradients: X = -50 (0%) to X = 705 (100%) */}
          <linearGradient id="leftLightGrad_periwinkle_1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6F86E8" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#6F86E8" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#6F86E8" stopOpacity="0.92" />
            <stop offset="88%" stopColor="#6F86E8" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#6F86E8" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_periwinkle_2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6179D8" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#6179D8" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#6179D8" stopOpacity="0.92" />
            <stop offset="88%" stopColor="#6179D8" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#6179D8" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_blue" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6FA9ED" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#6FA9ED" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#6FA9ED" stopOpacity="0.92" />
            <stop offset="88%" stopColor="#6FA9ED" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#6FA9ED" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_cyan_1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#45C4DB" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#45C4DB" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#45C4DB" stopOpacity="0.94" />
            <stop offset="88%" stopColor="#45C4DB" stopOpacity="0.58" />
            <stop offset="100%" stopColor="#45C4DB" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_cyan_2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#5BCDDD" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#5BCDDD" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#5BCDDD" stopOpacity="0.92" />
            <stop offset="88%" stopColor="#5BCDDD" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#5BCDDD" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_lavender_1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#9B7DE3" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#9B7DE3" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#9B7DE3" stopOpacity="0.94" />
            <stop offset="88%" stopColor="#9B7DE3" stopOpacity="0.58" />
            <stop offset="100%" stopColor="#9B7DE3" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_lavender_2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#AE93E8" stopOpacity="1.0" />
            <stop offset="55%" stopColor="#AE93E8" stopOpacity="0.98" />
            <stop offset="75%" stopColor="#AE93E8" stopOpacity="0.92" />
            <stop offset="88%" stopColor="#AE93E8" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#AE93E8" stopOpacity="0.00" />
          </linearGradient>

          <linearGradient id="leftLightGrad_ice" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#9EAFD4" stopOpacity="0.98" />
            <stop offset="55%" stopColor="#9EAFD4" stopOpacity="0.95" />
            <stop offset="75%" stopColor="#9EAFD4" stopOpacity="0.88" />
            <stop offset="88%" stopColor="#9EAFD4" stopOpacity="0.48" />
            <stop offset="100%" stopColor="#9EAFD4" stopOpacity="0.00" />
          </linearGradient>

          {/* Right Light Gradients: X = 735 (0%) to X = 1490 (100%) */}
          <linearGradient id="rightLightGrad_periwinkle_1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6F86E8" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#6F86E8" stopOpacity="0.55" />
            <stop offset="25%" stopColor="#6F86E8" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#6F86E8" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#6F86E8" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_periwinkle_2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6179D8" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#6179D8" stopOpacity="0.55" />
            <stop offset="25%" stopColor="#6179D8" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#6179D8" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#6179D8" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_blue" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6FA9ED" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#6FA9ED" stopOpacity="0.55" />
            <stop offset="25%" stopColor="#6FA9ED" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#6FA9ED" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#6FA9ED" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_cyan_1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#45C4DB" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#45C4DB" stopOpacity="0.58" />
            <stop offset="25%" stopColor="#45C4DB" stopOpacity="0.94" />
            <stop offset="45%" stopColor="#45C4DB" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#45C4DB" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_cyan_2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#5BCDDD" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#5BCDDD" stopOpacity="0.55" />
            <stop offset="25%" stopColor="#5BCDDD" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#5BCDDD" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#5BCDDD" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_lavender_1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#9B7DE3" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#9B7DE3" stopOpacity="0.58" />
            <stop offset="25%" stopColor="#9B7DE3" stopOpacity="0.94" />
            <stop offset="45%" stopColor="#9B7DE3" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#9B7DE3" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_lavender_2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#AE93E8" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#AE93E8" stopOpacity="0.55" />
            <stop offset="25%" stopColor="#AE93E8" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#AE93E8" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#AE93E8" stopOpacity="1.0" />
          </linearGradient>

          <linearGradient id="rightLightGrad_ice" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#9EAFD4" stopOpacity="0.00" />
            <stop offset="12%" stopColor="#9EAFD4" stopOpacity="0.48" />
            <stop offset="25%" stopColor="#9EAFD4" stopOpacity="0.88" />
            <stop offset="45%" stopColor="#9EAFD4" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#9EAFD4" stopOpacity="0.98" />
          </linearGradient>

          {/* Traveling highlight reflection gradient for Light Mode */}
          <linearGradient id="lightTravelingShineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6F86E8" stopOpacity="0" />
            <stop offset="42%" stopColor="#9B7DE3" stopOpacity="0.45" />
            <stop offset="50%" stopColor="#FFFFFF" stopOpacity="0.98" />
            <stop offset="58%" stopColor="#45C4DB" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#6F86E8" stopOpacity="0" />
          </linearGradient>

          {/* ==========================================================
              DARK MODE GRADIENTS (LOCKED - 100% UNCHANGED)
              ========================================================== */}
          <linearGradient id="leftDarkGrad_subtle" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-subtle)" stopOpacity="0.80" />
            <stop offset="50%" stopColor="var(--wave-strand-subtle)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--wave-strand-subtle)" stopOpacity="0.80" />
          </linearGradient>
          <linearGradient id="leftDarkGrad_primary" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-primary-1)" stopOpacity="0.85" />
            <stop offset="45%" stopColor="var(--wave-strand-primary-2)" stopOpacity="0.98" />
            <stop offset="100%" stopColor="var(--wave-strand-primary-3)" stopOpacity="0.85" />
          </linearGradient>
          <linearGradient id="leftDarkGrad_secondary" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-secondary-1)" stopOpacity="0.85" />
            <stop offset="50%" stopColor="var(--wave-strand-secondary-2)" stopOpacity="0.98" />
            <stop offset="100%" stopColor="var(--wave-strand-secondary-1)" stopOpacity="0.85" />
          </linearGradient>
          <linearGradient id="leftDarkGrad_accent" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-accent-1)" stopOpacity="0.85" />
            <stop offset="50%" stopColor="var(--wave-strand-accent-2)" stopOpacity="0.98" />
            <stop offset="100%" stopColor="var(--wave-strand-accent-1)" stopOpacity="0.85" />
          </linearGradient>

          <linearGradient id="rightDarkGrad_subtle" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-subtle)" stopOpacity="0.80" />
            <stop offset="50%" stopColor="var(--wave-strand-subtle)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--wave-strand-subtle)" stopOpacity="0.80" />
          </linearGradient>
          <linearGradient id="rightDarkGrad_primary" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-primary-1)" stopOpacity="0.85" />
            <stop offset="45%" stopColor="var(--wave-strand-primary-2)" stopOpacity="0.98" />
            <stop offset="100%" stopColor="var(--wave-strand-primary-3)" stopOpacity="0.85" />
          </linearGradient>
          <linearGradient id="rightDarkGrad_secondary" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-secondary-1)" stopOpacity="0.85" />
            <stop offset="50%" stopColor="var(--wave-strand-secondary-2)" stopOpacity="0.98" />
            <stop offset="100%" stopColor="var(--wave-strand-secondary-1)" stopOpacity="0.85" />
          </linearGradient>
          <linearGradient id="rightDarkGrad_accent" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-accent-1)" stopOpacity="0.85" />
            <stop offset="50%" stopColor="var(--wave-strand-accent-2)" stopOpacity="0.98" />
            <stop offset="100%" stopColor="var(--wave-strand-accent-1)" stopOpacity="0.85" />
          </linearGradient>

          {/* Traveling highlight reflection gradient for Dark Mode */}
          <linearGradient id="travelingShineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-shine)" stopOpacity="0" />
            <stop offset="45%" stopColor="var(--wave-shine)" stopOpacity="0.15" />
            <stop offset="50%" stopColor="var(--wave-shine)" stopOpacity="0.95" />
            <stop offset="55%" stopColor="var(--wave-shine)" stopOpacity="0.15" />
            <stop offset="100%" stopColor="var(--wave-shine)" stopOpacity="0" />
          </linearGradient>

          {/* Continuous keyframe animations & theme-specific strand rules */}
          <style>
            {`
              ${PRECOMPUTED_STRAND_CSS}

              /* Traveling Shines (Strand 2 & Strand 7) */
              .hero-shine-a {
                stroke: url(#lightTravelingShineGrad);
                stroke-width: 1.95px;
                stroke-dasharray: 260 1200;
                animation: strandShineA 8.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
              }
              .dark .hero-shine-a {
                stroke: url(#travelingShineGrad);
                stroke-width: 1.8px;
              }

              .hero-shine-b {
                stroke: url(#lightTravelingShineGrad);
                stroke-width: 1.85px;
                stroke-dasharray: 220 1300;
                animation: strandShineB 11s cubic-bezier(0.4, 0, 0.2, 1) infinite 3.5s;
              }
              .dark .hero-shine-b {
                stroke: url(#travelingShineGrad);
                stroke-width: 1.4px;
              }

              /* Particles & Stars */
              .hero-particle-normal {
                fill: #64748B;
                opacity: 0.65;
              }
              .dark .hero-particle-normal {
                fill: var(--star-normal);
                opacity: 0.58;
              }

              .hero-particle-secondary {
                fill: #7C8DB5;
                opacity: 0.64;
              }
              .dark .hero-particle-secondary {
                fill: var(--star-secondary);
                opacity: 0.52;
              }

              .hero-particle-bright {
                fill: #475569;
                opacity: 0.78;
              }
              .dark .hero-particle-bright {
                fill: var(--star-bright);
                opacity: 0.78;
              }

              .hero-sparkle {
                fill: #475569;
                opacity: 0.84;
              }
              .dark .hero-sparkle {
                fill: var(--star-bright);
                opacity: 0.80;
              }

              @keyframes strandShineA {
                0% { stroke-dashoffset: 1600; opacity: 0; }
                15% { opacity: 0.94; }
                85% { opacity: 0.94; }
                100% { stroke-dashoffset: -1600; opacity: 0; }
              }
              @keyframes strandShineB {
                0% { stroke-dashoffset: 1800; opacity: 0; }
                20% { opacity: 0.90; }
                80% { opacity: 0.90; }
                100% { stroke-dashoffset: -1800; opacity: 0; }
              }
              @keyframes dustShimmer {
                0%, 100% { opacity: 0.50; transform: scale(0.9); }
                50% { opacity: 0.85; transform: scale(1.05); }
              }
              @keyframes diamondGlint {
                0%, 100% { opacity: 0.45; transform: scale(0.85) rotate(0deg); }
                50% { opacity: 0.92; transform: scale(1.15) rotate(45deg); }
              }
            `}
          </style>
        </defs>

        {/* ==========================================================
            SHARED WAVE STRANDS & TRAVELING HIGHLIGHTS
            Same SVG path elements for both themes: continuous motion,
            zero jump, zero reset, and identical trajectories.
            ========================================================== */}
        <g id="leftWaveGroup">
          {leftStrands.map((strand, idx) => (
            <path
              key={`left_strand_${strand.id}`}
              ref={(el) => {
                leftPathsRef.current[idx] = el;
              }}
              d={computeSharedRibbonPath(strand, 1200, 'left')}
              className={`strand-left-${strand.id}`}
              fill="none"
              strokeLinecap="round"
            />
          ))}

          {!shouldReduceMotion && (
            <>
              <path
                ref={(el) => {
                  leftShinePathsRef.current[0] = el;
                }}
                d={computeSharedRibbonPath(leftStrands[2], 1200, 'left')}
                strokeLinecap="round"
                fill="none"
                className="hero-shine-a"
              />
              <path
                ref={(el) => {
                  leftShinePathsRef.current[1] = el;
                }}
                d={computeSharedRibbonPath(leftStrands[7], 1200, 'left')}
                strokeLinecap="round"
                fill="none"
                className="hero-shine-b"
              />
            </>
          )}
        </g>

        <g id="rightWaveGroup">
          {rightStrands.map((strand, idx) => (
            <path
              key={`right_strand_${strand.id}`}
              ref={(el) => {
                rightPathsRef.current[idx] = el;
              }}
              d={computeSharedRibbonPath(strand, 1200, 'right')}
              className={`strand-right-${strand.id}`}
              fill="none"
              strokeLinecap="round"
            />
          ))}

          {!shouldReduceMotion && (
            <>
              <path
                ref={(el) => {
                  rightShinePathsRef.current[0] = el;
                }}
                d={computeSharedRibbonPath(rightStrands[2], 1200, 'right')}
                strokeLinecap="round"
                fill="none"
                className="hero-shine-a"
              />
              <path
                ref={(el) => {
                  rightShinePathsRef.current[1] = el;
                }}
                d={computeSharedRibbonPath(rightStrands[7], 1200, 'right')}
                strokeLinecap="round"
                fill="none"
                className="hero-shine-b"
              />
            </>
          )}
        </g>

        {/* SHARED PARTICLES & SPARKLES */}
        <g id="particlesGroup">
          {SHARED_PARTICLES.map((p, idx) => (
            <circle
              key={`particle_${idx}`}
              cx={p.cx}
              cy={p.cy}
              r={p.r}
              className={
                p.type === 'bright'
                  ? 'hero-particle-bright'
                  : p.type === 'secondary'
                  ? 'hero-particle-secondary'
                  : 'hero-particle-normal'
              }
              style={{
                animation: shouldReduceMotion
                  ? 'none'
                  : `dustShimmer ${p.dur} ease-in-out infinite ${p.delay}`,
                transformOrigin: `${p.cx}px ${p.cy}px`,
              }}
            />
          ))}

          {/* 3 Delicate 4-point diamond sparkles */}
          <g
            transform="translate(1080, 500)"
            style={{
              animation: shouldReduceMotion ? 'none' : 'diamondGlint 6.5s ease-in-out infinite 1s',
              transformOrigin: '0 0',
            }}
          >
            <path
              d="M 0 -7 Q 0 0 7 0 Q 0 0 0 7 Q 0 0 -7 0 Q 0 0 0 -7 Z"
              className="hero-sparkle"
            />
          </g>

          <g
            transform="translate(340, 360)"
            style={{
              animation: shouldReduceMotion ? 'none' : 'diamondGlint 7.2s ease-in-out infinite 3.5s',
              transformOrigin: '0 0',
            }}
          >
            <path
              d="M 0 -5.5 Q 0 0 5.5 0 Q 0 0 0 5.5 Q 0 0 -5.5 0 Q 0 0 0 -5.5 Z"
              className="hero-sparkle"
            />
          </g>

          <g
            transform="translate(1240, 270)"
            style={{
              animation: shouldReduceMotion ? 'none' : 'diamondGlint 8.0s ease-in-out infinite 2s',
              transformOrigin: '0 0',
            }}
          >
            <path
              d="M 0 -4.5 Q 0 0 4.5 0 Q 0 0 0 4.5 Q 0 0 -4.5 0 Q 0 0 0 -4.5 Z"
              className="hero-sparkle"
            />
          </g>
        </g>
      </svg>
    </div>
  );
}
