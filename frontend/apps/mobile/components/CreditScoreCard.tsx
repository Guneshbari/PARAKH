import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { CreditAssessmentResult } from '@parakh/types';
import { Card } from './Card';
import { RiskBadge } from './RiskBadge';
import { MobileTheme, useTheme } from '../lib/theme';
import { Sparkles, ShieldCheck, Activity } from 'lucide-react-native';

interface MobileCreditScoreCardProps {
  assessment: CreditAssessmentResult;
  onPress?: () => void;
}

export function CreditScoreCard({ assessment, onPress }: MobileCreditScoreCardProps) {
  let colors = MobileTheme.colors;
  try {
    const theme = useTheme();
    colors = theme.colors;
  } catch {}

  return (
    <Card interactive={!!onPress} onPress={onPress} style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleContainer}>
          <Sparkles size={13} color={colors.textPrimary} />
          <Text style={[styles.headerTitle, { color: colors.textSecondary }]}>
            ALTERNATIVE CREDIT ASSESSMENT
          </Text>
        </View>
        <RiskBadge riskLevel={assessment.riskLevel} />
      </View>

      <View style={styles.scoreRow}>
        <Text style={[styles.scoreNumber, { color: colors.textPrimary }]}>
          {assessment.score}
        </Text>
        <Text style={[styles.scoreMax, { color: colors.textSecondary }]}>
          / {assessment.maxScore || 850}
        </Text>
      </View>

      <View style={[styles.divider, { backgroundColor: colors.border }]} />

      <View style={styles.metricsGrid}>
        <View style={styles.metricItem}>
          <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
            Repayment Stress
          </Text>
          <Text style={[styles.metricValue, { color: colors.textPrimary }]}>
            {assessment.estimatedRepaymentDifficulty}% Low
          </Text>
        </View>

        <View style={styles.metricItem}>
          <View style={styles.labelWithIcon}>
            <ShieldCheck size={11} color={colors.textSecondary} />
            <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
              Confidence
            </Text>
          </View>
          <Text style={[styles.metricValue, { color: colors.textPrimary }]}>
            {assessment.modelConfidence}% High
          </Text>
        </View>

        <View style={styles.metricItem}>
          <View style={styles.labelWithIcon}>
            <Activity size={11} color={colors.textSecondary} />
            <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
              Rebound Rate
            </Text>
          </View>
          <Text style={[styles.metricValue, { color: colors.textPrimary }]}>
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
    flexWrap: 'wrap',
    gap: 6,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  headerTitle: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  scoreNumber: {
    fontSize: 46,
    fontWeight: '900',
    letterSpacing: -1,
  },
  scoreMax: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 6,
  },
  divider: {
    height: 1,
    marginVertical: 4,
  },
  metricsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 8,
  },
  metricItem: {
    gap: 2,
    minWidth: 80,
  },
  labelWithIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metricLabel: {
    fontSize: 10,
    fontWeight: '500',
  },
  metricValue: {
    fontSize: 12,
    fontWeight: '700',
  },
});
