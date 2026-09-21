import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Sparkles, Activity, ShieldCheck, ArrowRight, Sun, Moon } from 'lucide-react-native';
import { useTheme } from '../lib/theme';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { FloatingBottomNav, TabKey } from '../components/FloatingBottomNav';

export default function MobileHomeScreen() {
  const insets = useSafeAreaInsets();
  const { colors, isDark, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<TabKey>('home');
  const [portal, setPortal] = useState<'user' | 'admin'>('user');

  return (
    <View style={[styles.screen, { backgroundColor: colors.background }]}>
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
            <View
              style={[
                styles.brandIcon,
                {
                  backgroundColor: colors.surfaceElevated,
                  borderColor: colors.border,
                },
              ]}
            >
              <Sparkles size={16} color={colors.textPrimary} />
            </View>
            <View>
              <Text style={[styles.brandTitle, { color: colors.textPrimary }]}>PARAKH</Text>
              <Text style={[styles.brandSubtitle, { color: colors.textSecondary }]}>Credit for the Invisible</Text>
            </View>
          </View>

          <View style={styles.headerActions}>
            {/* Theme Switcher Pill */}
            <Pressable
              onPress={toggleTheme}
              style={[
                styles.themeToggleBtn,
                {
                  backgroundColor: colors.surfaceElevated,
                  borderColor: colors.border,
                },
              ]}
              accessibilityRole="button"
              accessibilityLabel={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            >
              {isDark ? (
                <Sun size={15} color={colors.textPrimary} />
              ) : (
                <Moon size={15} color={colors.textPrimary} />
              )}
            </Pressable>

            {/* Quick Portal Switcher Pills */}
            <View
              style={[
                styles.portalToggle,
                {
                  backgroundColor: colors.surfaceElevated,
                  borderColor: colors.border,
                },
              ]}
            >
              <Button
                title="Applicant"
                size="sm"
                variant={portal === 'user' ? 'default' : 'ghost'}
                onPress={() => setPortal('user')}
                style={styles.toggleButton}
              />
              <Button
                title="Credit Reviewer"
                size="sm"
                variant={portal === 'admin' ? 'default' : 'ghost'}
                onPress={() => setPortal('admin')}
                style={styles.toggleButton}
              />
            </View>
          </View>
        </View>

        {/* Editorial Heading */}
        <View style={styles.editorialSection}>
          <Badge
            label={portal === 'user' ? 'Applicant Assessment' : 'Credit Review Dashboard'}
            variant="secondary"
            icon={<Sparkles size={12} color={colors.textSecondary} />}
          />
          <Text style={[styles.editorialHeading, { color: colors.textPrimary }]}>
            {portal === 'user'
              ? 'Your PARAKH Assessment'
              : 'Applications for Review'}
          </Text>
          <Text style={[styles.editorialDescription, { color: colors.textSecondary }]}>
            {portal === 'user'
              ? 'Volatility-aware credit intelligence distinguishing healthy gig cycles from financial distress.'
              : 'Algorithmic model metrics separated from human credit reviewer verification outcomes.'}
          </Text>
        </View>

        {/* Primary Benchmark Score Card */}
        <Card
          interactive
          style={[
            styles.benchmarkCard,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
        >
          <View style={styles.cardHeaderRow}>
            <Text style={[styles.cardSubtitle, { color: colors.textSecondary }]}>
              {portal === 'user' ? 'Alternative Credit Score' : 'Cohort Benchmark'}
            </Text>
            <Badge label="LOWER ESTIMATED RISK" variant="riskLower" />
          </View>

          <View style={styles.scoreRow}>
            <Text style={[styles.scoreValue, { color: colors.textPrimary }]}>742</Text>
            <Text style={[styles.scoreMax, { color: colors.textMuted }]}> / 850</Text>
          </View>

          <View style={[styles.divider, { backgroundColor: colors.border }]} />

          <View style={styles.metaRow}>
            <View>
              <Text style={[styles.metaLabel, { color: colors.textSecondary }]}>Repayment Difficulty</Text>
              <Text style={[styles.metaValue, { color: colors.textPrimary }]}>21% (Low)</Text>
            </View>
            <View style={styles.alignRight}>
              <Text style={[styles.metaLabel, { color: colors.textSecondary }]}>Data Confidence</Text>
              <Text style={[styles.metaValue, { color: colors.textPrimary }]}>
                87% High
              </Text>
            </View>
          </View>
        </Card>

        {/* Volatility Metrics Card */}
        <Card
          interactive
          style={[
            styles.metricCard,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
        >
          <View style={styles.cardHeaderRow}>
            <Text style={[styles.cardSubtitle, { color: colors.textSecondary }]}>Volatility Resilience</Text>
            <Activity size={16} color={colors.textPrimary} />
          </View>

          <View style={styles.metricRow}>
            <Text style={[styles.metricValue, { color: colors.textPrimary }]}>94%</Text>
            <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>Recovery rate after low-earning weeks</Text>
          </View>

          <View style={[styles.divider, { backgroundColor: colors.border }]} />

          <View style={styles.metaRow}>
            <Text style={[styles.metaLabel, { color: colors.textSecondary }]}>Shock Cycle Count</Text>
            <Text style={[styles.metaValue, { color: colors.textPrimary }]}>3 Dips Fully Absorbed</Text>
          </View>
        </Card>

        {/* Contextual AI Insight Card */}
        <Card
          style={[
            styles.aiCard,
            {
              backgroundColor: colors.surfaceElevated,
              borderColor: colors.border,
            },
          ]}
        >
          <View style={styles.aiHeader}>
            <Sparkles size={14} color={colors.textPrimary} />
            <Text style={[styles.aiTitle, { color: colors.textPrimary }]}>PARAKH Decision Intelligence</Text>
          </View>

          <Text style={[styles.aiText, { color: colors.textSecondary }]}>
            &ldquo;Weekly earning variations follow normal platform ride-hail seasonal rhythms.
            Zero missed utility payments over the past 6 shock cycles.&rdquo;
          </Text>

          <View style={[styles.aiFooter, { borderTopColor: colors.border }]}>
            <Text style={[styles.aiSubtext, { color: colors.textMuted }]}>Explainable Feature Signal</Text>
            <Badge label="Audited Metric" variant="secondary" />
          </View>
        </Card>

        {/* Action Button */}
        <Button
          title={portal === 'user' ? 'Start New Assessment' : 'Applications for Review (4)'}
          variant="default"
          size="default"
          icon={
            portal === 'user' ? (
              <ArrowRight size={18} color={isDark ? '#08090A' : '#FFFFFF'} />
            ) : (
              <ShieldCheck size={18} color={isDark ? '#08090A' : '#FFFFFF'} />
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
    flexWrap: 'wrap',
    gap: 8,
  },
  brandContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  brandIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: -0.2,
  },
  brandSubtitle: {
    fontSize: 10,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  themeToggleBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  portalToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 3,
    borderRadius: 9999,
    borderWidth: 1,
    gap: 4,
  },
  toggleButton: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    minHeight: 28,
  },
  editorialSection: {
    gap: 8,
    marginVertical: 4,
  },
  editorialHeading: {
    fontSize: 26,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  editorialDescription: {
    fontSize: 13,
    lineHeight: 19,
  },
  benchmarkCard: {
    borderWidth: 1,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  cardSubtitle: {
    fontSize: 13,
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
    letterSpacing: -1,
  },
  scoreMax: {
    fontSize: 20,
    fontWeight: '600',
  },
  divider: {
    height: 1,
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
  },
  metaValue: {
    fontSize: 13,
    fontWeight: '700',
    marginTop: 2,
  },
  metricCard: {
    borderWidth: 1,
  },
  metricRow: {
    marginVertical: 4,
  },
  metricValue: {
    fontSize: 36,
    fontWeight: '800',
  },
  metricLabel: {
    fontSize: 12,
    marginTop: 2,
  },
  aiCard: {
    borderWidth: 1,
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
  },
  aiText: {
    fontSize: 13,
    lineHeight: 19,
  },
  aiFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
  },
  aiSubtext: {
    fontSize: 11,
  },
  primaryActionButton: {
    marginVertical: 8,
  },
});
