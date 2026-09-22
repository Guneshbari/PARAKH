// Mobile Theme Architecture for PARAKH
// Dual-Personality Design System: Light / Minimal ↔ Monochrome Charcoal Dark
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { tokens } from '@parakh/design-tokens';

export type ThemeMode = 'dark' | 'light';

export const darkThemeColors = {
  background: tokens.darkColors.base,
  baseSecondary: tokens.darkColors.baseSecondary,
  surface: tokens.darkColors.surface,
  surfaceElevated: tokens.darkColors.surfaceElevated,
  surfaceHighlight: tokens.darkColors.surfaceHighlight,
  border: tokens.darkColors.border,
  borderStrong: tokens.darkColors.borderStrong,

  textPrimary: tokens.darkColors.textPrimary,
  textSecondary: tokens.darkColors.textSecondary,
  textMuted: tokens.darkColors.textMuted,

  primaryButtonBg: tokens.darkColors.primaryButtonBg,
  primaryButtonText: tokens.darkColors.primaryButtonText,
  secondaryButtonBg: tokens.darkColors.secondaryButtonBg,
  secondaryButtonBorder: tokens.darkColors.secondaryButtonBorder,
  secondaryButtonText: tokens.darkColors.secondaryButtonText,

  // Distinguishable subtle risk indicators
  riskLower: tokens.darkColors.riskLower,
  riskLowerSurface: tokens.darkColors.riskLowerSurface,
  riskLowerBorder: tokens.darkColors.riskLowerBorder,

  riskModerate: tokens.darkColors.riskModerate,
  riskModerateSurface: tokens.darkColors.riskModerateSurface,
  riskModerateBorder: tokens.darkColors.riskModerateBorder,

  riskHigher: tokens.darkColors.riskHigher,
  riskHigherSurface: tokens.darkColors.riskHigherSurface,
  riskHigherBorder: tokens.darkColors.riskHigherBorder,

  riskNeutral: tokens.darkColors.riskNeutral,
  riskNeutralSurface: tokens.darkColors.riskNeutralSurface,
  riskNeutralBorder: tokens.darkColors.riskNeutralBorder,

  // Backward compatibility aliases
  mint: tokens.darkColors.textPrimary,
  lavender: tokens.darkColors.textSecondary,
} as const;

export const lightThemeColors = {
  background: tokens.lightColors.base,
  baseSecondary: tokens.lightColors.baseSecondary,
  surface: tokens.lightColors.surface,
  surfaceElevated: tokens.lightColors.surfaceElevated,
  surfaceHighlight: tokens.lightColors.surfaceHighlight,
  border: tokens.lightColors.border,
  borderStrong: tokens.lightColors.borderStrong,

  textPrimary: tokens.lightColors.textPrimary,
  textSecondary: tokens.lightColors.textSecondary,
  textMuted: tokens.lightColors.textMuted,

  primaryButtonBg: tokens.lightColors.primaryButtonBg,
  primaryButtonText: tokens.lightColors.primaryButtonText,
  secondaryButtonBg: tokens.lightColors.secondaryButtonBg,
  secondaryButtonBorder: tokens.lightColors.secondaryButtonBorder,
  secondaryButtonText: tokens.lightColors.secondaryButtonText,

  // Soft semantic risk indicators
  riskLower: tokens.lightColors.riskLower,
  riskLowerSurface: tokens.lightColors.riskLowerSurface,
  riskLowerBorder: tokens.lightColors.riskLowerBorder,

  riskModerate: tokens.lightColors.riskModerate,
  riskModerateSurface: tokens.lightColors.riskModerateSurface,
  riskModerateBorder: tokens.lightColors.riskModerateBorder,

  riskHigher: tokens.lightColors.riskHigher,
  riskHigherSurface: tokens.lightColors.riskHigherSurface,
  riskHigherBorder: tokens.lightColors.riskHigherBorder,

  riskNeutral: tokens.lightColors.riskNeutral,
  riskNeutralSurface: tokens.lightColors.riskNeutralSurface,
  riskNeutralBorder: tokens.lightColors.riskNeutralBorder,

  // Backward compatibility aliases
  mint: tokens.lightColors.textPrimary,
  lavender: tokens.lightColors.textSecondary,
} as const;

export type MobileColors = typeof darkThemeColors;

export const MobileTheme = {
  colors: darkThemeColors,
  radii: {
    card: 16,
    pill: 9999,
    button: 12,
    badge: 9999,
  },
  typography: {
    heroMetric: { fontSize: 44, fontWeight: '900' as const, letterSpacing: -1 },
    editorialHeading: { fontSize: 28, fontWeight: '800' as const, letterSpacing: -0.5 },
    sectionTitle: { fontSize: 20, fontWeight: '700' as const, letterSpacing: -0.2 },
    body: { fontSize: 14, lineHeight: 21 },
    caption: { fontSize: 12, lineHeight: 16 },
    badge: { fontSize: 11, fontWeight: '700' as const, letterSpacing: 0.5, textTransform: 'uppercase' as const },
  },
};

interface ThemeContextValue {
  theme: ThemeMode;
  isDark: boolean;
  colors: MobileColors;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  isDark: true,
  colors: darkThemeColors,
  toggleTheme: () => {},
  setTheme: () => {},
});

const MOBILE_THEME_STORAGE_KEY = 'parakh_mobile_theme';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('dark');

  // Load persisted theme on mount
  useEffect(() => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = window.localStorage.getItem(MOBILE_THEME_STORAGE_KEY) as ThemeMode;
        if (stored === 'light' || stored === 'dark') {
          setThemeState(stored);
        }
      }
    } catch {}
  }, []);

  const setTheme = useCallback((newTheme: ThemeMode) => {
    setThemeState(newTheme);
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(MOBILE_THEME_STORAGE_KEY, newTheme);
      }
    } catch {}
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [theme, setTheme]);

  const colors = theme === 'dark' ? darkThemeColors : (lightThemeColors as unknown as MobileColors);

  return React.createElement(
    ThemeContext.Provider,
    {
      value: {
        theme,
        isDark: theme === 'dark',
        colors,
        toggleTheme,
        setTheme,
      },
    },
    children
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
