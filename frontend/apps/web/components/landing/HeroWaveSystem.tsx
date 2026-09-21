'use client';

import React, { useEffect, useRef } from 'react';
import { useReducedMotion } from 'framer-motion';

interface StrandConfig {
  id: number;
  u: number; // 0 to 1 normalized position in bundle
  opacity: number;
  strokeWidth: number;
  gradientId: string;
  speedMultiplier: number;
  phaseOffset: number;
}

// 14 strands on desktop, 8 on mobile
const DESKTOP_STRAND_COUNT = 14;
const MOBILE_STRAND_COUNT = 8;

const leftStrands: StrandConfig[] = Array.from({ length: DESKTOP_STRAND_COUNT }, (_, i) => {
  const u = i / (DESKTOP_STRAND_COUNT - 1);
  const isForeground = i >= DESKTOP_STRAND_COUNT - 4;
  const isBackground = i <= 3;
  const strokeWidth = isForeground ? 1.6 + (i % 3) * 0.3 : isBackground ? 0.75 : 1.1;
  const opacity = isForeground ? 0.85 : isBackground ? 0.25 : 0.55;
  const gradIndex = Math.floor(u * 4);

  return {
    id: i,
    u,
    opacity,
    strokeWidth,
    gradientId: `leftGrad_${gradIndex}`,
    speedMultiplier: 0.85 + u * 0.3,
    phaseOffset: u * 2.4,
  };
});

const rightStrands: StrandConfig[] = Array.from({ length: DESKTOP_STRAND_COUNT }, (_, i) => {
  const u = i / (DESKTOP_STRAND_COUNT - 1);
  const isForeground = i >= DESKTOP_STRAND_COUNT - 4;
  const isBackground = i <= 3;
  const strokeWidth = isForeground ? 1.6 + (i % 3) * 0.3 : isBackground ? 0.75 : 1.1;
  const opacity = isForeground ? 0.85 : isBackground ? 0.25 : 0.55;
  const gradIndex = Math.floor(u * 4);

  return {
    id: i,
    u,
    opacity,
    strokeWidth,
    gradientId: `rightGrad_${gradIndex}`,
    speedMultiplier: 0.85 + u * 0.3,
    phaseOffset: u * 2.4,
  };
});

// Compute smooth cubic Bezier path for Left wave
const computeLeftPath = (u: number, t: number, phase: number): string => {
  const wave1 = Math.sin(t * 0.00085 + phase) * 22;
  const wave2 = Math.cos(t * 0.0014 - u * 3.2 + phase * 0.7) * 16;
  const wave3 = Math.sin(t * 0.00045 + u * 4.0) * 12;

  const bundleSpread = (u - 0.5) * 85;

  const x0 = -30 + u * 40;
  const y0 = 120 + u * 140 + wave1 * 0.6;

  const cp1x = 120 + u * 60 + wave2 * 0.8;
  const cp1y = 260 + bundleSpread * 0.9 + wave1;

  const cp2x = 240 + u * 80 + wave3;
  const cp2y = 450 + bundleSpread * 1.4 + wave2 * 1.2;

  const cp3x = 380 + u * 60 + wave1 * 0.7;
  const cp3y = 610 + bundleSpread * 1.1 + wave3;

  const x4 = 520 + u * 70 + wave2 * 0.6;
  const y4 = 750 + bundleSpread * 0.8 + wave1 * 0.5;

  return `M ${x0.toFixed(1)},${y0.toFixed(1)} C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${cp3x.toFixed(1)},${cp3y.toFixed(1)} S ${x4.toFixed(1)},${y4.toFixed(1)} ${(x4 + 60).toFixed(1)},${(y4 + 40).toFixed(1)}`;
};

// Compute smooth cubic Bezier path for Right wave
const computeRightPath = (u: number, t: number, phase: number): string => {
  const wave1 = Math.sin(t * 0.0008 + phase + 1.2) * 22;
  const wave2 = Math.cos(t * 0.0013 - u * 3.2 + phase * 0.7) * 16;
  const wave3 = Math.sin(t * 0.00042 + u * 4.0 + 0.8) * 12;

  const bundleSpread = (u - 0.5) * 85;

  const x0 = 1470 - u * 40;
  const y0 = 140 + u * 140 + wave1 * 0.6;

  const cp1x = 1320 - u * 60 - wave2 * 0.8;
  const cp1y = 280 + bundleSpread * 0.9 + wave1;

  const cp2x = 1200 - u * 80 - wave3;
  const cp2y = 460 + bundleSpread * 1.4 + wave2 * 1.2;

  const cp3x = 1060 - u * 60 - wave1 * 0.7;
  const cp3y = 620 + bundleSpread * 1.1 + wave3;

  const x4 = 920 - u * 70 - wave2 * 0.6;
  const y4 = 750 + bundleSpread * 0.8 + wave1 * 0.5;

  return `M ${x0.toFixed(1)},${y0.toFixed(1)} C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${cp3x.toFixed(1)},${cp3y.toFixed(1)} S ${x4.toFixed(1)},${y4.toFixed(1)} ${(x4 - 60).toFixed(1)},${(y4 + 40).toFixed(1)}`;
};

export function HeroWaveSystem() {
  const shouldReduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const leftPathsRef = useRef<(SVGPathElement | null)[]>([]);
  const rightPathsRef = useRef<(SVGPathElement | null)[]>([]);
  const animationFrameRef = useRef<number | null>(null);
  const timeRef = useRef<number>(0);
  const lastFrameTimeRef = useRef<number>(0);
  const isVisibleRef = useRef<boolean>(true);
  const isMobileRef = useRef<boolean>(false);

  useEffect(() => {
    // Detect mobile viewport
    const checkMobile = () => {
      isMobileRef.current = window.innerWidth < 768;
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);

    // Initial static positioning
    const activeCount = isMobileRef.current ? MOBILE_STRAND_COUNT : DESKTOP_STRAND_COUNT;
    for (let i = 0; i < DESKTOP_STRAND_COUNT; i++) {
      const lEl = leftPathsRef.current[i];
      if (lEl) {
        lEl.setAttribute('d', computeLeftPath(leftStrands[i].u, 1500, leftStrands[i].phaseOffset));
        lEl.style.display = i < activeCount ? 'block' : 'none';
      }
      const rEl = rightPathsRef.current[i];
      if (rEl) {
        rEl.setAttribute('d', computeRightPath(rightStrands[i].u, 1500, rightStrands[i].phaseOffset));
        rEl.style.display = i < activeCount ? 'block' : 'none';
      }
    }

    if (shouldReduceMotion) {
      return () => {
        window.removeEventListener('resize', checkMobile);
      };
    }

    // Target ~33 FPS (frame interval 30ms) for high performance
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

        const count = isMobileRef.current ? MOBILE_STRAND_COUNT : DESKTOP_STRAND_COUNT;

        for (let idx = 0; idx < count; idx++) {
          const lStrand = leftStrands[idx];
          const lPath = leftPathsRef.current[idx];
          if (lPath) {
            lPath.setAttribute(
              'd',
              computeLeftPath(lStrand.u, t * lStrand.speedMultiplier, lStrand.phaseOffset)
            );
          }

          const rStrand = rightStrands[idx];
          const rPath = rightPathsRef.current[idx];
          if (rPath) {
            rPath.setAttribute(
              'd',
              computeRightPath(rStrand.u, t * rStrand.speedMultiplier, rStrand.phaseOffset)
            );
          }
        }
      }

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    // IntersectionObserver to pause when hero is off-screen
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
      window.removeEventListener('resize', checkMobile);
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
          {/* Left Wave Gradients: Blue -> Cyan -> Mint -> Violet */}
          <linearGradient id="leftGrad_0" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1E40AF" stopOpacity="0.4" />
            <stop offset="35%" stopColor="#0284C7" stopOpacity="0.7" />
            <stop offset="70%" stopColor="#06B6D4" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#2DD4BF" stopOpacity="0.8" />
          </linearGradient>

          <linearGradient id="leftGrad_1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2563EB" stopOpacity="0.5" />
            <stop offset="30%" stopColor="#0EA5E9" stopOpacity="0.85" />
            <stop offset="65%" stopColor="#22D3EE" stopOpacity="1" />
            <stop offset="100%" stopColor="#34D399" stopOpacity="0.85" />
          </linearGradient>

          <linearGradient id="leftGrad_2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.6" />
            <stop offset="40%" stopColor="#22D3EE" stopOpacity="0.95" />
            <stop offset="75%" stopColor="#2DD4BF" stopOpacity="1" />
            <stop offset="100%" stopColor="#818CF8" stopOpacity="0.8" />
          </linearGradient>

          <linearGradient id="leftGrad_3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#60A5FA" stopOpacity="0.7" />
            <stop offset="35%" stopColor="#38BDF8" stopOpacity="1" />
            <stop offset="70%" stopColor="#2DD4BF" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#A78BFA" stopOpacity="0.9" />
          </linearGradient>

          {/* Right Wave Gradients: Violet -> Pink -> Cyan -> Blue */}
          <linearGradient id="rightGrad_0" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#7C3AED" stopOpacity="0.4" />
            <stop offset="35%" stopColor="#C026D3" stopOpacity="0.7" />
            <stop offset="70%" stopColor="#06B6D4" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#1D4ED8" stopOpacity="0.8" />
          </linearGradient>

          <linearGradient id="rightGrad_1" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.5" />
            <stop offset="30%" stopColor="#D946EF" stopOpacity="0.85" />
            <stop offset="65%" stopColor="#22D3EE" stopOpacity="1" />
            <stop offset="100%" stopColor="#2563EB" stopOpacity="0.85" />
          </linearGradient>

          <linearGradient id="rightGrad_2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#A855F7" stopOpacity="0.6" />
            <stop offset="40%" stopColor="#EC4899" stopOpacity="0.95" />
            <stop offset="75%" stopColor="#38BDF8" stopOpacity="1" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.8" />
          </linearGradient>

          <linearGradient id="rightGrad_3" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#C084FC" stopOpacity="0.7" />
            <stop offset="35%" stopColor="#F472B6" stopOpacity="1" />
            <stop offset="70%" stopColor="#22D3EE" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {/* LEFT WAVE STRANDS */}
        <g id="leftWaveGroup">
          {leftStrands.map((strand, idx) => (
            <path
              key={`left_${strand.id}`}
              ref={(el) => {
                leftPathsRef.current[idx] = el;
              }}
              d={computeLeftPath(strand.u, 1000, strand.phaseOffset)}
              stroke={`url(#${strand.gradientId})`}
              strokeWidth={strand.strokeWidth}
              strokeOpacity={strand.opacity}
              strokeLinecap="round"
              fill="none"
            />
          ))}
        </g>

        {/* RIGHT WAVE STRANDS */}
        <g id="rightWaveGroup">
          {rightStrands.map((strand, idx) => (
            <path
              key={`right_${strand.id}`}
              ref={(el) => {
                rightPathsRef.current[idx] = el;
              }}
              d={computeRightPath(strand.u, 1000, strand.phaseOffset)}
              stroke={`url(#${strand.gradientId})`}
              strokeWidth={strand.strokeWidth}
              strokeOpacity={strand.opacity}
              strokeLinecap="round"
              fill="none"
            />
          ))}
        </g>
      </svg>
    </div>
  );
}
