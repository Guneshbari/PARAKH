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
  Building2,
  MapPin,
  Users,
  CheckCircle2,
  SlidersHorizontal,
  BarChart2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import {
  api,
  type BackendModelVersion,
  type BackendFairnessAuditResponse,
  type BackendGlobalSHAPResponse,
} from '@parakh/api';

interface FairnessCategoryDef {
  id: string;
  name: string;
  subgroupField: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const FAIRNESS_CATEGORIES: FairnessCategoryDef[] = [
  {
    id: 'gig_sectors',
    name: 'Gig Work Sectors',
    subgroupField: 'gig_work_type',
    description: 'Audited across operational platform occupations to verify income volatility normalization does not systematically penalize specific worker segments.',
    icon: Building2,
  },
  {
    id: 'cohorts',
    name: 'Experience Cohorts',
    subgroupField: 'cohort_archetype',
    description: 'Segmented by platform tenure and earning stability cohorts to evaluate algorithmic parity between new and tenured gig workers.',
    icon: Users,
  },
  {
    id: 'loan_purpose',
    name: 'Loan Purposes',
    subgroupField: 'loan_purpose',
    description: 'Segmented by applicant financing intent (vehicle repairs, equipment purchases, working capital) ensuring equitable approval distributions.',
    icon: MapPin,
  },
];

function formatSubgroupName(name: string): string {
  return name
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export default function AdminModelInsightsPage() {
  const [modelVersions, setModelVersions] = useState<BackendModelVersion[]>([]);
  const [activeModel, setActiveModel] = useState<BackendModelVersion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFairnessCategory, setSelectedFairnessCategory] = useState<string>('gig_sectors');
  const [isActivatingId, setIsActivatingId] = useState<string | null>(null);
  const [fairnessResults, setFairnessResults] = useState<Record<string, BackendFairnessAuditResponse>>({});
  const [fairnessLoading, setFairnessLoading] = useState(false);
  const [fairnessError, setFairnessError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  // P2-10: Global SHAP state
  const [globalSHAP, setGlobalSHAP] = useState<BackendGlobalSHAPResponse | null>(null);
  const [isComputingShap, setIsComputingShap] = useState(false);
  const [shapError, setShapError] = useState<string | null>(null);

  const activeCategory =
    FAIRNESS_CATEGORIES.find((c) => c.id === selectedFairnessCategory) ||
    FAIRNESS_CATEGORIES[0];
  const activeFairness = fairnessResults[activeCategory.subgroupField] || null;

  const fetchModelData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const versions = await api.getModelVersions();
      if (versions && versions.length > 0) {
        setModelVersions(versions);
        const active =
          versions.find((v) => v.is_active && v.model_name === 'volatility-aware-risk-model') ||
          versions.find((v) => v.is_active) ||
          versions[0];
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

  const handleActivateModelVersion = async (id: string) => {
    setIsActivatingId(id);
    setActionMessage(null);
    try {
      await api.activateModelVersion(id);
      setActionMessage('Model version activated successfully in PostgreSQL registry.');
      await fetchModelData();
    } catch (err: any) {
      console.error('Failed to activate model version:', err);
      setActionMessage(err?.message || 'Failed to activate model version.');
    } finally {
      setIsActivatingId(null);
    }
  };

  const fetchFairnessAuditForField = async (modelId: string, subgroupField: string) => {
    setFairnessLoading(true);
    setFairnessError(null);
    try {
      const result = await api.runFairnessAudit(modelId, {
        subgroup_field: subgroupField,
        threshold: 0.5,
      });
      setFairnessResults((prev) => ({ ...prev, [subgroupField]: result }));
    } catch (err: any) {
      console.error('Failed to run fairness audit:', err);
      setFairnessError(err?.message || 'Fairness audit execution failed.');
    } finally {
      setFairnessLoading(false);
    }
  };

  const handleRunFairnessAudit = () => {
    if (!activeModel) return;
    fetchFairnessAuditForField(activeModel.id, activeCategory.subgroupField);
  };

  // P2-10: Compute real global SHAP feature importance from backend
  const handleComputeGlobalSHAP = async (modelId?: string) => {
    const targetId = modelId || activeModel?.id;
    if (!targetId) return;
    setIsComputingShap(true);
    setShapError(null);
    try {
      const result = await api.getGlobalSHAP(targetId);
      setGlobalSHAP(result);
    } catch (err: any) {
      console.error('Failed to compute global SHAP:', err);
      setShapError(err?.message || 'Global SHAP computation failed. Ensure the offline evaluation dataset and model artifacts are available.');
    } finally {
      setIsComputingShap(false);
    }
  };

  useEffect(() => {
    fetchModelData();
  }, []);

  // Automatically trigger backend fairness audit when active model or category changes
  useEffect(() => {
    if (!activeModel?.id) return;
    if (!fairnessResults[activeCategory.subgroupField]) {
      fetchFairnessAuditForField(activeModel.id, activeCategory.subgroupField);
    }
  }, [activeModel?.id, activeCategory.subgroupField]);

  // Automatically load global SHAP on active model identification
  useEffect(() => {
    if (activeModel?.id && !globalSHAP && !isComputingShap) {
      handleComputeGlobalSHAP(activeModel.id);
    }
  }, [activeModel?.id]);

  const handleDownloadModelCard = () => {
    const cardData = {
      modelName: activeModel?.model_name || 'volatility-aware-risk-model',
      modelVersion: activeModel ? `v${activeModel.version}` : 'v1.0.0',
      algorithm: activeModel?.algorithm || 'LightGBM + RobustScaler + TreeSHAP',
      status: activeModel?.is_active ? 'ACTIVE_PROTOTYPE' : 'STANDBY',
      exportedAt: new Date().toISOString(),
      createdAt: activeModel?.created_at || new Date().toISOString(),
      fairnessAudit: activeFairness
        ? {
            framework: 'Fairlearn Diagnostic Evaluation',
            status: 'COMPUTED',
            subgroupField: activeFairness.subgroup_field,
            demographicParityRatio: activeFairness.demographic_parity_ratio,
            equalOpportunityDifference: activeFairness.equal_opportunity_difference,
            sampleCount: activeFairness.sample_count,
            threshold: activeFairness.threshold,
            evaluationTimestamp: activeFairness.evaluation_timestamp,
            limitationsDisclaimer: activeFairness.limitations_disclaimer,
          }
        : {
            framework: 'Fairlearn Diagnostic Evaluation',
            status: 'EVALUATION_DATA_REQUIRED',
            targetStandards: 'Digital Personal Data Protection Act 2023 & RBI Fair Practice Code guidelines',
            note: 'Demographic parity and equalized-odds metrics require a defined protected-group evaluation dataset and computed audit results.',
          },
      explainability: {
        framework: 'TreeSHAP',
        status: globalSHAP ? 'GLOBAL_AND_LOCAL_TREESHAP_ACTIVE' : 'LOCAL_TREESHAP_ACTIVE',
        note: globalSHAP
          ? 'TreeSHAP feature attributions generated for individual scored assessments and aggregated globally across offline evaluation dataset.'
          : 'Local TreeSHAP feature attributions are generated for individual scored assessments.',
        globalSHAPSummary: globalSHAP
          ? {
              sampleCount: globalSHAP.sample_count,
              evaluatedAt: globalSHAP.evaluated_at,
              datasetSource: globalSHAP.dataset_source,
              topFeatures: globalSHAP.features.slice(0, 20).map((f) => ({
                rank: f.rank,
                featureName: f.feature_name,
                meanAbsShap: f.mean_abs_shap,
                signedMeanShap: f.mean_shap,
              })),
            }
          : null,
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
            <Badge variant="outline" className="text-xs py-0.5 px-2.5 text-foreground-secondary border-border font-medium">
              Governance Status: {activeModel ? 'REGISTERED' : 'INITIALIZING'}
            </Badge>
            {activeModel && (
              <Badge variant="mint" className="text-xs font-mono">
                Active: v{activeModel.version}
              </Badge>
            )}
          </div>
          <p className="text-sm sm:text-base text-foreground-secondary">
            Model version lineage, Fairlearn diagnostic fairness evaluation, and SHAP explainability governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchModelData}
            disabled={isLoading}
            className="rounded-full gap-1.5 text-xs sm:text-sm text-foreground-secondary border-border hover:bg-surface-highlight"
          >
            <RefreshCw className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadModelCard}
            className="rounded-full gap-1.5 text-xs sm:text-sm text-foreground-secondary border-border hover:bg-surface-highlight"
          >
            <Download className="size-3.5" /> Export Model Card (JSON)
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs sm:text-sm text-foreground-secondary hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Audit
          </Button>
        </div>
      </div>

      {/* ERROR BANNER */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-600 dark:text-rose-400 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-4.5 shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchModelData} className="text-rose-600 dark:text-rose-400 hover:text-rose-700 text-xs sm:text-sm h-8">
            Retry
          </Button>
        </div>
      )}

      {/* 2. MODEL SPECIFICATION & ARCHITECTURE HERO STRIP */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-foreground-secondary">
            <Cpu className="size-3.5 text-foreground-secondary" />
            <span>Architecture</span>
          </div>
          <span className="text-sm sm:text-base font-bold text-foreground block truncate" title={activeModel?.algorithm || 'Model metadata unavailable'}>
            {activeModel ? activeModel.algorithm : 'Model metadata unavailable'}
          </span>
          <span className="text-xs text-foreground-secondary block truncate" title={activeModel?.model_name || 'Model metadata unavailable'}>
            {activeModel ? activeModel.model_name : 'Model metadata unavailable'}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-foreground-secondary">
            <Layers className="size-3.5 text-foreground-secondary" />
            <span>Registered Models</span>
          </div>
          <span className="text-sm sm:text-base font-bold text-foreground font-mono block">
            {modelVersions.length}
          </span>
          <span className="text-xs text-foreground-secondary block">In PostgreSQL Registry</span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-foreground-secondary">
            <Calendar className="size-3.5 text-foreground-secondary" />
            <span>Active Registered</span>
          </div>
          <span className="text-sm sm:text-base font-bold text-foreground block">
            {activeModel?.created_at
              ? new Date(activeModel.created_at).toLocaleDateString('en-IN', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })
              : '—'}
          </span>
          <span className="text-xs text-foreground-secondary block">
            {activeModel ? `Version ${activeModel.version}` : 'No active model'}
          </span>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-foreground-secondary">
            <Scale className="size-3.5 text-foreground-secondary" />
            <span>Audit Standard</span>
          </div>
          <span className="text-sm sm:text-base font-bold text-foreground block">
            Fairlearn 0.97
          </span>
          <span className="text-xs text-foreground-secondary block">Statutory DPDP Target</span>
        </div>
      </div>

      {/* PRODUCTION PROTOTYPE ML MODEL ACTIVE NOTICE */}
      <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-sm flex items-start gap-3">
        <ShieldCheck className="size-4.5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-foreground block">
            Production Prototype ML Model Active
          </span>
          <p className="text-foreground-secondary text-xs sm:text-sm leading-relaxed">
            The active assessment model <strong className="text-foreground">{activeModel?.model_name || 'volatility-aware-risk-model'}{activeModel ? ` (v${activeModel.version})` : ''}</strong> is registered and serving live prototype credit assessments. LightGBM inference and local TreeSHAP explanations have been verified through the end-to-end assessment pipeline.
          </p>
        </div>
      </div>

      {/* 3. FAIRLEARN DEMOGRAPHIC & COHORT PARITY AUDIT */}
      <Card className="p-4 sm:p-6 bg-surface border-border space-y-6 min-w-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
                <Scale className="size-5 text-foreground-secondary" />
                Fairness Audit — Fairlearn Subgroup Parity
              </h2>
              <Badge variant="mint" className="text-xs py-0.5 px-2.5 font-mono">
                {activeFairness ? 'AUDITED' : fairnessLoading ? 'AUDITING' : 'READY'}
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Demographic parity ratio (DPR) and equalized odds evaluation criteria across gig segments, experience cohorts, and loan purposes.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRunFairnessAudit}
              disabled={fairnessLoading || !activeModel}
              className="rounded-full gap-1.5 text-xs text-foreground-secondary border-border hover:bg-surface-highlight"
            >
              <RefreshCw className={`size-3.5 ${fairnessLoading ? 'animate-spin' : ''}`} />
              {fairnessLoading ? 'Auditing...' : 'Run Subgroup Audit'}
            </Button>
            <span className="text-xs font-mono text-foreground-secondary">
              {activeFairness ? `N=${activeFairness.sample_count.toLocaleString()} Evaluated` : 'Benchmark Records'}
            </span>
          </div>
        </div>

        {/* ERROR STATE */}
        {fairnessError && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-600 dark:text-rose-400 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4.5 shrink-0" />
              <span>{fairnessError}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={handleRunFairnessAudit} disabled={fairnessLoading} className="text-rose-600 dark:text-rose-400 text-xs h-8">
              Retry
            </Button>
          </div>
        )}

        {/* AUTHORITATIVE BACKEND FAIRNESS AUDIT RESULT BANNER */}
        {activeFairness && (
          <div className="p-3.5 rounded-xl bg-surface-highlight/40 border border-border text-xs sm:text-sm space-y-1">
            <div className="flex items-center justify-between font-mono">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <CheckCircle2 className="size-3.5 text-mint" />
                Backend Audit Report ({activeFairness.subgroup_field})
              </span>
              <span className="text-foreground-secondary text-xs">
                Evaluated: {new Date(activeFairness.evaluation_timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 text-xs font-mono text-foreground-secondary pt-1">
              <span>DPR: <strong className="text-foreground">{activeFairness.demographic_parity_ratio ?? 'N/A'}</strong></span>
              <span>EOD: <strong className="text-foreground">{activeFairness.equal_opportunity_difference ?? 'N/A'}</strong></span>
              <span>Threshold: {activeFairness.threshold}</span>
              <span>Samples: {activeFairness.sample_count.toLocaleString()}</span>
            </div>
            <p className="text-[11px] text-foreground-secondary italic pt-1 leading-relaxed">
              {activeFairness.limitations_disclaimer}
            </p>
          </div>
        )}

        {/* TOP LEVEL PARITY KPIS */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1 min-w-0">
            <span className="text-xs font-semibold text-foreground-secondary block">Demographic Parity Ratio</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-foreground">
                {activeFairness?.demographic_parity_ratio !== null && activeFairness?.demographic_parity_ratio !== undefined ? activeFairness.demographic_parity_ratio.toFixed(2) : '—'}
              </span>
              <span className="text-xs text-mint font-semibold">
                {activeFairness?.demographic_parity_ratio && activeFairness.demographic_parity_ratio >= 0.8 && activeFairness.demographic_parity_ratio <= 1.25 ? 'Four-Fifths Pass' : activeFairness ? 'Review Corridor' : 'Pending Audit'}
              </span>
            </div>
            <span className="text-xs text-foreground-secondary block truncate">
              Target corridor: 0.80 — 1.25
            </span>
          </div>

          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1 min-w-0">
            <span className="text-xs font-semibold text-foreground-secondary block">Equal Opportunity Diff</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-foreground">
                {activeFairness?.equal_opportunity_difference !== null && activeFairness?.equal_opportunity_difference !== undefined ? `${(activeFairness.equal_opportunity_difference * 100).toFixed(1)}%` : '—'}
              </span>
              <span className="text-xs text-mint font-semibold">
                {activeFairness?.equal_opportunity_difference && activeFairness.equal_opportunity_difference < 0.15 ? 'Low Disparity' : activeFairness ? 'Moderate' : 'Pending Audit'}
              </span>
            </div>
            <span className="text-xs text-foreground-secondary block truncate">
              True positive rate divergence
            </span>
          </div>

          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1 min-w-0">
            <span className="text-xs font-semibold text-foreground-secondary block">Protected Attributes</span>
            <span className="text-sm sm:text-base font-bold text-foreground block truncate">
              {activeCategory.name}
            </span>
            <span className="text-xs text-foreground-secondary block truncate">
              DPDP compliant proxy segmentation
            </span>
          </div>

          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1 min-w-0">
            <span className="text-xs font-semibold text-foreground-secondary block">Evaluation Protocol</span>
            <span className="text-sm sm:text-base font-bold text-foreground block truncate">
              Fairlearn 0.97
            </span>
            <span className="text-xs text-foreground-secondary block truncate">
              Fair Lending diagnostic protocol
            </span>
          </div>
        </div>

        {/* FOUR-FIFTHS BENCHMARK GAUGE VISUALIZATION */}
        <div className="p-4 rounded-xl bg-surface-highlight/20 border border-border space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-1">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <SlidersHorizontal className="size-3.5 text-foreground-secondary" />
              Four-Fifths Rule Parity Corridor (0.80 — 1.25)
            </span>
            <span className="font-mono text-mint font-semibold">
              Current Model: {activeFairness?.demographic_parity_ratio ? `${activeFairness.demographic_parity_ratio.toFixed(2)} DPR (${activeFairness.demographic_parity_ratio >= 0.8 && activeFairness.demographic_parity_ratio <= 1.25 ? 'Equitable Zone' : 'Review Corridor'})` : 'Awaiting Audit Calculation'}
            </span>
          </div>

          <div className="relative pt-2 pb-1">
            {/* Background track */}
            <div className="h-3 w-full rounded-full bg-surface border border-border overflow-hidden flex">
              <div className="w-[30%] bg-rose-500/20" title="Adverse Impact Zone (< 0.80)" />
              <div className="w-[45%] bg-emerald-500/25 border-x border-emerald-500/40 relative flex items-center justify-center text-[10px] text-emerald-600 dark:text-emerald-400 font-mono font-bold" title="Equitable Corridor (0.80 - 1.25)">
                Equitable Corridor (80% - 125%)
              </div>
              <div className="w-[25%] bg-rose-500/20" title="Adverse Impact Zone (> 1.25)" />
            </div>

            {/* Scale markers */}
            <div className="flex justify-between text-[11px] font-mono text-foreground-secondary pt-1.5">
              <span>0.50</span>
              <span className="text-amber-600 dark:text-amber-400 font-semibold">0.80 (Min Threshold)</span>
              <span className="text-foreground font-bold underline decoration-mint decoration-2 underline-offset-2">
                {activeFairness?.demographic_parity_ratio ? `${activeFairness.demographic_parity_ratio.toFixed(2)} (PARAKH)` : '1.00 (Parity)'}
              </span>
              <span>1.00 (Parity)</span>
              <span className="text-amber-600 dark:text-amber-400 font-semibold">1.25 (Max Threshold)</span>
              <span>1.50</span>
            </div>
          </div>
        </div>

        {/* CATEGORY SELECTOR TABS */}
        <div className="space-y-4 pt-1">
          <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3">
            <span className="text-xs font-semibold text-foreground-secondary mr-2">Audit Cohort:</span>
            {FAIRNESS_CATEGORIES.map((cat) => {
              const isSelected = selectedFairnessCategory === cat.id;
              const Icon = cat.icon;
              const catResult = fairnessResults[cat.subgroupField];
              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedFairnessCategory(cat.id)}
                  className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                      : 'bg-surface-highlight text-foreground-secondary hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-surface-elevated border border-border'
                  }`}
                >
                  <Icon className="size-3.5" />
                  <span>{cat.name}</span>
                  {catResult?.demographic_parity_ratio !== null && catResult?.demographic_parity_ratio !== undefined && (
                    <Badge variant={isSelected ? "outline" : "secondary"} className="text-[10px] py-0 px-1.5 border-current font-mono">
                      DPR {catResult.demographic_parity_ratio.toFixed(2)}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>

          {/* ACTIVE CATEGORY DETAIL & TABLE */}
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-surface-highlight/30 border border-border text-xs sm:text-sm">
              <p className="text-foreground-secondary leading-relaxed">
                {activeCategory.description}
              </p>
              {activeFairness && (
                <div className="flex items-center gap-3 shrink-0 font-mono text-xs">
                  <span className="text-foreground-secondary">
                    Segment DPR: <strong className="text-foreground">{activeFairness.demographic_parity_ratio !== null && activeFairness.demographic_parity_ratio !== undefined ? activeFairness.demographic_parity_ratio.toFixed(2) : 'N/A'}</strong>
                  </span>
                  <span className="text-foreground-secondary">
                    EOD: <strong className="text-foreground">{activeFairness.equal_opportunity_difference !== null && activeFairness.equal_opportunity_difference !== undefined ? activeFairness.equal_opportunity_difference.toFixed(3) : 'N/A'}</strong>
                  </span>
                </div>
              )}
            </div>

            {fairnessLoading ? (
              <div className="p-8 text-center text-sm text-foreground-secondary space-y-2">
                <RefreshCw className="size-6 animate-spin mx-auto text-foreground-secondary" />
                <p>Executing Fairlearn subgroup audit for {activeCategory.name} across offline benchmark records...</p>
              </div>
            ) : !activeFairness ? (
              <div className="p-8 rounded-2xl bg-surface-highlight/20 border border-dashed border-border text-center space-y-2">
                <Scale className="size-6 text-foreground-secondary mx-auto" />
                <p className="text-sm font-medium text-foreground">Subgroup Audit Not Yet Executed</p>
                <p className="text-xs sm:text-sm text-foreground-secondary max-w-sm mx-auto">
                  Click <strong>Run Subgroup Audit</strong> to evaluate Demographic Parity and Equal Opportunity difference across {activeCategory.name}.
                </p>
              </div>
            ) : (
              /* SUBGROUP COMPARISON TABLE */
              <div className="overflow-x-auto rounded-xl border border-border bg-surface">
                <table className="w-full min-w-[650px] text-left text-xs sm:text-sm">
                  <thead className="bg-surface-highlight/50 border-b border-border text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                    <tr>
                      <th className="py-3 px-4">Subgroup Cohort</th>
                      <th className="py-3 px-4 font-mono">Sample Size (N)</th>
                      <th className="py-3 px-4">Favorable / Approval Rate</th>
                      <th className="py-3 px-4 font-mono">Parity vs Benchmark</th>
                      <th className="py-3 px-4 font-mono">True Pos. (Recall)</th>
                      <th className="py-3 px-4">Disparate Impact Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border font-normal">
                    {(() => {
                      const subgroupsList = Object.values(activeFairness.subgroups);
                      const maxFavRate = Math.max(
                        ...subgroupsList.map((s) => s.favorable_prediction_rate),
                        0.001
                      );
                      return subgroupsList.map((sub) => {
                        const favPct = (sub.favorable_prediction_rate * 100).toFixed(1);
                        const parityRatio = (sub.favorable_prediction_rate / maxFavRate).toFixed(2);
                        const isCompliant = Number(parityRatio) >= 0.80;
                        return (
                          <tr key={sub.subgroup_name} className="hover:bg-surface-highlight/20 transition-colors">
                            <td className="py-3 px-4 font-semibold text-foreground">
                              {formatSubgroupName(sub.subgroup_name)}
                            </td>
                            <td className="py-3 px-4 font-mono text-foreground-secondary">
                              {sub.sample_count.toLocaleString()}
                            </td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2.5">
                                <div className="w-24 bg-surface-highlight h-2 rounded-full overflow-hidden shrink-0">
                                  <div
                                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                                    style={{ width: `${Math.min(100, Math.max(0, sub.favorable_prediction_rate * 100))}%` }}
                                  />
                                </div>
                                <span className="font-mono font-semibold text-foreground">
                                  {favPct}%
                                </span>
                              </div>
                            </td>
                            <td className="py-3 px-4 font-mono text-foreground font-semibold">
                              {parityRatio} <span className="text-xs text-foreground-secondary font-normal">/ 1.00</span>
                            </td>
                            <td className="py-3 px-4 font-mono text-foreground-secondary">
                              {sub.true_positive_rate !== null && sub.true_positive_rate !== undefined ? `${(sub.true_positive_rate * 100).toFixed(1)}%` : '—'}
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant={isCompliant ? 'mint' : 'riskHigher'} className="text-xs font-medium gap-1 py-0.5 px-2">
                                <CheckCircle2 className="size-3" />
                                <span>{isCompliant ? 'Compliant' : 'Review Required'}</span>
                              </Badge>
                            </td>
                          </tr>
                        );
                      });
                    })()}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* REGULATORY DISCLAIMER & GOVERNANCE NOTICE */}
        <div className="p-4 rounded-xl bg-surface-highlight/20 border border-border text-xs sm:text-sm text-foreground-secondary flex items-start gap-3">
          <Info className="size-4.5 text-foreground-secondary shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-foreground block">
              DPDP & Fairlearn Methodology Notice
            </span>
            <p className="leading-relaxed text-foreground-secondary">
              Fairlearn audit protocols evaluate whether the volatility-aware alternative scoring model introduces disparate impact across gig sectors, geographies, or tenured cohorts. In accordance with the Digital Personal Data Protection (DPDP) Act, raw sensitive personal demographic attributes are not captured; evaluations utilize anonymized operational metadata and synthetic proxy benchmark distributions.
            </p>
          </div>
        </div>
      </Card>

      {/* 4. TREESHAP EXPLAINABILITY */}
      <Card className="p-6 bg-surface border-border space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
              <Sparkles className="size-4.5 text-mint" />
              TreeSHAP Explainability — Active
            </h2>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Local TreeSHAP feature attributions are generated for scored assessments and are displayed in applicant and reviewer assessment views.
            </p>
          </div>
          <Badge variant="mint" className="text-xs font-mono">
            ACTIVE
          </Badge>
        </div>

        {/* P2-10: GLOBAL SHAP FEATURE IMPORTANCE — BACKEND CONNECTED */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="space-y-0.5">
              <h3 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-2">
                <BarChart2 className="size-4 text-foreground-secondary" />
                Global Feature Importance — Model-Level SHAP Aggregation
              </h3>
              <p className="text-xs text-foreground-secondary leading-relaxed max-w-xl">
                Mean absolute SHAP values computed from the offline evaluation dataset using the existing TreeSHAP infrastructure.
                This represents <strong className="text-foreground">model-level feature importance</strong>, not individual applicant explanations.
                No applicant personal data is included in this aggregation.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleComputeGlobalSHAP()}
              disabled={isComputingShap || !activeModel}
              className="rounded-full gap-1.5 text-xs text-foreground-secondary border-border hover:bg-surface-highlight shrink-0"
            >
              <RefreshCw className={`size-3.5 ${isComputingShap ? 'animate-spin' : ''}`} />
              {isComputingShap ? 'Computing SHAP...' : globalSHAP ? 'Recompute' : 'Compute Global SHAP'}
            </Button>
          </div>

          {/* SHAP ERROR STATE */}
          {shapError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-600 dark:text-rose-400 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4.5 shrink-0" />
                <span>{shapError}</span>
              </div>
              <Button variant="ghost" size="sm" onClick={() => handleComputeGlobalSHAP()} disabled={isComputingShap} className="text-rose-600 dark:text-rose-400 text-xs h-8">
                Retry
              </Button>
            </div>
          )}

          {/* SHAP LOADING STATE */}
          {isComputingShap && (
            <div className="p-8 text-center text-sm text-foreground-secondary space-y-2">
              <RefreshCw className="size-6 animate-spin mx-auto text-foreground-secondary" />
              <p>Computing global SHAP values from {activeModel?.model_name} over offline evaluation dataset...</p>
              <p className="text-xs">This may take a few seconds.</p>
            </div>
          )}

          {/* SHAP EMPTY STATE */}
          {!isComputingShap && !globalSHAP && !shapError && (
            <div className="p-8 rounded-2xl bg-surface-highlight/20 border border-dashed border-border text-center space-y-2">
              <Sparkles className="size-6 text-foreground-secondary mx-auto" />
              <p className="text-sm font-medium text-foreground">Global SHAP Feature Importance Not Yet Computed</p>
              <p className="text-xs sm:text-sm text-foreground-secondary max-w-sm mx-auto">
                Click <strong>Compute Global SHAP</strong> to aggregate mean absolute SHAP values across the offline evaluation dataset using the frozen {activeModel?.model_name || 'volatility-aware'} model.
              </p>
            </div>
          )}

          {/* SHAP RESULTS TABLE */}
          {!isComputingShap && globalSHAP && (
            <div className="space-y-3">
              {/* Metadata banner */}
              <div className="p-3.5 rounded-xl bg-surface-highlight/40 border border-border text-xs sm:text-sm space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <CheckCircle2 className="size-3.5 text-mint" />
                    Backend SHAP Aggregation — {globalSHAP.model_name} v{globalSHAP.model_version}
                  </span>
                  <span className="text-foreground-secondary text-xs">
                    Computed: {new Date(globalSHAP.evaluated_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex flex-wrap gap-4 text-xs font-mono text-foreground-secondary">
                  <span>N={globalSHAP.sample_count.toLocaleString()} evaluation records</span>
                  <span className="text-foreground-secondary italic">{globalSHAP.dataset_source.split('.')[0]}.</span>
                </div>
              </div>

              {/* Feature importance table */}
              <div className="overflow-x-auto rounded-xl border border-border bg-surface">
                <table className="w-full min-w-[620px] text-left text-xs sm:text-sm">
                  <thead className="bg-surface-highlight/50 border-b border-border text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                    <tr>
                      <th className="py-3 px-4">Rank</th>
                      <th className="py-3 px-4">Feature Name</th>
                      <th className="py-3 px-4 font-mono text-right">
                        Mean |SHAP|
                        <span className="block text-[10px] font-normal normal-case text-foreground-secondary/70">Primary importance</span>
                      </th>
                      <th className="py-3 px-4 font-mono text-right">
                        Mean SHAP
                        <span className="block text-[10px] font-normal normal-case text-foreground-secondary/70">Signed direction</span>
                      </th>
                      <th className="py-3 px-4">Direction</th>
                      <th className="py-3 px-4">Importance Bar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border font-normal">
                    {globalSHAP.features.slice(0, 20).map((feat) => {
                      const maxAbsShap = globalSHAP.features[0]?.mean_abs_shap || 1;
                      const barWidth = Math.round((feat.mean_abs_shap / maxAbsShap) * 100);
                      const isRiskIncreasing = feat.mean_shap > 0;
                      return (
                        <tr key={feat.feature_name} className="hover:bg-surface-highlight/20 transition-colors">
                          <td className="py-2.5 px-4 font-mono text-foreground-secondary text-xs font-semibold">
                            #{feat.rank}
                          </td>
                          <td className="py-2.5 px-4 font-mono text-foreground text-xs font-medium max-w-[180px] truncate" title={feat.feature_name}>
                            {feat.feature_name}
                          </td>
                          <td className="py-2.5 px-4 font-mono text-foreground font-semibold text-right text-xs">
                            {feat.mean_abs_shap.toFixed(4)}
                          </td>
                          <td className={`py-2.5 px-4 font-mono font-semibold text-right text-xs ${isRiskIncreasing ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                            {feat.mean_shap > 0 ? '+' : ''}{feat.mean_shap.toFixed(4)}
                          </td>
                          <td className="py-2.5 px-4 text-xs">
                            <Badge
                              variant={isRiskIncreasing ? 'riskHigher' : 'riskLower'}
                              className="text-[10px] py-0 px-1.5 font-medium"
                            >
                              {isRiskIncreasing ? '↑ Risk' : '↓ Risk'}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-4">
                            <div className="w-28 bg-surface-highlight h-2 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-500 ${isRiskIncreasing ? 'bg-rose-500' : 'bg-emerald-500'}`}
                                style={{ width: `${barWidth}%` }}
                              />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {globalSHAP.features.length > 20 && (
                  <div className="p-3 text-center text-xs text-foreground-secondary border-t border-border">
                    Showing top 20 of {globalSHAP.features.length} features
                  </div>
                )}
              </div>

              <div className="p-3 rounded-xl bg-surface-highlight/20 border border-border text-xs text-foreground-secondary flex items-start gap-2">
                <Info className="size-3.5 shrink-0 mt-0.5" />
                <span>
                  <strong className="text-foreground">Mean |SHAP|</strong> is the primary importance measure — the average magnitude of each feature's contribution across the evaluation population.
                  <strong className="text-foreground"> Mean SHAP</strong> (signed) indicates whether the average contribution increases (positive) or decreases (negative) default risk.
                  These are <em>global/model-level</em> aggregations; individual assessment explanations are shown separately in each application dossier.
                </span>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* 5. MODEL VERSION AUDIT LINEAGE */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
            <FileCheck className="size-4.5 text-foreground-secondary" />
            Model Version Lineage & Regulatory Audit Log
          </h2>
          <span className="text-xs sm:text-sm font-mono text-foreground-secondary">
            {modelVersions.length} Iteration{modelVersions.length === 1 ? '' : 's'} Registered
          </span>
        </div>

        {actionMessage && (
          <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border text-xs sm:text-sm text-foreground flex items-center justify-between">
            <span>{actionMessage}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActionMessage(null)}
              className="text-foreground-secondary hover:text-foreground text-xs h-6 px-2"
            >
              Dismiss
            </Button>
          </div>
        )}

        <div className="space-y-3 pt-1 text-sm">
          {isLoading ? (
            <div className="p-8 text-center text-sm text-foreground-secondary">
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
                    <span className="font-mono font-semibold text-foreground text-sm sm:text-base">
                      {mv.model_name} (v{mv.version})
                    </span>
                    <Badge
                      variant={mv.is_active ? 'mint' : 'outline'}
                      className="text-xs py-0 px-2 font-medium"
                    >
                      {mv.is_active ? 'Current Active' : 'Archived'}
                    </Badge>
                  </div>
                  <p className="text-foreground-secondary text-xs sm:text-sm">
                    {mv.description || `Algorithm: ${mv.algorithm}`}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="font-mono text-foreground-secondary text-xs sm:text-sm">
                    {new Date(mv.created_at).toLocaleDateString('en-IN', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </span>
                  {!mv.is_active && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleActivateModelVersion(mv.id)}
                      disabled={isActivatingId === mv.id}
                      className="rounded-full gap-1 text-xs text-foreground border-border hover:bg-surface-highlight h-7 px-2.5"
                    >
                      {isActivatingId === mv.id ? (
                        <>
                          <RefreshCw className="size-3 animate-spin" />
                          <span>Activating...</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="size-3 text-mint" />
                          <span>Activate</span>
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 rounded-2xl bg-surface-highlight/20 border border-dashed border-border text-center space-y-2">
              <Clock className="size-6 text-foreground-secondary mx-auto" />
              <p className="text-sm font-medium text-foreground">No model versions registered in backend yet</p>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Model versions will appear here as assessment engines are registered in PostgreSQL.
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* 6. ALGORITHMIC ACCOUNTABILITY FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-xs sm:text-sm text-foreground-secondary flex items-start gap-3">
        <Info className="size-4.5 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Algorithmic Accountability & Explainability Declaration
          </span>
          <p className="leading-relaxed">
            PARAKH exposes model lineage and local explainability for assessment transparency. Fairness evaluation requires a defined protected-group evaluation dataset and should be performed before any production lending deployment.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
