import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Card } from './Card';
import { Badge } from './Badge';
import { MobileTheme } from '../lib/theme';

interface MobileMetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  pillLabel?: string;
  pillVariant?: 'mint' | 'lavender' | 'riskLower' | 'riskModerate' | 'outline';
  icon?: React.ReactNode;
  onPress?: () => void;
}

export function MetricCard({
  title,
  value,
  subtitle,
  pillLabel,
  pillVariant = 'mint',
  icon,
  onPress,
}: MobileMetricCardProps) {
  return (
    <Card interactive={!!onPress} onPress={onPress} style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{title}</Text>
        {pillLabel && <Badge label={pillLabel} variant={pillVariant} />}
        {icon && !pillLabel && icon}
      </View>

      <Text style={styles.value}>{value}</Text>

      {subtitle && (
        <View style={styles.footer}>
          <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 10,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: 12,
    fontWeight: '700',
    color: MobileTheme.colors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  value: {
    fontSize: 34,
    fontWeight: '900',
    color: MobileTheme.colors.textPrimary,
    letterSpacing: -0.5,
  },
  footer: {
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: MobileTheme.colors.border,
  },
  subtitle: {
    fontSize: 12,
    color: MobileTheme.colors.textSecondary,
  },
});
