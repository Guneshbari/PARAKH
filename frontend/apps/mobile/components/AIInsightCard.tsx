import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Card } from './Card';
import { Button } from './Button';
import { MobileTheme } from '../lib/theme';
import { Sparkles, ArrowRight } from 'lucide-react-native';

interface MobileAIInsightCardProps {
  title?: string;
  insight: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function AIInsightCard({
  title = 'PARAKH AI Insight',
  insight,
  actionLabel,
  onAction,
}: MobileAIInsightCardProps) {
  return (
    <Card style={styles.card}>
      <View style={styles.header}>
        <Sparkles size={14} color={MobileTheme.colors.lavender} />
        <Text style={styles.title}>{title}</Text>
      </View>

      <Text style={styles.insightText}>&ldquo;{insight}&rdquo;</Text>

      {(actionLabel || onAction) && (
        <View style={styles.footer}>
          <Text style={styles.subtext}>Explainable Feature Signal</Text>
          {actionLabel && (
            <Button
              title={actionLabel}
              size="sm"
              variant="lavender"
              onPress={onAction}
              icon={<ArrowRight size={14} color="#1E1B2E" />}
            />
          )}
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#131622',
    borderColor: 'rgba(196, 181, 253, 0.2)',
    gap: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  title: {
    fontSize: 12,
    fontWeight: '700',
    color: MobileTheme.colors.lavender,
    letterSpacing: 0.3,
  },
  insightText: {
    fontSize: 13,
    color: '#DDD6FE',
    lineHeight: 19,
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(196, 181, 253, 0.12)',
    marginTop: 2,
  },
  subtext: {
    fontSize: 11,
    color: 'rgba(196, 181, 253, 0.65)',
  },
});
