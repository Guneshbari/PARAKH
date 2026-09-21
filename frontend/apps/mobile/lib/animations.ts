import { WithSpringConfig } from 'react-native-reanimated';

// Reanimated spring configs matching web Framer Motion curves
export const MOBILE_SPRING_GENTLE: WithSpringConfig = {
  damping: 24,
  stiffness: 260,
  mass: 1,
};

export const MOBILE_SPRING_TACTILE: WithSpringConfig = {
  damping: 22,
  stiffness: 340,
  mass: 0.8,
};

export const MOBILE_SPRING_SNAPPY: WithSpringConfig = {
  damping: 28,
  stiffness: 400,
  mass: 0.7,
};
