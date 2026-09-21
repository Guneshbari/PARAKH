import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Sparkles, Activity, ShieldCheck, ArrowRight } from 'lucide-react-native';
import { MobileTheme } from '../lib/theme';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { FloatingBottomNav, TabKey } from '../components/FloatingBottomNav';

export default function MobileHomeScreen() {
  const insets = useSafeAreaInsets();
  const [activeTab, setActiveTab] = useState<TabKey>('home');
  const [portal, setPortal] = useState<'user' | 'admin'>('user');

  return (
    <View style={styles.screen}>
      <ScrollView
        contentContainerStyle={[
          styles.scrollContent,
          {
            paddingTop: insets.top + 16,
            paddingBottom: insets.bottom + 100,
          },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Top Header / Portal Switcher */}
        <View style={styles.headerRow}>
          <View style={styles.brandContainer}>
            <View style={styles.brandIcon}>
              <Sparkles size={16} color="#042F2E" />
            </View>
            <View>
              <Text style={styles.brandTitle}>PARAKH</Text>
              <Text style={styles.brandSubtitle}>Credit for the Invisible</Text>
            </View>
          </View>

          {/* Quick Portal Switcher Pills */}
          <View style={styles.portalToggle}>
            <Button
              title="Borrower"
              size="sm"
              variant={portal === 'user' ? 'mint' : 'outline'}
              onPress={() => setPortal('user')}
              style={styles.toggleButton}
            />
            <Button
              title="Underwriter"
              size="sm"
              variant={portal === 'admin' ? 'mint' : 'outline'}
              onPress={() => setPortal('admin')}
              style={styles.toggleButton}
            />
          </View>
        </View>

        {/* Editorial Heading */}
        <View style={styles.editorialSection}>
          <Badge
            label={portal === 'user' ? 'Borrower Assessment' : 'Underwriter Cockpit'}
            variant="lavender"
            icon={<Sparkles size={12} color={MobileTheme.colors.lavender} />}
          />
          <Text style={styles.editorialHeading}>
            {portal === 'user'
              ? 'Your PARAKH Assessment'
              : 'Portfolio Risk Radar'}
          </Text>
          <Text style={styles.editorialDescription}>
            {portal === 'user'
              ? 'Volatility-aware credit intelligence distinguishing healthy gig cycles from financial distress.'
              : 'Algorithmic model metrics separated from human verification review outcomes.'}
          </Text>
        </View>

        {/* Primary Benchmark Score Card */}
        <Card interactive style={styles.benchmarkCard}>
          <View style={styles.cardHeaderRow}>
            <Text style={styles.cardSubtitle}>
              {portal === 'user' ? 'Alternative Credit Score' : 'Cohort Benchmark'}
            </Text>
            <Badge label="LOWER ESTIMATED RISK" variant="riskLower" />
          </View>

          <View style={styles.scoreRow}>
            <Text style={styles.scoreValue}>742</Text>
            <Text style={styles.scoreMax}> / 850</Text>
          </View>

          <View style={styles.divider} />

          <View style={styles.metaRow}>
            <View>
              <Text style={styles.metaLabel}>Repayment Difficulty</Text>
              <Text style={styles.metaValue}>21% (Low)</Text>
            </View>
            <View style={styles.alignRight}>
              <Text style={styles.metaLabel}>Data Confidence</Text>
              <Text style={[styles.metaValue, { color: MobileTheme.colors.mint }]}>
                87% High
              </Text>
            </View>
          </View>
        </Card>

        {/* Volatility Metrics Card */}
        <Card interactive style={styles.metricCard}>
          <View style={styles.cardHeaderRow}>
            <Text style={styles.cardSubtitle}>Volatility Resilience</Text>
            <Activity size={16} color={MobileTheme.colors.mint} />
          </View>

          <View style={styles.metricRow}>
            <Text style={styles.metricValue}>94%</Text>
            <Text style={styles.metricLabel}>Recovery rate after low-earning weeks</Text>
          </View>

          <View style={styles.divider} />

          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Shock Cycle Count</Text>
            <Text style={styles.metaValue}>3 Dips Fully Absorbed</Text>
          </View>
        </Card>

        {/* Contextual AI Insight Card (Reference Style) */}
        <Card style={styles.aiCard}>
          <View style={styles.aiHeader}>
            <Sparkles size={14} color={MobileTheme.colors.lavender} />
            <Text style={styles.aiTitle}>PARAKH AI Insight</Text>
          </View>

          <Text style={styles.aiText}>
            &ldquo;Weekly earning variations follow normal platform ride-hail seasonal rhythms.
            Zero missed utility payments over the past 6 shock cycles.&rdquo;
          </Text>

          <View style={styles.aiFooter}>
            <Text style={styles.aiSubtext}>Explainable Feature Signal</Text>
            <Badge label="Validated" variant="lavender" />
          </View>
        </Card>

        {/* Action Button */}
        <Button
          title={portal === 'user' ? 'Start New Assessment' : 'View Priority Queue (4)'}
          variant="default"
          size="default"
          icon={
            portal === 'user' ? (
              <ArrowRight size={18} color="#042F2E" />
            ) : (
              <ShieldCheck size={18} color="#042F2E" />
            )
          }
          style={styles.primaryActionButton}
        />
      </ScrollView>

      {/* Floating Bottom Navigation Bar */}
      <FloatingBottomNav
        activeTab={activeTab}
        onTabSelect={(tab) => setActiveTab(tab)}
        portal={portal}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: MobileTheme.colors.background,
  },
  scrollContent: {
    paddingHorizontal: 20,
    gap: 16,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  brandContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  brandIcon: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: MobileTheme.colors.mint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: MobileTheme.colors.textPrimary,
    letterSpacing: -0.2,
  },
  brandSubtitle: {
    fontSize: 10,
    color: MobileTheme.colors.textSecondary,
  },
  portalToggle: {
    flexDirection: 'row',
    gap: 6,
  },
  toggleButton: {
    paddingVertical: 5,
    paddingHorizontal: 10,
  },
  editorialSection: {
    gap: 8,
    marginVertical: 4,
  },
  editorialHeading: {
    fontSize: 28,
    fontWeight: '800',
    color: MobileTheme.colors.textPrimary,
    letterSpacing: -0.5,
  },
  editorialDescription: {
    fontSize: 14,
    color: MobileTheme.colors.textSecondary,
    lineHeight: 20,
  },
  benchmarkCard: {
    backgroundColor: MobileTheme.colors.surface,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  cardSubtitle: {
    fontSize: 13,
    color: MobileTheme.colors.textSecondary,
    fontWeight: '500',
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginVertical: 4,
  },
  scoreValue: {
    fontSize: 48,
    fontWeight: '900',
    color: MobileTheme.colors.textPrimary,
    letterSpacing: -1,
  },
  scoreMax: {
    fontSize: 20,
    color: MobileTheme.colors.textSecondary,
    fontWeight: '600',
  },
  divider: {
    height: 1,
    backgroundColor: MobileTheme.colors.border,
    marginVertical: 12,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  alignRight: {
    alignItems: 'flex-end',
  },
  metaLabel: {
    fontSize: 11,
    color: MobileTheme.colors.textSecondary,
  },
  metaValue: {
    fontSize: 13,
    fontWeight: '700',
    color: MobileTheme.colors.textPrimary,
    marginTop: 2,
  },
  metricCard: {
    backgroundColor: MobileTheme.colors.surface,
  },
  metricRow: {
    marginVertical: 4,
  },
  metricValue: {
    fontSize: 36,
    fontWeight: '800',
    color: MobileTheme.colors.textPrimary,
  },
  metricLabel: {
    fontSize: 12,
    color: MobileTheme.colors.textSecondary,
    marginTop: 2,
  },
  aiCard: {
    backgroundColor: '#1E1B2E',
    borderColor: 'rgba(196, 181, 253, 0.2)',
  },
  aiHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  aiTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: MobileTheme.colors.lavender,
  },
  aiText: {
    fontSize: 13,
    color: '#DDD6FE',
    lineHeight: 19,
  },
  aiFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(196, 181, 253, 0.1)',
  },
  aiSubtext: {
    fontSize: 11,
    color: 'rgba(196, 181, 253, 0.6)',
  },
  primaryActionButton: {
    marginVertical: 8,
  },
});
