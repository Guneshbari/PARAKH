import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Card } from './Card';
import { Button } from './Button';
import { MobileTheme, useTheme } from '../lib/theme';
import { Sparkles, ArrowRight } from 'lucide-react-native';

interface MobileAIInsightCardProps {
  title?: string;
  insight: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function AIInsightCard({
  title = 'PARAKH AI INSIGHT',
  insight,
  actionLabel,
  onAction,
}: MobileAIInsightCardProps) {
  let colors = MobileTheme.colors;
  try {
    const theme = useTheme();
    colors = theme.colors;
  } catch {}

  return (
    <Card style={styles.card}>
      <View style={styles.header}>
        <Sparkles size={13} color={colors.textPrimary} />
        <Text style={[styles.title, { color: colors.textPrimary }]}>{title}</Text>
      </View>

      <Text style={[styles.insightText, { color: colors.textSecondary }]}>
        &ldquo;{insight}&rdquo;
      </Text>

      {(actionLabel || onAction) && (
        <View style={[styles.footer, { borderTopColor: colors.border }]}>
          <Text style={[styles.subtext, { color: colors.textMuted }]}>
            Explainable Feature Signal
          </Text>
          {actionLabel && (
            <Button
              title={actionLabel}
              size="sm"
              variant="secondary"
              onPress={onAction}
              icon={<ArrowRight size={12} color={colors.textPrimary} />}
            />
          )}
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  title: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  insightText: {
    fontSize: 12,
    lineHeight: 18,
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
    borderTopWidth: 1,
    marginTop: 2,
    flexWrap: 'wrap',
    gap: 6,
  },
  subtext: {
    fontSize: 10,
    fontFamily: 'monospace',
  },
});
