import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { MobileTheme } from '../lib/theme';

export type BadgeVariant =
  | 'riskLower'
  | 'riskModerate'
  | 'riskHigher'
  | 'riskNeutral'
  | 'mint'
  | 'lavender'
  | 'outline';

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
}

export function Badge({
  label,
  variant = 'mint',
  style,
  textStyle,
  icon,
}: BadgeProps) {
  const getBadgeColors = () => {
    switch (variant) {
      case 'riskLower':
        return {
          bg: 'rgba(52, 211, 153, 0.15)',
          border: 'rgba(52, 211, 153, 0.3)',
          text: MobileTheme.colors.riskLower,
        };
      case 'riskModerate':
        return {
          bg: 'rgba(251, 191, 36, 0.15)',
          border: 'rgba(251, 191, 36, 0.3)',
          text: MobileTheme.colors.riskModerate,
        };
      case 'riskHigher':
        return {
          bg: 'rgba(248, 113, 113, 0.15)',
          border: 'rgba(248, 113, 113, 0.3)',
          text: MobileTheme.colors.riskHigher,
        };
      case 'riskNeutral':
        return {
          bg: 'rgba(100, 116, 139, 0.15)',
          border: 'rgba(100, 116, 139, 0.3)',
          text: MobileTheme.colors.riskNeutral,
        };
      case 'lavender':
        return {
          bg: 'rgba(196, 181, 253, 0.15)',
          border: 'rgba(196, 181, 253, 0.3)',
          text: MobileTheme.colors.lavender,
        };
      case 'outline':
        return {
          bg: 'transparent',
          border: MobileTheme.colors.border,
          text: MobileTheme.colors.textSecondary,
        };
      default:
        return {
          bg: 'rgba(45, 212, 191, 0.15)',
          border: 'rgba(45, 212, 191, 0.3)',
          text: MobileTheme.colors.mint,
        };
    }
  };

  const colors = getBadgeColors();

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: colors.bg,
          borderColor: colors.border,
        },
        style,
      ]}
    >
      {icon}
      <Text style={[styles.text, { color: colors.text }, textStyle]}>
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
    gap: 6,
    paddingVertical: 5,
    paddingHorizontal: 12,
    borderRadius: MobileTheme.radii.badge,
    borderWidth: 1,
  },
  text: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
});
