// Reusable Framer Motion animation utilities and variants for PARAKH
import { Transition, Variants } from 'framer-motion';

export const SPRING_GENTLE: Transition = {
  type: 'spring',
  stiffness: 260,
  damping: 24,
};

export const SPRING_SNAPPY: Transition = {
  type: 'spring',
  stiffness: 400,
  damping: 30,
};

export const EASE_SMOOTH: Transition = {
  duration: 0.35,
  ease: [0.25, 0.1, 0.25, 1],
};

// Page entrance transition
export const pageVariants: Variants = {
  initial: {
    opacity: 0,
    y: 8,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};

// Container that staggers its children (e.g. dashboard cards, metric grids)
export const staggerContainer = (staggerChildren = 0.07, delayChildren = 0.05): Variants => ({
  initial: {},
  animate: {
    transition: {
      staggerChildren,
      delayChildren,
    },
  },
});

// Card entrance variant (used inside a staggerContainer)
export const fadeInUp: Variants = {
  initial: {
    opacity: 0,
    y: 16,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
};

// Card scale-fade entrance
export const scaleIn: Variants = {
  initial: {
    opacity: 0,
    scale: 0.96,
  },
  animate: {
    opacity: 1,
    scale: 1,
    transition: SPRING_GENTLE,
  },
};

// Interactive hover and press states for rounded cards
export const cardHoverMotion: Variants = {
  rest: {
    y: 0,
    scale: 1,
    borderColor: 'rgba(255, 255, 255, 0.07)',
    transition: { duration: 0.2 },
  },
  hover: {
    y: -3,
    scale: 1.005,
    borderColor: 'rgba(255, 255, 255, 0.14)',
    transition: { duration: 0.2 },
  },
  tap: {
    scale: 0.995,
    transition: { duration: 0.1 },
  },
};

// Tactile button micro-interaction
export const buttonPressMotion = {
  whileHover: { scale: 1.02 },
  whileTap: { scale: 0.97 },
  transition: { type: 'spring' as const, stiffness: 450, damping: 25 },
};

// Floating AI badge subtle glow pulse
export const pulseGlow: Variants = {
  initial: { opacity: 0.7 },
  animate: {
    opacity: [0.7, 1, 0.7],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};
