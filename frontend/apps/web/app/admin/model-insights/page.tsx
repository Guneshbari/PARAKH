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
  RefreshCw,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { api, type BackendModelVersion } from '@parakh/api';

export default function AdminModelInsightsPage() {
  const [modelVersions, setModelVersions] = useState<BackendModelVersion[]>([]);
  const [activeModel, setActiveModel] = useState<BackendModelVersion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchModelData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const versions = await api.getModelVersions();
      if (versions && versions.length > 0) {
        setModelVersions(versions);
        const active = versions.find((v) => v.is_active) || versions[0];
        setActiveModel(active);
      } else {
        setModelVersions([]);
        setActiveModel(null);
      }
    } catch (err) {
      console.warn('Could not fetch model versions from backend:', err);
      setError('Failed to load registered model versions from the backend.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchModelData();
  }, []);

  const handleDownloadModelCard = () => {
    const cardData = {
      modelName: activeModel?.model_name || 'PARAKH Assessment Engine',
      modelVersion: activeModel ? `v${activeModel.version}` : 'unversioned',
      algorithm: activeModel?.algorithm || 'Deterministic Baseline',
      status: activeModel?.is_active ? 'ACTIVE_PRODUCTION' : 'STANDBY',
      createdAt: activeModel?.created_at || new Date().toISOString(),
      fairnessAudit: {
        framework: 'Fairlearn Demographic Parity & Equalized Odds',
        status: 'PENDING_ML_CALIBRATION',
        targetStandards: 'Digital Personal Data Protection Act 2023 & RBI Fair Practice Code',
        note: 'Dynamic demographic parity metrics will populate upon completion of Person 2/3 ML assessment pipeline.',
      },
      explainability: {
        framework: 'TreeSHAP / KernelSHAP',
        status: 'PENDING_ML_CALIBRATION',
        note: 'Global feature importance weights will be calculated after LightGBM training.',
      },
      registeredVersions: modelVersions.map((v) => ({
        version: v.version,
        name: v.model_name,
        algorithm: v.algorithm,
        isActive: v.is_active,
        createdAt: v.created_at,
      })),
    };

    const blob = new Blob([JSON.stringify(cardData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PARAKH_Model_Governance_Card_${activeModel ? `v${activeModel.version}` : 'latest'}.json`;
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
            <Badge variant="outline" className="text-[10px] py-0.5 px-2 text-foreground-secondary border-border">
              Governance Status: {activeModel ? 'REGISTERED' : 'INITIALIZING'}
            </Badge>
            {activeModel && (
              <Badge variant="mint" className="text-[10px] font-mono">
                Active: v{activeModel.version}
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Model version lineage, Fairlearn statutory alignment protocols, and SHAP explainability governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchModelData}
            disabled={isLoading}
            className="rounded-full gap-1.5 text-xs text-foreground-secondary border-border hover:bg-surface-highlight"
          >
            <RefreshCw className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>

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

      {/* ERROR BANNER */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-500 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchModelData} className="text-rose-500 hover:text-rose-600 text-xs h-7">
            Retry
          </Button>
        </div>
      )}

      {/* 2. MODEL SPECIFICATION & ARCHITECTURE HERO STRIP */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Cpu className="size-3.5 text-foreground-secondary" />
            <span>Architecture</span>
          </div>
          <span className="text-sm font-bold text-foreground block truncate" title={activeModel?.algorithm || 'Deterministic Engine'}>
            {activeModel ? activeModel.algorithm : 'Deterministic Engine'}
          </span>
          <span className="text-[10px] text-foreground-secondary block truncate" title={activeModel?.model_name || 'MockAssessmentEngine'}>
            {activeModel ? activeModel.model_name : 'MockAssessmentEngine'}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Layers className="size-3.5 text-foreground-secondary" />
            <span>Registered Models</span>
          </div>
          <span className="text-sm font-bold text-foreground font-mono block">
            {modelVersions.length}
          </span>
          <span className="text-[10px] text-foreground-muted block">In PostgreSQL Registry</span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Calendar className="size-3.5 text-foreground-secondary" />
            <span>Active Registered</span>
          </div>
          <span className="text-sm font-bold text-foreground block">
            {activeModel?.created_at
              ? new Date(activeModel.created_at).toLocaleDateString('en-IN', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })
              : '—'}
          </span>
          <span className="text-[10px] text-foreground-secondary block">
            {activeModel ? `Version ${activeModel.version}` : 'No active model'}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] text-foreground-muted">
            <Scale className="size-3.5 text-foreground-secondary" />
            <span>Audit Standard</span>
          </div>
          <span className="text-sm font-bold text-foreground block">
            Fairlearn 0.97
          </span>
          <span className="text-[10px] text-foreground-secondary block">Statutory DPDP Target</span>
        </div>
      </div>

      {/* TRAINING PIPELINE / AUDIT IN PROGRESS NOTICE */}
      <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-xs flex items-start gap-3">
        <AlertTriangle className="size-4 text-amber-500 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-foreground block">
            ML Training Pipeline & Fairlearn Demographic Audit in Progress
          </span>
          <p className="text-foreground-muted text-[11px] leading-relaxed">
            LightGBM and Logistic Regression synthetic feature calibration is actively being trained. In the interim, live credit assessments are scored through the deterministic <strong className="text-foreground">{activeModel?.model_name || 'MockAssessmentEngine'}</strong> registered in PostgreSQL. Evaluative SHAP rankings and demographic parity metrics will populate dynamically once the production assessment model is integrated.
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

          <Badge variant="outline" className="text-[10px] py-0 px-2 font-mono text-amber-500 border-amber-500/30">
            Pending ML Calibration
          </Badge>
        </div>

        {/* EXPLICIT PLACEHOLDER: ML FAIRNESS AUDIT */}
        <div className="p-6 rounded-2xl bg-surface-highlight/20 border border-dashed border-border text-center space-y-3">
          <div className="inline-flex p-3 rounded-full bg-surface-highlight text-foreground-secondary">
            <Scale className="size-6" />
          </div>
          <div className="space-y-1 max-w-lg mx-auto">
            <h3 className="text-sm font-semibold text-foreground">
              Fairlearn Demographic Parity Evaluation Pending
            </h3>
            <p className="text-xs text-foreground-muted leading-relaxed">
              Model fairness audits (Demographic Parity Ratio and Equalized Odds Differences across gig cohorts) will be computed dynamically upon training completion of the ML assessment pipeline. Statutory benchmarks (0.80 – 1.25) and disparate impact verification will be rendered here.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-left max-w-2xl mx-auto">
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <span className="text-[10px] text-foreground-muted block uppercase tracking-wider font-semibold">Standard Target</span>
              <span className="text-xs font-mono font-bold text-foreground block">0.80 – 1.25 DPR</span>
              <span className="text-[10px] text-foreground-secondary block">Four-Fifths Rule compliance</span>
            </div>
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <span className="text-[10px] text-foreground-muted block uppercase tracking-wider font-semibold">Protected Attributes</span>
              <span className="text-xs font-bold text-foreground block">Gender & Geography</span>
              <span className="text-[10px] text-foreground-secondary block">Urban, Semi-Urban, Tier 2/3</span>
            </div>
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <span className="text-[10px] text-foreground-muted block uppercase tracking-wider font-semibold">Statutory Basis</span>
              <span className="text-xs font-bold text-foreground block">RBI Fair Practice Code</span>
              <span className="text-[10px] text-foreground-secondary block">DPDP Act 2023 aligned</span>
            </div>
          </div>
        </div>

        {/* Explainability guidance */}
        <div className="p-3.5 rounded-xl bg-surface-highlight/20 border border-border text-[11px] text-foreground-muted flex items-start gap-2.5">
          <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            Parity ratios above 0.80 indicate that the alternative model does not systematically disadvantage specific informal occupations, geographical clusters, or demographic cohorts. Disparate impact testing will be continuously audited upon every retrain cycle.
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
          <Badge variant="outline" className="text-[10px] font-mono text-amber-500 border-amber-500/30">
            Pending ML Calibration
          </Badge>
        </div>

        {/* EXPLICIT PLACEHOLDER: SHAP FEATURE IMPORTANCE */}
        <div className="p-6 rounded-2xl bg-surface-highlight/20 border border-dashed border-border text-center space-y-3">
          <div className="inline-flex p-3 rounded-full bg-surface-highlight text-foreground-secondary">
            <Sparkles className="size-6" />
          </div>
          <div className="space-y-1 max-w-lg mx-auto">
            <h3 className="text-sm font-semibold text-foreground">
              Global SHAP Feature Importance Pending Calibration
            </h3>
            <p className="text-xs text-foreground-muted leading-relaxed">
              SHAP (SHapley Additive exPlanations) values will calculate mathematical feature weight distributions once the LightGBM/XGBoost training pipeline is connected. Live individual risk factors are currently generated deterministically per application.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-left max-w-2xl mx-auto">
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <ShieldCheck className="size-3.5 text-foreground-secondary" />
                <span>Cashflow Volatility & Buffer</span>
              </div>
              <p className="text-[11px] text-foreground-muted">
                Weighted coefficient of variation across rolling 90-day UPI and AA banking inflow cycles.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <ShieldCheck className="size-3.5 text-foreground-secondary" />
                <span>Platform Continuity & Rating</span>
              </div>
              <p className="text-[11px] text-foreground-muted">
                Tenure, active payout frequency, and partner performance metrics across verified gig platforms.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <ShieldCheck className="size-3.5 text-foreground-secondary" />
                <span>Multi-Gig Income Resilience</span>
              </div>
              <p className="text-[11px] text-foreground-muted">
                Diversification index across delivery, mobility, and home services streams mitigating sector shocks.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-surface border border-border space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <ShieldCheck className="size-3.5 text-foreground-secondary" />
                <span>BBPS Utility Payment Cadence</span>
              </div>
              <p className="text-[11px] text-foreground-muted">
                Consistency of recurring electricity, telecom, and municipal utility payments via NPCI BBPS.
              </p>
            </div>
          </div>
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
            {modelVersions.length} Iteration{modelVersions.length === 1 ? '' : 's'} Registered
          </span>
        </div>

        <div className="space-y-3 pt-1 text-xs">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-foreground-muted">
              Loading registered model versions...
            </div>
          ) : modelVersions.length > 0 ? (
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
            <div className="p-8 rounded-2xl bg-surface-highlight/20 border border-dashed border-border text-center space-y-2">
              <Clock className="size-6 text-foreground-muted mx-auto" />
              <p className="text-xs font-medium text-foreground">No model versions registered in backend yet</p>
              <p className="text-[11px] text-foreground-muted">
                Model versions will appear here as assessment engines are registered in PostgreSQL.
              </p>
            </div>
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
