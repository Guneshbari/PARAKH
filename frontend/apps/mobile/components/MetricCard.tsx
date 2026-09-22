import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Card } from './Card';
import { Badge, BadgeVariant } from './Badge';
import { MobileTheme, useTheme } from '../lib/theme';

interface MobileMetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  pillLabel?: string;
  pillVariant?: BadgeVariant;
  icon?: React.ReactNode;
  onPress?: () => void;
}

export function MetricCard({
  title,
  value,
  subtitle,
  pillLabel,
  pillVariant = 'secondary',
  icon,
  onPress,
}: MobileMetricCardProps) {
  let colors = MobileTheme.colors;
  try {
    const theme = useTheme();
    colors = theme.colors;
  } catch {}

  return (
    <Card interactive={!!onPress} onPress={onPress} style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={[styles.title, { color: colors.textSecondary }]}>{title}</Text>
        {pillLabel && <Badge label={pillLabel} variant={pillVariant} />}
        {icon && !pillLabel && icon}
      </View>

      <Text style={[styles.value, { color: colors.textPrimary }]}>{value}</Text>

      {subtitle && (
        <View style={[styles.footer, { borderTopColor: colors.border }]}>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>{subtitle}</Text>
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 8,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 4,
  },
  title: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  value: {
    fontSize: 32,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  footer: {
    paddingTop: 8,
    borderTopWidth: 1,
  },
  subtitle: {
    fontSize: 11,
  },
});
