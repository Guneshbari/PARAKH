import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { CreditAssessmentResult } from '@parakh/types';
import { Card } from './Card';
import { RiskBadge } from './RiskBadge';
import { MobileTheme } from '../lib/theme';
import { Sparkles, ShieldCheck, Activity } from 'lucide-react-native';

interface MobileCreditScoreCardProps {
  assessment: CreditAssessmentResult;
  onPress?: () => void;
}

export function CreditScoreCard({ assessment, onPress }: MobileCreditScoreCardProps) {
  return (
    <Card interactive={!!onPress} onPress={onPress} style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleContainer}>
          <Sparkles size={14} color={MobileTheme.colors.mint} />
          <Text style={styles.headerTitle}>PARAKH ASSESSMENT</Text>
        </View>
        <RiskBadge riskLevel={assessment.riskLevel} />
      </View>

      <View style={styles.scoreRow}>
        <Text style={styles.scoreNumber}>{assessment.score}</Text>
        <Text style={styles.scoreMax}> / {assessment.maxScore || 850}</Text>
      </View>

      <View style={styles.divider} />

      <View style={styles.metricsGrid}>
        <View style={styles.metricItem}>
          <Text style={styles.metricLabel}>Repayment Difficulty</Text>
          <Text style={styles.metricValue}>
            {assessment.estimatedRepaymentDifficulty}% Low
          </Text>
        </View>

        <View style={styles.metricItem}>
          <View style={styles.labelWithIcon}>
            <ShieldCheck size={12} color={MobileTheme.colors.mint} />
            <Text style={styles.metricLabel}>Confidence</Text>
          </View>
          <Text style={[styles.metricValue, { color: MobileTheme.colors.mint }]}>
            {assessment.modelConfidence}% High
          </Text>
        </View>

        <View style={styles.metricItem}>
          <View style={styles.labelWithIcon}>
            <Activity size={12} color={MobileTheme.colors.lavender} />
            <Text style={styles.metricLabel}>Shock Recovery</Text>
          </View>
          <Text style={[styles.metricValue, { color: MobileTheme.colors.lavender }]}>
            {Math.round((assessment.volatilityProfile?.recoveryRateAfterLowIncome ?? 0.94) * 100)}%
          </Text>
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  headerTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: MobileTheme.colors.textSecondary,
    letterSpacing: 0.5,
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  scoreNumber: {
    fontSize: 48,
    fontWeight: '900',
    color: MobileTheme.colors.textPrimary,
    letterSpacing: -1,
  },
  scoreMax: {
    fontSize: 20,
    fontWeight: '600',
    color: MobileTheme.colors.textSecondary,
    marginLeft: 6,
  },
  divider: {
    height: 1,
    backgroundColor: MobileTheme.colors.border,
    marginVertical: 4,
  },
  metricsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metricItem: {
    gap: 3,
  },
  labelWithIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metricLabel: {
    fontSize: 11,
    color: MobileTheme.colors.textSecondary,
  },
  metricValue: {
    fontSize: 13,
    fontWeight: '700',
    color: MobileTheme.colors.textPrimary,
  },
});
