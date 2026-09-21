// @parakh/design-tokens
// Central design tokens for Web and Mobile applications matching the CashPilot visual reference

export const colors = {
  // Base surfaces - Deep Navy Family
  base: '#060D1F',
  surface: '#0A162E',
  surfaceElevated: '#0E1F3D',
  surfaceHighlight: '#14274E',
  border: 'rgba(255, 255, 255, 0.08)',
  borderHover: 'rgba(255, 255, 255, 0.16)',

  // Typography
  textPrimary: '#F8FAFC',
  textSecondary: '#A8B7CC',
  textTertiary: '#71829A',

  // Signature FinTech Accents
  accentLime: '#C8F451',
  accentElectricBlue: '#2563EB',
  accentRoyalBlue: '#1239A6',
  accentCyan: '#22D3EE',
  accentMint: '#2DD4BF',
  accentMintSurface: 'rgba(45, 212, 191, 0.12)',
  accentMintBorder: 'rgba(45, 212, 191, 0.3)',
  
  accentViolet: '#8B5CF6',
  accentVioletSurface: 'rgba(139, 92, 246, 0.12)',
  accentVioletBorder: 'rgba(139, 92, 246, 0.3)',

  accentLavender: '#C4B5FD',
  accentLavenderSurface: '#1F1E2E',
  accentLavenderBorder: 'rgba(196, 181, 253, 0.3)',

  accentMagenta: '#EC4899',

  // Four Restrained Risk States
  riskLower: '#34D399',
  riskLowerSurface: 'rgba(52, 211, 153, 0.12)',
  riskLowerBorder: 'rgba(52, 211, 153, 0.28)',

  riskModerate: '#FBBF24',
  riskModerateSurface: 'rgba(251, 191, 36, 0.12)',
  riskModerateBorder: 'rgba(251, 191, 36, 0.28)',

  riskHigher: '#F87171',
  riskHigherSurface: 'rgba(248, 113, 113, 0.12)',
  riskHigherBorder: 'rgba(248, 113, 113, 0.28)',

  riskNeutral: '#64748B',
  riskNeutralSurface: 'rgba(100, 116, 139, 0.12)',
  riskNeutralBorder: 'rgba(100, 116, 139, 0.28)',
} as const;

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
  card: '0 4px 20px -2px rgba(0, 0, 0, 0.5)',
  dock: '0 10px 30px 0 rgba(0, 0, 0, 0.7)',
  accentGlow: '0 0 24px -4px rgba(45, 212, 191, 0.2)',
  aiGlow: '0 0 24px -4px rgba(196, 181, 253, 0.2)',
} as const;

export const tokens = {
  colors,
  radii,
  typography,
  shadows,
} as const;

export type ColorTokens = typeof colors;
export type RadiiTokens = typeof radii;
