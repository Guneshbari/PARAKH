// @parakh/design-tokens
// Central design tokens for Web and Mobile applications
// DUAL-PERSONALITY DESIGN SYSTEM: Light / Minimal ↔ Monochrome / Black & White

export const darkColors = {
  // Base surfaces - Monochrome Charcoal Family
  base: '#08090A',
  baseSecondary: '#0D0E10',
  surface: '#121416',
  surfaceElevated: '#181A1D',
  surfaceHighlight: '#22252A',
  border: 'rgba(255, 255, 255, 0.08)',
  borderStrong: 'rgba(255, 255, 255, 0.16)',

  // Typography
  textPrimary: '#F5F5F5',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',

  // Buttons
  primaryButtonBg: '#F5F5F5',
  primaryButtonText: '#08090A',
  secondaryButtonBg: 'rgba(255, 255, 255, 0.05)',
  secondaryButtonBorder: 'rgba(255, 255, 255, 0.14)',
  secondaryButtonText: '#F5F5F5',

  // Silk Waves
  waveColors: ['#FFFFFF', '#E4E4E7', '#D4D4D8', '#A1A1AA', '#71717A'],
  waveShine: 'rgba(255, 255, 255, 0.95)',
  starColor: '#FFFFFF',

  // Charts
  chartPrimary: '#FFFFFF',
  chartSecondary: '#A1A1AA',
  chartTertiary: '#71717A',
  chartGrid: 'rgba(255, 255, 255, 0.06)',

  // Grayscale-First with Subtle Distinct Risk Indicators
  riskLower: '#34D399',
  riskLowerSurface: 'rgba(52, 211, 153, 0.12)',
  riskLowerBorder: 'rgba(52, 211, 153, 0.28)',

  riskModerate: '#FBBF24',
  riskModerateSurface: 'rgba(251, 191, 36, 0.12)',
  riskModerateBorder: 'rgba(251, 191, 36, 0.28)',

  riskHigher: '#F87171',
  riskHigherSurface: 'rgba(248, 113, 113, 0.12)',
  riskHigherBorder: 'rgba(248, 113, 113, 0.28)',

  riskNeutral: '#94A3B8',
  riskNeutralSurface: 'rgba(148, 163, 184, 0.12)',
  riskNeutralBorder: 'rgba(148, 163, 184, 0.28)',

  // Backward compatibility aliases
  accentMint: '#F5F5F5',
  accentLavender: '#A1A1AA',
} as const;

export const lightColors = {
  // Base surfaces - Light Minimal
  base: '#F7F8FC',
  baseSecondary: '#F2F4FA',
  surface: '#FFFFFF',
  surfaceElevated: '#F8FAFC',
  surfaceHighlight: '#EEF2F6',
  border: 'rgba(15, 23, 42, 0.08)',
  borderStrong: 'rgba(15, 23, 42, 0.16)',

  // Typography (Deep navy / near-black & slate gray)
  textPrimary: '#0F172A',
  textSecondary: '#475569',
  textMuted: '#94A3B8',

  // Buttons
  primaryButtonBg: '#0F172A',
  primaryButtonText: '#FFFFFF',
  secondaryButtonBg: '#FFFFFF',
  secondaryButtonBorder: 'rgba(15, 23, 42, 0.12)',
  secondaryButtonText: '#0F172A',

  // Silk Waves
  waveColors: ['#CBD5FF', '#C4B5FD', '#93C5FD', '#67E8F9', '#D8B4FE'],
  waveShine: 'rgba(147, 197, 253, 0.85)',
  starColor: '#93C5FD',

  // Charts
  chartPrimary: '#0F172A',
  chartSecondary: '#60A5FA',
  chartTertiary: '#C4B5FD',
  chartGrid: 'rgba(15, 23, 42, 0.06)',

  // Soft Semantic Risk Indicators (Non-neon)
  riskLower: '#059669',
  riskLowerSurface: 'rgba(5, 150, 105, 0.08)',
  riskLowerBorder: 'rgba(5, 150, 105, 0.22)',

  riskModerate: '#D97706',
  riskModerateSurface: 'rgba(217, 119, 6, 0.08)',
  riskModerateBorder: 'rgba(217, 119, 6, 0.22)',

  riskHigher: '#DC2626',
  riskHigherSurface: 'rgba(220, 38, 38, 0.08)',
  riskHigherBorder: 'rgba(220, 38, 38, 0.22)',

  riskNeutral: '#475569',
  riskNeutralSurface: 'rgba(71, 85, 105, 0.08)',
  riskNeutralBorder: 'rgba(71, 85, 105, 0.22)',

  // Backward compatibility aliases
  accentMint: '#0F172A',
  accentLavender: '#475569',
} as const;

// Default export corresponds to darkColors for initial dark experience
export const colors = darkColors;

export const radii = {
  sm: '8px',
  md: '10px',
  lg: '12px',
  xl: '14px',
  '2xl': '16px',
  '3xl': '20px',
  card: '16px',
  pill: '9999px',
} as const;

export const typography = {
  heroMetric: {
    size: '48px',
    weight: '900',
    letterSpacing: '-1px',
    lineHeight: '1',
  },
  editorialHeading: {
    size: '32px',
    weight: '800',
    letterSpacing: '-0.5px',
    lineHeight: '1.2',
  },
  sectionTitle: {
    size: '20px',
    weight: '700',
    letterSpacing: '-0.2px',
    lineHeight: '1.3',
  },
  body: {
    size: '14px',
    weight: '400',
    lineHeight: '1.5',
  },
  caption: {
    size: '12px',
    weight: '500',
    lineHeight: '1.4',
  },
  badge: {
    size: '11px',
    weight: '700',
    letterSpacing: '0.5px',
    textTransform: 'uppercase' as const,
  },
} as const;

export const shadows = {
  card: '0 2px 12px -2px rgba(0, 0, 0, 0.3)',
  dock: '0 10px 30px 0 rgba(0, 0, 0, 0.5)',
} as const;

export const tokens = {
  darkColors,
  lightColors,
  colors,
  radii,
  typography,
  shadows,
} as const;

export type ColorTokens = typeof darkColors;
export type RadiiTokens = typeof radii;
