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
  gradientId: string;
}

// Responsive strand counts per side (Left and Right)
// Desktop: 22 per side (44 total)
// Tablet: 16 per side (32 total)
// Mobile: 10 per side (20 total)
const DESKTOP_STRAND_COUNT = 22;
const TABLET_STRAND_COUNT = 16;
const MOBILE_STRAND_COUNT = 10;

// Shared conceptual center: Phone center is at X=720, Y=540 on 1440x950 canvas
const HERO_CENTER_X = 720;

// Deterministically construct organic, DNA-woven, non-radial silk strand configurations
function buildRibbonStrandConfigs(side: 'left' | 'right'): RibbonStrandConfig[] {
  const isLeft = side === 'left';
  const strands: RibbonStrandConfig[] = [];

  // 4 intentional clusters for uneven density:
  // 0-4: Upper Swell cluster (5 strands) - floating higher in the field
  // 5-13: Mid DNA Weave cluster (9 strands) - dense interwoven ribbon core
  // 14-18: Lower Cascade cluster (5 strands) - draping lower
  // 19-21: Ambient Hairlines (3 strands) - delicate spatial breathers
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
    let strokeWidth = 0.75;
    let opacity = 0.35;
    let tier: RibbonStrandConfig['tier'] = 'secondary';

    if (i < 5) {
      // Upper Swell: strands gradually drift upward (Y ~ 180-320)
      const u = i / 4;
      y0 = isLeft ? 510 - u * 25 : 515 - u * 25;
      drapeSlope = isLeft ? -220 - u * 60 : -200 - u * 70;
      drapeCurve = isLeft ? -40 + u * 20 : -35 + u * 20;
      amp1 = 40 + u * 15;
      k1 = 1.4 + u * 0.3;
      amp2 = 18 + u * 8;
      k2 = 2.6 + u * 0.4;
      strokeWidth = i === 2 ? 1.45 : i % 2 === 0 ? 0.58 : 0.88;
      opacity = i === 2 ? 0.68 : i % 2 === 0 ? 0.22 : 0.38;
      tier = i === 2 ? 'primary' : i % 2 === 0 ? 'hairline' : 'secondary';
    } else if (i < 14) {
      // Mid DNA Weave: dense cluster around Y ~ 430-580 with alternating S-curves
      const u = (i - 5) / 8;
      y0 = isLeft ? 530 + (u - 0.5) * 45 : 525 + (u - 0.5) * 45;
      // DNA alternating slope & wave phase
      const isEven = (i - 5) % 2 === 0;
      drapeSlope = isEven ? -40 - u * 30 : 50 + u * 30;
      drapeCurve = isEven ? 30 : -30;
      amp1 = 55 + u * 20;
      k1 = 1.75 + (isEven ? 0.2 : -0.2);
      amp2 = 24;
      k2 = 3.2;
      phase1 = (i - 5) * 0.9 + (isEven ? 0 : Math.PI); // Phase inversion creates DNA helix crossings!
      phase2 = (i - 5) * 1.3 + (isEven ? Math.PI * 0.5 : -Math.PI * 0.5);
      strokeWidth = i === 7 || i === 11 ? 1.5 : i % 2 === 0 ? 0.65 : 0.95;
      opacity = i === 7 || i === 11 ? 0.72 : i % 2 === 0 ? 0.25 : 0.42;
      tier = i === 7 || i === 11 ? 'primary' : i % 2 === 0 ? 'hairline' : 'secondary';
    } else if (i < 19) {
      // Lower Cascade: draping down towards Y ~ 680-800
      const u = (i - 14) / 4;
      y0 = isLeft ? 550 + u * 20 : 545 + u * 20;
      drapeSlope = isLeft ? 200 + u * 50 : 210 + u * 55;
      drapeCurve = isLeft ? 40 - u * 15 : 45 - u * 15;
      amp1 = 45 + u * 12;
      k1 = 1.5 + u * 0.25;
      amp2 = 20;
      k2 = 2.7;
      strokeWidth = i === 16 ? 1.38 : i % 2 === 0 ? 0.58 : 0.85;
      opacity = i === 16 ? 0.62 : i % 2 === 0 ? 0.18 : 0.32;
      tier = i === 16 ? 'primary' : i % 2 === 0 ? 'hairline' : 'secondary';
    } else {
      // Ambient hairlines: very calm, low opacity
      const u = (i - 19) / 2;
      y0 = u === 0 ? 490 : u === 1 ? 570 : 530;
      drapeSlope = u === 0 ? -380 : u === 1 ? 340 : -140;
      drapeCurve = 0;
      amp1 = 20;
      k1 = 1.2;
      amp2 = 10;
      k2 = 2.0;
      strokeWidth = 0.5;
      opacity = 0.14;
      tier = 'ambient';
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
      gradientId: `${side}Grad_${i % 4}`,
    });
  }

  return strands;
}

const leftStrands = buildRibbonStrandConfigs('left');
const rightStrands = buildRibbonStrandConfigs('right');

// Fast evaluation points buffer (5 points)
const PTS_X = [0, 0, 0, 0, 0];
const PTS_Y = [0, 0, 0, 0, 0];
const STEPS = [0, 0.22, 0.48, 0.74, 1.0];

// Compute smooth Catmull-Rom cubic Bezier ribbon path with zero allocations
function computeRibbonPath(strand: RibbonStrandConfig, t: number, side: 'left' | 'right'): string {
  const isLeft = side === 'left';
  const startX = HERO_CENTER_X + (isLeft ? -15 : 15);
  const endX = isLeft ? -50 : 1490;
  const totalDx = endX - startX;

  for (let idx = 0; idx < 5; idx++) {
    const s = STEPS[idx];
    const x = startX + s * totalDx;

    // Envelope: 0 behind phone center, smoothly rising past bezel so origin is calm
    const env = Math.pow(Math.sin(s * Math.PI * 0.5), 0.85);

    // Harmonic undulating waves
    const w1 = Math.sin(s * strand.k1 * Math.PI * 2 + t * 0.0009 * strand.speed + strand.phase1);
    const w2 = Math.cos(s * strand.k2 * Math.PI * 2 - t * 0.0005 * strand.speed + strand.phase2);

    // Base drape curve
    const drape = strand.drapeSlope * s + strand.drapeCurve * s * s;
    const y = strand.y0 + drape + (strand.amp1 * w1 + strand.amp2 * w2) * env;

    PTS_X[idx] = x;
    PTS_Y[idx] = y;
  }

  // Generate Catmull-Rom Bezier string
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

// 14 subtle particles along the organic silk ribbon arcs
const PARTICLES = [
  // Left side arcs
  { cx: 340, cy: 350, r: 1.0, delay: '0s', dur: '4.2s' },
  { cx: 180, cy: 260, r: 1.5, delay: '1.2s', dur: '5.1s' },
  { cx: 450, cy: 500, r: 1.0, delay: '2.5s', dur: '3.8s' },
  { cx: 310, cy: 540, r: 1.5, delay: '0.8s', dur: '4.7s' },
  { cx: 180, cy: 490, r: 2.0, delay: '2.1s', dur: '6.0s' },
  { cx: 380, cy: 660, r: 1.0, delay: '3.0s', dur: '4.5s' },
  { cx: 220, cy: 750, r: 1.5, delay: '1.7s', dur: '5.4s' },

  // Right side arcs
  { cx: 1100, cy: 340, r: 1.5, delay: '0.5s', dur: '4.8s' },
  { cx: 1260, cy: 260, r: 1.0, delay: '2.2s', dur: '3.9s' },
  { cx: 990, cy: 500, r: 2.0, delay: '1.4s', dur: '5.8s' },
  { cx: 1130, cy: 540, r: 1.5, delay: '3.1s', dur: '4.3s' },
  { cx: 1260, cy: 490, r: 1.0, delay: '0.9s', dur: '5.0s' },
  { cx: 1060, cy: 660, r: 1.0, delay: '2.7s', dur: '4.1s' },
  { cx: 1220, cy: 750, r: 1.5, delay: '1.9s', dur: '5.2s' },
];

export function HeroWaveSystem() {
  const shouldReduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
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

      const activeCount = activeCountRef.current;
      for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
        const lEl = leftPathsRef.current[i];
        if (lEl) lEl.style.display = i < activeCount ? 'block' : 'none';
        const rEl = rightPathsRef.current[i];
        if (rEl) rEl.style.display = i < activeCount ? 'block' : 'none';
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const activeCount = activeCountRef.current;

    // Initial render of paths
    for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
      const lEl = leftPathsRef.current[i];
      if (lEl) {
        const dStr = computeRibbonPath(leftStrands[i], 1200, 'left');
        lEl.setAttribute('d', dStr);
        lEl.style.display = i < activeCount ? 'block' : 'none';

        if (i === 2 && leftShinePathsRef.current[0]) {
          leftShinePathsRef.current[0]!.setAttribute('d', dStr);
        }
        if (i === 7 && leftShinePathsRef.current[1]) {
          leftShinePathsRef.current[1]!.setAttribute('d', dStr);
        }
      }

      const rEl = rightPathsRef.current[i];
      if (rEl) {
        const dStr = computeRibbonPath(rightStrands[i], 1200, 'right');
        rEl.setAttribute('d', dStr);
        rEl.style.display = i < activeCount ? 'block' : 'none';

        if (i === 2 && rightShinePathsRef.current[0]) {
          rightShinePathsRef.current[0]!.setAttribute('d', dStr);
        }
        if (i === 7 && rightShinePathsRef.current[1]) {
          rightShinePathsRef.current[1]!.setAttribute('d', dStr);
        }
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
        const count = activeCountRef.current;

        for (let idx = 0; idx < count; idx++) {
          const lStrand = leftStrands[idx];
          const lPath = leftPathsRef.current[idx];
          if (lPath) {
            const dStr = computeRibbonPath(lStrand, t, 'left');
            lPath.setAttribute('d', dStr);

            if (idx === 2 && leftShinePathsRef.current[0]) {
              leftShinePathsRef.current[0]!.setAttribute('d', dStr);
            }
            if (idx === 7 && leftShinePathsRef.current[1]) {
              leftShinePathsRef.current[1]!.setAttribute('d', dStr);
            }
          }

          const rStrand = rightStrands[idx];
          const rPath = rightPathsRef.current[idx];
          if (rPath) {
            const dStr = computeRibbonPath(rStrand, t, 'right');
            rPath.setAttribute('d', dStr);

            if (idx === 2 && rightShinePathsRef.current[0]) {
              rightShinePathsRef.current[0]!.setAttribute('d', dStr);
            }
            if (idx === 7 && rightShinePathsRef.current[1]) {
              rightShinePathsRef.current[1]!.setAttribute('d', dStr);
            }
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
          {/* Gradients using semantic CSS tokens:
              In Dark mode: White, Silver, Zinc, Charcoal (#FFFFFF, #E4E4E7, #D4D4D8, #A1A1AA, #71717A)
              In Light mode: Soft Pastels (#CBD5FF, #C4B5FD, #93C5FD, #67E8F9, #D8B4FE)
              Theme toggle updates tokens automatically without resetting RAF! */}
          <linearGradient id="leftGrad_0" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-1)" stopOpacity="0.35" />
            <stop offset="45%" stopColor="var(--wave-strand-2)" stopOpacity="0.7" />
            <stop offset="85%" stopColor="var(--wave-strand-3)" stopOpacity="0.85" />
            <stop offset="100%" stopColor="var(--wave-strand-4)" stopOpacity="0.75" />
          </linearGradient>

          <linearGradient id="leftGrad_1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-2)" stopOpacity="0.45" />
            <stop offset="40%" stopColor="var(--wave-strand-3)" stopOpacity="0.8" />
            <stop offset="75%" stopColor="var(--wave-strand-4)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--wave-strand-5)" stopOpacity="0.75" />
          </linearGradient>

          <linearGradient id="leftGrad_2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-3)" stopOpacity="0.5" />
            <stop offset="40%" stopColor="var(--wave-strand-4)" stopOpacity="0.85" />
            <stop offset="80%" stopColor="var(--wave-strand-1)" stopOpacity="0.9" />
            <stop offset="100%" stopColor="var(--wave-strand-2)" stopOpacity="0.7" />
          </linearGradient>

          <linearGradient id="leftGrad_3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-4)" stopOpacity="0.55" />
            <stop offset="50%" stopColor="var(--wave-strand-5)" stopOpacity="0.8" />
            <stop offset="85%" stopColor="var(--wave-strand-2)" stopOpacity="0.85" />
            <stop offset="100%" stopColor="var(--wave-strand-3)" stopOpacity="0.65" />
          </linearGradient>

          {/* Right Gradients */}
          <linearGradient id="rightGrad_0" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-1)" stopOpacity="0.35" />
            <stop offset="45%" stopColor="var(--wave-strand-2)" stopOpacity="0.7" />
            <stop offset="85%" stopColor="var(--wave-strand-3)" stopOpacity="0.85" />
            <stop offset="100%" stopColor="var(--wave-strand-4)" stopOpacity="0.75" />
          </linearGradient>

          <linearGradient id="rightGrad_1" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-2)" stopOpacity="0.45" />
            <stop offset="40%" stopColor="var(--wave-strand-3)" stopOpacity="0.8" />
            <stop offset="75%" stopColor="var(--wave-strand-4)" stopOpacity="0.95" />
            <stop offset="100%" stopColor="var(--wave-strand-5)" stopOpacity="0.75" />
          </linearGradient>

          <linearGradient id="rightGrad_2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-3)" stopOpacity="0.5" />
            <stop offset="40%" stopColor="var(--wave-strand-4)" stopOpacity="0.85" />
            <stop offset="80%" stopColor="var(--wave-strand-1)" stopOpacity="0.9" />
            <stop offset="100%" stopColor="var(--wave-strand-2)" stopOpacity="0.7" />
          </linearGradient>

          <linearGradient id="rightGrad_3" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-strand-4)" stopOpacity="0.55" />
            <stop offset="50%" stopColor="var(--wave-strand-5)" stopOpacity="0.8" />
            <stop offset="85%" stopColor="var(--wave-strand-2)" stopOpacity="0.85" />
            <stop offset="100%" stopColor="var(--wave-strand-3)" stopOpacity="0.65" />
          </linearGradient>

          {/* Traveling studio light reflection gradient */}
          <linearGradient id="travelingShineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--wave-shine)" stopOpacity="0" />
            <stop offset="45%" stopColor="var(--wave-shine)" stopOpacity="0.12" />
            <stop offset="50%" stopColor="var(--wave-shine)" stopOpacity="0.9" />
            <stop offset="55%" stopColor="var(--wave-shine)" stopOpacity="0.12" />
            <stop offset="100%" stopColor="var(--wave-shine)" stopOpacity="0" />
          </linearGradient>

          {/* Keyframe animation for traveling shine along curved trajectories */}
          <style>
            {`
              @keyframes strandShineA {
                0% { stroke-dashoffset: 1600; opacity: 0; }
                15% { opacity: 0.85; }
                85% { opacity: 0.85; }
                100% { stroke-dashoffset: -1600; opacity: 0; }
              }
              @keyframes strandShineB {
                0% { stroke-dashoffset: 1800; opacity: 0; }
                20% { opacity: 0.75; }
                80% { opacity: 0.75; }
                100% { stroke-dashoffset: -1800; opacity: 0; }
              }
              @keyframes dustShimmer {
                0%, 100% { opacity: 0.2; transform: scale(0.9); }
                50% { opacity: 0.8; transform: scale(1.15); }
              }
              @keyframes diamondGlint {
                0%, 100% { opacity: 0.2; transform: scale(0.8) rotate(0deg); }
                50% { opacity: 0.95; transform: scale(1.2) rotate(45deg); }
              }
              .shine-strand-a {
                stroke-dasharray: 240 1200;
                animation: strandShineA 9s cubic-bezier(0.4, 0, 0.2, 1) infinite;
              }
              .shine-strand-b {
                stroke-dasharray: 200 1300;
                animation: strandShineB 12s cubic-bezier(0.4, 0, 0.2, 1) infinite 4s;
              }
            `}
          </style>
        </defs>

        {/* LEFT WAVE STRANDS (Curved DNA / Silk Strands) */}
        <g id="leftWaveGroup">
          {leftStrands.map((strand, idx) => (
            <path
              key={`left_${strand.id}`}
              ref={(el) => {
                leftPathsRef.current[idx] = el;
              }}
              d={computeRibbonPath(strand, 1000, 'left')}
              stroke={`url(#${strand.gradientId})`}
              strokeWidth={strand.strokeWidth}
              strokeOpacity={strand.opacity}
              strokeLinecap="round"
              fill="none"
            />
          ))}

          {/* Traveling light reflection paths on left bundle (following curved strands 2 & 7) */}
          {!shouldReduceMotion && (
            <>
              <path
                ref={(el) => {
                  leftShinePathsRef.current[0] = el;
                }}
                stroke="url(#travelingShineGrad)"
                strokeWidth={1.8}
                strokeLinecap="round"
                fill="none"
                className="shine-strand-a"
              />
              <path
                ref={(el) => {
                  leftShinePathsRef.current[1] = el;
                }}
                stroke="url(#travelingShineGrad)"
                strokeWidth={1.4}
                strokeLinecap="round"
                fill="none"
                className="shine-strand-b"
              />
            </>
          )}
        </g>

        {/* RIGHT WAVE STRANDS (Curved DNA / Silk Strands) */}
        <g id="rightWaveGroup">
          {rightStrands.map((strand, idx) => (
            <path
              key={`right_${strand.id}`}
              ref={(el) => {
                rightPathsRef.current[idx] = el;
              }}
              d={computeRibbonPath(strand, 1000, 'right')}
              stroke={`url(#${strand.gradientId})`}
              strokeWidth={strand.strokeWidth}
              strokeOpacity={strand.opacity}
              strokeLinecap="round"
              fill="none"
            />
          ))}

          {/* Traveling light reflection paths on right bundle (following curved strands 2 & 7) */}
          {!shouldReduceMotion && (
            <>
              <path
                ref={(el) => {
                  rightShinePathsRef.current[0] = el;
                }}
                stroke="url(#travelingShineGrad)"
                strokeWidth={1.8}
                strokeLinecap="round"
                fill="none"
                className="shine-strand-a"
              />
              <path
                ref={(el) => {
                  rightShinePathsRef.current[1] = el;
                }}
                stroke="url(#travelingShineGrad)"
                strokeWidth={1.4}
                strokeLinecap="round"
                fill="none"
                className="shine-strand-b"
              />
            </>
          )}
        </g>

        {/* SPARSE TINY PARTICLES & 4-POINT DIAMOND GLINTS ALONG SILK ARCS */}
        <g id="particlesGroup">
          {PARTICLES.map((p, idx) => (
            <circle
              key={`particle_${idx}`}
              cx={p.cx}
              cy={p.cy}
              r={p.r}
              fill="var(--star-color)"
              style={{
                opacity: 0.45,
                animation: shouldReduceMotion
                  ? 'none'
                  : `dustShimmer ${p.dur} ease-in-out infinite ${p.delay}`,
                transformOrigin: `${p.cx}px ${p.cy}px`,
              }}
            />
          ))}

          {/* 3 Delicate 4-point diamond glints */}
          <g
            transform="translate(1080, 500)"
            style={{
              animation: shouldReduceMotion ? 'none' : 'diamondGlint 6.5s ease-in-out infinite 1s',
              transformOrigin: '0 0',
            }}
          >
            <path
              d="M 0 -7 Q 0 0 7 0 Q 0 0 0 7 Q 0 0 -7 0 Q 0 0 0 -7 Z"
              fill="var(--star-color)"
              opacity="0.85"
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
              fill="var(--star-color)"
              opacity="0.75"
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
              fill="var(--star-color)"
              opacity="0.65"
            />
          </g>
        </g>
      </svg>
    </div>
  );
}
