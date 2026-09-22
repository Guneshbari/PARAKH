'use client';

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  FileCheck,
  Scale,
  Layers,
  Printer,
  Info,
  Calendar,
  Cpu,
  Download,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { api, type BackendModelVersion } from '@parakh/api';
import { mockModelInsights } from '@/data/mock/admin';

export default function AdminModelInsightsPage() {
  const insights = mockModelInsights;
  const [modelVersions, setModelVersions] = useState<BackendModelVersion[]>([]);
  const [activeModel, setActiveModel] = useState<BackendModelVersion | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchModelData() {
      try {
        const versions = await api.getModelVersions();
        if (!isMounted) return;
        if (versions && versions.length > 0) {
          setModelVersions(versions);
          const active = versions.find((v) => v.is_active) || versions[0];
          setActiveModel(active);
        }
      } catch (err) {
        console.warn('Could not fetch model versions from backend:', err);
      }
    }
    fetchModelData();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleDownloadModelCard = () => {
    const cardData = {
      modelName: 'PARAKH Volatility-Aware Alternative Credit Assessment Engine',
      modelVersion: insights.modelVersion,
      architecture: 'Gradient Boosted Volatility Trees + Calibrated Logistic Ridge',
      trainingDataset: {
        anonymizedCashflowCycles: insights.datasetRecordsCount,
        jurisdiction: 'India (Karnataka, Telangana, Maharashtra pilots)',
        dataSources: ['Swiggy Partner API', 'Urban Company Partner Connect', 'NPCI Bharat BillPay', 'Sahamati Account Aggregator'],
      },
      fairnessAudit: {
        framework: 'Fairlearn Demographic Parity & Equalized Odds',
        demographicGroups: insights.fairnessMetrics,
        statutoryStandards: 'Digital Personal Data Protection Act 2023 & RBI Fair Practice Code',
      },
      globalFeatureWeights: insights.topFeatures,
      lastAuditedAt: insights.lastTrainedAt,
    };

    const blob = new Blob([JSON.stringify(cardData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PARAKH_Model_Governance_Card_${insights.modelVersion}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & GOVERNANCE BADGES */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Fairness, SHAP & Model Governance
            </h1>
            <Badge variant="mint" className="text-[10px] py-0.5 px-2">
              Audit Status: FAIR
            </Badge>
            <Badge variant="outline" className="text-[10px] font-mono">
              {insights.modelVersion}
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Fairlearn-aligned demographic parity audits, SHAP global feature rankings, and algorithmic version lineage.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadModelCard}
            className="rounded-full gap-1.5 text-xs text-foreground-secondary border-border hover:bg-surface-highlight"
          >
            <Download className="size-3.5" /> Export Model Card (JSON)
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Audit
          </Button>
        </div>
      </div>

      {/* 2. MODEL SPECIFICATION & ARCHITECTURE HERO STRIP */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Cpu className="size-3.5 text-foreground-secondary" />
            <span>Architecture</span>
          </div>
          <span className="text-sm font-bold text-foreground block truncate" title={activeModel?.algorithm || 'GB Volatility Trees'}>
            {activeModel ? activeModel.algorithm : 'GB Volatility Trees'}
          </span>
          <span className="text-[10px] text-foreground-secondary block truncate" title={activeModel?.model_name || 'Calibrated Ridge Blend'}>
            {activeModel ? activeModel.model_name : 'Calibrated Ridge Blend'}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Layers className="size-3.5 text-foreground-secondary" />
            <span>Training Dataset</span>
          </div>
          <span className="text-sm font-bold text-foreground font-mono block">
            {insights.datasetRecordsCount.toLocaleString()} Cycles
          </span>
          <span className="text-[10px] text-foreground-muted block">Anonymized Inflow Records</span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Calendar className="size-3.5 text-foreground-secondary" />
            <span>Last Retrained</span>
          </div>
          <span className="text-sm font-bold text-foreground block">
            {new Date(activeModel?.created_at || insights.lastTrainedAt).toLocaleDateString('en-IN', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
          <span className="text-[10px] text-foreground-secondary block">
            {activeModel ? `Version ${activeModel.version}` : 'Active Production Baseline'}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Scale className="size-3.5 text-foreground-secondary" />
            <span>Parity Framework</span>
          </div>
          <span className="text-sm font-bold text-foreground block">
            Fairlearn 0.97
          </span>
          <span className="text-[10px] text-foreground-secondary block">Zero Protected Disparities</span>
        </div>
      </div>

      {/* TRAINING PIPELINE / AUDIT IN PROGRESS NOTICE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/40 border border-border text-xs flex items-start gap-3">
        <AlertTriangle className="size-4 text-amber-500 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-foreground block">
            ML Training Pipeline & Fairlearn Demographic Audit in Progress
          </span>
          <p className="text-foreground-muted text-[11px] leading-relaxed">
            LightGBM and Logistic Regression synthetic feature calibration is actively being trained by Person 2 & 3. In the interim, live assessments are scored through the deterministic <strong className="text-foreground">{activeModel?.model_name || 'MockAssessmentEngine'}</strong> registered in PostgreSQL. The metrics below represent the baseline validation benchmark and target statutory thresholds.
          </p>
        </div>
      </div>

      {/* 3. FAIRLEARN DEMOGRAPHIC & COHORT PARITY AUDIT */}
      <Card className="p-6 bg-surface border-border space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
          <div>
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Scale className="size-4 text-foreground-secondary" />
              Statutory Demographic Parity & Fairness Audit (Fairlearn)
            </h2>
            <p className="text-xs text-foreground-muted">
              Evaluates demographic parity ratio and equalized odds differences across gig segments and geographies.
            </p>
          </div>

          <Badge variant="mint" className="text-[10px] py-0 px-2 font-mono">
            Compliant with RBI Fair Practice Code
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {insights.fairnessMetrics.map((item) => (
            <div
              key={item.attribute}
              className="p-4 rounded-2xl bg-surface-highlight/30 border border-border space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-xs font-semibold text-foreground block">{item.attribute}</span>
                  <span className="text-[11px] text-foreground-muted">{item.demographicGroup}</span>
                </div>
                <Badge variant="mint" className="text-[10px] py-0 px-2">
                  {item.auditStatus}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-border">
                <div>
                  <span className="text-[10px] text-foreground-muted block">
                    Demographic Parity Ratio
                  </span>
                  <span className="font-mono font-bold text-foreground text-sm">
                    {item.parityRatio.toFixed(2)}
                  </span>
                  <span className="text-[9px] text-foreground-muted block">
                    Benchmark: 0.80 – 1.25
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-foreground-muted block">
                    Equalized Odds Diff
                  </span>
                  <span className="font-mono font-semibold text-foreground-secondary text-sm">
                    {item.equalizedOddsDifference.toFixed(2)}
                  </span>
                  <span className="text-[9px] text-foreground-secondary block">Minimal Variance</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Explainability guidance */}
        <div className="p-3.5 rounded-xl bg-surface-highlight/20 border border-border text-[11px] text-foreground-muted flex items-start gap-2.5">
          <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            Parity ratios above 0.80 indicate that the alternative model does not systematically disadvantage specific informal occupations, geographical clusters, or demographic cohorts. Disparate impact testing is continuously audited upon every retrain cycle.
          </p>
        </div>
      </Card>

      {/* 4. GLOBAL SHAP FEATURE IMPORTANCE RANKINGS */}
      <Card className="p-6 bg-surface border-border space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
          <div>
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Sparkles className="size-4 opacity-75" />
              Global SHAP Feature Importance Rankings
            </h2>
            <p className="text-xs text-foreground-muted">
              Relative global weight distribution of mathematical factors governing volatility resilience scoring.
            </p>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono">
            Sum of Weights: 1.00
          </Badge>
        </div>

        <div className="space-y-4 pt-1">
          {insights.topFeatures.map((feat, idx) => {
            const percentage = (feat.importance * 100).toFixed(0);

            return (
              <div key={feat.feature} className="space-y-1.5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-foreground-muted text-[11px]">
                      0{idx + 1}
                    </span>
                    <span className="font-semibold text-foreground">{feat.displayName}</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-[11px] text-foreground-muted font-mono">
                      Weight: {feat.importance.toFixed(2)}
                    </span>
                    <span className="font-mono font-semibold text-foreground w-10 text-right">
                      {percentage}%
                    </span>
                  </div>
                </div>

                <div className="w-full h-1.5 rounded-full bg-surface-highlight overflow-hidden">
                  <div
                    style={{ width: `${percentage}%` }}
                    className="h-full rounded-full bg-[#472393] dark:bg-foreground transition-all duration-500"
                  />
                </div>

                <p className="text-[11px] text-foreground-muted leading-relaxed pl-6">
                  {feat.description}
                </p>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 5. MODEL VERSION AUDIT LINEAGE */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <FileCheck className="size-4 text-foreground-secondary" />
            Model Version Lineage & Regulatory Audit Log
          </h2>
          <span className="text-xs font-mono text-foreground-muted">
            {modelVersions.length > 0 ? `${modelVersions.length} Iterations Registered` : '4 Iterations Logged'}
          </span>
        </div>

        <div className="space-y-3 pt-1 text-xs">
          {modelVersions.length > 0 ? (
            modelVersions.map((mv) => (
              <div
                key={mv.id}
                className={`p-3.5 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                  mv.is_active
                    ? 'bg-surface-highlight/40 border-border'
                    : 'bg-surface-highlight/20 border-border'
                }`}
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-foreground">
                      {mv.model_name} (v{mv.version})
                    </span>
                    <Badge
                      variant={mv.is_active ? 'mint' : 'outline'}
                      className="text-[9px] py-0 px-1.5"
                    >
                      {mv.is_active ? 'Current Active' : 'Archived'}
                    </Badge>
                  </div>
                  <p className="text-foreground-secondary text-[11px]">
                    {mv.description || `Algorithm: ${mv.algorithm}`}
                  </p>
                </div>
                <span className="font-mono text-foreground-muted text-[11px] shrink-0">
                  {new Date(mv.created_at).toLocaleDateString('en-IN', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </span>
              </div>
            ))
          ) : (
            <>
              <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-foreground">v2.4-volatility-prod</span>
                    <Badge variant="mint" className="text-[9px] py-0 px-1.5">
                      Current Active
                    </Badge>
                  </div>
                  <p className="text-foreground-secondary text-[11px]">
                    Introduced localized monsoon precipitation multipliers; tuned rebound window to 10–14 days.
                  </p>
                </div>
                <span className="font-mono text-foreground-muted text-[11px] shrink-0">
                  Sep 10, 2026
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-surface-highlight/20 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-foreground">v2.3-telemetry-sync</span>
                    <Badge variant="outline" className="text-[9px] py-0 px-1.5">
                      Archived
                    </Badge>
                  </div>
                  <p className="text-foreground-muted text-[11px]">
                    Integrated Urban Company multi-tier task rating telemetry; calibrated AA cashflow weight.
                  </p>
                </div>
                <span className="font-mono text-foreground-muted text-[11px] shrink-0">
                  Jul 24, 2026
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-surface-highlight/20 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-foreground">v2.2-bbps-cadence</span>
                    <Badge variant="outline" className="text-[9px] py-0 px-1.5">
                      Archived
                    </Badge>
                  </div>
                  <p className="text-foreground-muted text-[11px]">
                    Expanded NPCI BBPS biller network telemetry ingestion to include electricity and LPG cylinder cadence.
                  </p>
                </div>
                <span className="font-mono text-foreground-muted text-[11px] shrink-0">
                  May 12, 2026
                </span>
              </div>
            </>
          )}
        </div>
      </Card>

      {/* 6. ALGORITHMIC ACCOUNTABILITY FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-[11px] text-foreground-muted flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Algorithmic Accountability & Explainability Declaration
          </span>
          <p>
            PARAKH algorithms undergo quarterly third-party algorithmic fairness audits. Model SHAP values provide clear explanations for every score output to avoid black-box automated lending decisions.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
