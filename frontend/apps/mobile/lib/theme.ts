// Mobile Theme Constants for PARAKH
import { tokens } from '@parakh/design-tokens';

export const MobileTheme = {
  colors: {
    background: tokens.colors.base,
    surface: tokens.colors.surface,
    surfaceElevated: tokens.colors.surfaceElevated,
    textPrimary: tokens.colors.textPrimary,
    textSecondary: tokens.colors.textSecondary,
    mint: tokens.colors.accentMint,
    lavender: tokens.colors.accentLavender,
    // Risk state mappings
    riskLower: tokens.colors.riskLower,
    riskModerate: tokens.colors.riskModerate,
    riskHigher: tokens.colors.riskHigher,
    riskNeutral: tokens.colors.riskNeutral,
    border: 'rgba(255, 255, 255, 0.08)',
  },
  radii: {
    card: 16,
    pill: 9999,
    button: 12,
    badge: 9999,
  },
  typography: {
    heroMetric: { fontSize: 44, fontWeight: '800' as const, letterSpacing: -0.5 },
    editorialHeading: { fontSize: 28, fontWeight: '700' as const, letterSpacing: -0.3 },
    sectionTitle: { fontSize: 20, fontWeight: '700' as const },
    body: { fontSize: 15, lineHeight: 22 },
    caption: { fontSize: 12, lineHeight: 16 },
    badge: { fontSize: 11, fontWeight: '600' as const, textTransform: 'uppercase' as const },
  },
};
