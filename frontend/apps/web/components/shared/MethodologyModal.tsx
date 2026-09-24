'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  Layers,
  Activity,
  TrendingUp,
  Scale,
  DollarSign,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type MethodologyPillarId =
  | 'all'
  | 'data'
  | 'volatility'
  | 'recovery'
  | 'obligations'
  | 'explainability'
  | 'governance';

interface MethodologyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MethodologyModal({ isOpen, onClose }: MethodologyModalProps) {
  const [activeTab, setActiveTab] = useState<MethodologyPillarId>('all');

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sections = [
    {
      id: 'data',
      number: '01',
      title: 'Alternative Data Ingestion',
      icon: Layers,
      badge: 'Consented Telemetry',
      summary:
        'Captures verified real-world operational cashflows rather than relying solely on traditional credit bureau scores.',
      points: [
        {
          label: 'Platform & Work Signals',
          desc: 'Cumulative partner tenure, order/task completion consistency, and sustained customer feedback ratings (e.g. Swiggy, Urban Company).',
        },
        {
          label: 'UPI & Merchant Cashflows',
          desc: 'High-frequency transaction volume, QR settlement cadence, and operational account turnover verified via RBI Account Aggregators.',
        },
        {
          label: 'Utility Settlement History',
          desc: 'Consecutive on-time payments across electricity (BESCOM), LPG gas refills, telecom, and recurring micro-obligations.',
        },
        {
          label: 'Consented Privacy Boundaries',
          desc: 'Purpose-limited ingestion operating strictly under the Digital Personal Data Protection (DPDP) Act 2023.',
        },
      ],
    },
    {
      id: 'volatility',
      number: '02',
      title: 'Volatility Normalization',
      icon: Activity,
      badge: 'Seasonality-Aware',
      summary:
        'Normal gig-income variation is mathematically isolated so cyclical seasonal swings are not misclassified as credit distress.',
      points: [
        {
          label: 'Separation of Volatility from Insolvency',
          desc: 'Traditional bureaus penalize weekly income variation as high risk. PARAKH standardizes coefficient of variation across a rolling 12-week window.',
        },
        {
          label: 'Monsoon & Weather Multipliers',
          desc: 'Algorithmic dampening during heavy seasonal rainfall or regional festivals prevents temporary demand shifts from lowering worker scores.',
        },
        {
          label: 'Multi-Channel Diversification',
          desc: 'Cross-platform earners who balance multiple platforms receive credit resilience adjustments for earnings independence.',
        },
      ],
    },
    {
      id: 'recovery',
      number: '03',
      title: 'Shock Rebound Dynamics',
      icon: TrendingUp,
      badge: '10–14 Day Velocity',
      summary:
        'Measures how rapidly cashflow rebounds to baseline following an earning shock, quantifying behavioral resilience.',
      points: [
        {
          label: 'Shock Rebound Velocity',
          desc: 'Empirically proven that 93%+ of informal worker earning dips recover to baseline within 10 to 14 days.',
        },
        {
          label: 'Historical Recovery Ratio',
          desc: 'Ratio of low-income weeks followed by rapid positive recovery cycles (e.g. 3 of 3 shocks successfully recovered = 100% resilience).',
        },
        {
          label: 'Punctuality Maintenance',
          desc: 'Proves whether debt commitments and micro-obligations remained 100% paid during the temporary earning dip.',
        },
      ],
    },
    {
      id: 'obligations',
      number: '04',
      title: 'Financial Commitments & Cushion',
      icon: DollarSign,
      badge: 'Safe Debt Buffer',
      summary:
        'Calculates real disposable cushion between fixed obligations and fluctuating informal inflows.',
      points: [
        {
          label: 'Obligation-to-Inflow Ratio',
          desc: 'Fixed recurring liabilities (rent, existing micro-loans, utility baselines) must remain below safe thresholds (typically <35% of median inflow).',
        },
        {
          label: 'Repayment Difficulty Index',
          desc: 'Predictive probabilistic estimate (e.g. 21% Low Difficulty) measuring debt-service friction under seasonal stress scenarios.',
        },
        {
          label: 'Discretionary Surplus',
          desc: 'Quantifies net disposable capital available after mandatory household and platform operating expenses.',
        },
      ],
    },
    {
      id: 'explainability',
      number: '05',
      title: 'Explainable AI & SHAP Attributions',
      icon: Sparkles,
      badge: 'No Black Boxes',
      summary:
        'Every score is paired with transparent SHAP feature contributions, positive drivers, and actionable recommendations.',
      points: [
        {
          label: 'Feature Weight Divergence',
          desc: 'SHAP (SHapley Additive exPlanations) bars reveal exact positive (+42% Rebound Velocity) and negative (-15% Single Platform) weights.',
        },
        {
          label: 'Positive vs. Attention Factors',
          desc: 'Non-technical translation separating strong discipline from areas requiring supplementary documentation.',
        },
        {
          label: 'Confidence Interval',
          desc: 'Standardized model confidence score (e.g. 87% with confidence bounds [728–756]) based on data quality and feed freshness.',
        },
      ],
    },
    {
      id: 'governance',
      number: '06',
      title: 'Human Review & Non-Lending Boundary',
      icon: Scale,
      badge: 'Human-in-the-Loop',
      summary:
        'PARAKH is an assessment intelligence engine. It never executes automated loan originations or binding credit approvals.',
      points: [
        {
          label: 'Statutory Independence',
          desc: 'Algorithmic scores serve as explanatory decision-support evidence for institutional credit partners.',
        },
        {
          label: 'Certified Credit Reviews',
          desc: 'Non-standard volatility patterns undergo human review (MANUAL_REVIEW, REQUEST_VERIFICATION, RECORD_OUTCOME) by certified officers.',
        },
        {
          label: 'Fairlearn Bias Audits',
          desc: 'Continuous demographic parity testing (0.97 parity ratio) ensures fair evaluation across informal trades and geographic tiers.',
        },
      ],
    },
  ];

  const displayedSections =
    activeTab === 'all'
      ? sections
      : sections.filter((s) => s.id === activeTab);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="methodology-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-background/80 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="bg-surface border border-border rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between p-5 sm:p-6 border-b border-border bg-surface">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-lg bg-surface-highlight border border-border flex items-center justify-center text-foreground">
                <Sparkles className="size-4" />
              </div>
              <h2 id="methodology-modal-title" className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
                PARAKH Assessment Methodology
              </h2>
              <Badge variant="outline" className="text-xs py-0.5 px-2 font-mono">
                v2.4 Framework
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary max-w-2xl leading-relaxed">
              How PARAKH translates informal earnings, seasonal volatility, and shock rebound dynamics into explainable alternative credit intelligence.
            </p>
          </div>

          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 rounded-xl text-foreground-secondary hover:text-foreground hover:bg-surface-highlight transition-colors cursor-pointer"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Pillar Navigation Pills */}
        <div className="px-5 py-3 border-b border-border bg-surface-elevated/40 flex items-center gap-1.5 overflow-x-auto text-xs sm:text-sm scrollbar-none">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap transition-all cursor-pointer ${
              activeTab === 'all'
                ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                : 'text-foreground-secondary hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-surface-highlight'
            }`}
          >
            All 6 Pillars
          </button>
          {sections.map((sec) => (
            <button
              key={sec.id}
              onClick={() => setActiveTab(sec.id as MethodologyPillarId)}
              className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap transition-all cursor-pointer ${
                activeTab === sec.id
                  ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                  : 'text-foreground-secondary hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-surface-highlight'
              }`}
            >
              {sec.number}. {sec.title.split(' ')[0]}
            </button>
          ))}
        </div>

        {/* Scrollable Content Body */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6 text-xs sm:text-sm divide-y divide-border">
          {displayedSections.map((sec) => {
            const Icon = sec.icon;
            return (
              <div key={sec.id} className="pt-6 first:pt-0 space-y-3.5">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono font-semibold text-foreground-secondary text-sm">
                      {sec.number}
                    </span>
                    <Icon className="size-4 text-foreground-secondary" />
                    <h3 className="text-sm sm:text-base font-semibold text-foreground tracking-tight">
                      {sec.title}
                    </h3>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono">
                    {sec.badge}
                  </Badge>
                </div>

                <p className="text-foreground-secondary text-xs sm:text-sm leading-relaxed max-w-3xl">
                  {sec.summary}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                  {sec.points.map((pt) => (
                    <div
                      key={pt.label}
                      className="p-3 rounded-xl bg-surface-highlight/40 border border-border space-y-1"
                    >
                      <span className="font-semibold text-foreground flex items-center gap-1.5 text-xs sm:text-sm">
                        <CheckCircle2 className="size-3 text-foreground-secondary shrink-0" />
                        {pt.label}
                      </span>
                      <p className="text-xs text-foreground-secondary leading-relaxed pl-4.5">
                        {pt.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-4 sm:p-5 border-t border-border bg-surface flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm text-foreground-secondary">
          <div className="flex items-center gap-2">
            <Info className="size-3.5 text-foreground-secondary shrink-0" />
            <span>
              DPDP Act 2023 Compliant • Purpose: Alternative Credit Evaluation Only
            </span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={onClose}
            className="rounded-full text-xs h-8 px-4 w-full sm:w-auto"
          >
            Close Dossier
          </Button>
        </div>
      </div>
    </div>
  );
}
