import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { MobileTheme, useTheme } from '../lib/theme';

export type BadgeVariant =
  | 'riskLower'
  | 'riskModerate'
  | 'riskHigher'
  | 'riskNeutral'
  | 'default'
  | 'secondary'
  | 'outline'
  | 'mint'
  | 'lavender';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
}

export function Badge({
  label,
  variant = 'secondary',
  style,
  textStyle,
  icon,
}: BadgeProps) {
  let colors = MobileTheme.colors;
  try {
    const theme = useTheme();
    colors = theme.colors;
  } catch {}

  const getBadgeColors = () => {
    switch (variant) {
      case 'riskLower':
        return {
          bg: colors.riskLowerSurface,
          border: colors.riskLowerBorder,
          text: colors.riskLower,
        };
      case 'riskModerate':
        return {
          bg: colors.riskModerateSurface,
          border: colors.riskModerateBorder,
          text: colors.riskModerate,
        };
      case 'riskHigher':
        return {
          bg: colors.riskHigherSurface,
          border: colors.riskHigherBorder,
          text: colors.riskHigher,
        };
      case 'riskNeutral':
        return {
          bg: colors.riskNeutralSurface,
          border: colors.riskNeutralBorder,
          text: colors.riskNeutral,
        };
      case 'outline':
        return {
          bg: 'transparent',
          border: colors.border,
          text: colors.textSecondary,
        };
      case 'secondary':
      case 'lavender':
        return {
          bg: colors.surfaceElevated,
          border: colors.border,
          text: colors.textSecondary,
        };
      case 'default':
      case 'mint':
      default:
        return {
          bg: colors.surfaceHighlight,
          border: colors.borderStrong,
          text: colors.textPrimary,
        };
    }
  };

  const badgeColors = getBadgeColors();

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: badgeColors.bg,
          borderColor: badgeColors.border,
        },
        style,
      ]}
    >
      {icon}
      <Text style={[styles.text, { color: badgeColors.text }, textStyle]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 5,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: MobileTheme.radii.badge,
    borderWidth: 1,
  },
  text: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
});
