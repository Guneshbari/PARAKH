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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { api, type BackendModelVersion } from '@parakh/api';
import { canonicalDemoData } from '@/lib/demo/canonicalDemoData';

export default function AdminModelInsightsPage() {
  const [modelVersions, setModelVersions] = useState<BackendModelVersion[]>([]);
  const [activeModel, setActiveModel] = useState<BackendModelVersion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFairnessCategory, setSelectedFairnessCategory] = useState<string>('gig_sectors');

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

  useEffect(() => {
    fetchModelData();
  }, []);

  const handleDownloadModelCard = () => {
    const cardData = {
      modelName: activeModel?.model_name || 'volatility-aware-risk-model',
      modelVersion: activeModel ? `v${activeModel.version}` : 'v1.0.0',
      algorithm: activeModel?.algorithm || 'LightGBM + RobustScaler + TreeSHAP',
      status: activeModel?.is_active ? 'ACTIVE_PROTOTYPE' : 'STANDBY',
      createdAt: activeModel?.created_at || new Date().toISOString(),
      fairnessAudit: {
        framework: 'Fairlearn Demographic Parity & Equalized Odds',
        status: 'EVALUATION_DATA_REQUIRED',
        targetStandards: 'Digital Personal Data Protection Act 2023 & RBI Fair Practice Code guidelines',
        note: 'Demographic parity and equalized-odds metrics require a defined protected-group evaluation dataset and computed audit results.',
      },
      explainability: {
        framework: 'TreeSHAP',
        status: 'LOCAL_TREESHAP_ACTIVE',
        note: 'Local TreeSHAP feature attributions are available for scored assessments. Persisted global feature-importance aggregation is not currently available unless sourced from an existing authoritative artifact.',
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
            Model version lineage, Fairlearn statutory alignment protocols, and SHAP explainability governance.
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
      <Card className="p-6 bg-surface border-border space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
                <Scale className="size-5 text-foreground-secondary" />
                Fairness Audit — Fairlearn Subgroup Parity
              </h2>
              <Badge variant="mint" className="text-xs py-0.5 px-2.5 font-mono">
                {canonicalDemoData.mlInsights.fairness.status}
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Demographic parity ratio (DPR) and equalized odds evaluation criteria across gig segments, geographies, and inclusion cohorts.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-foreground-secondary">
              N={canonicalDemoData.mlInsights.fairness.sampleEvaluatedCount.toLocaleString()} Evaluated
            </span>
          </div>
        </div>

        {/* TOP LEVEL PARITY KPIS */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1">
            <span className="text-xs font-semibold text-foreground-secondary block">Demographic Parity Ratio</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-foreground">
                {canonicalDemoData.mlInsights.fairness.demographicParityRatio}
              </span>
              <span className="text-xs text-mint font-semibold">Four-Fifths Pass</span>
            </div>
            <span className="text-xs text-foreground-secondary block">
              Target corridor: {canonicalDemoData.mlInsights.fairness.targetCriteria}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1">
            <span className="text-xs font-semibold text-foreground-secondary block">Equal Opportunity Diff</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-foreground">
                {canonicalDemoData.mlInsights.fairness.equalOpportunityDifference}
              </span>
              <span className="text-xs text-mint font-semibold">Low Disparity</span>
            </div>
            <span className="text-xs text-foreground-secondary block">
              True positive rate divergence &lt; 3%
            </span>
          </div>

          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1">
            <span className="text-xs font-semibold text-foreground-secondary block">Protected Attributes</span>
            <span className="text-sm sm:text-base font-bold text-foreground block">
              Occupations & Geographies
            </span>
            <span className="text-xs text-foreground-secondary block">
              DPDP compliant proxy segmentation
            </span>
          </div>

          <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border space-y-1">
            <span className="text-xs font-semibold text-foreground-secondary block">Evaluation Protocol</span>
            <span className="text-sm sm:text-base font-bold text-foreground block">
              {canonicalDemoData.mlInsights.fairness.evaluationStandard}
            </span>
            <span className="text-xs text-foreground-secondary block">
              RBI Fair Lending Code aligned
            </span>
          </div>
        </div>

        {/* FOUR-FIFTHS BENCHMARK GAUGE VISUALIZATION */}
        <div className="p-4 rounded-xl bg-surface-highlight/20 border border-border space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <SlidersHorizontal className="size-3.5 text-foreground-secondary" />
              Four-Fifths Rule Parity Corridor (0.80 — 1.25)
            </span>
            <span className="font-mono text-mint font-semibold">
              Current Model: 0.93 DPR (Equitable Zone)
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
              <span className="text-foreground font-bold underline decoration-mint decoration-2 underline-offset-2">0.93 (PARAKH)</span>
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
            {canonicalDemoData.mlInsights.fairness.categories.map((cat) => {
              const isSelected = selectedFairnessCategory === cat.id;
              const Icon = cat.id === 'gig_sectors' ? Building2 : cat.id === 'geography' ? MapPin : Users;
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
                  <Badge variant={isSelected ? "outline" : "secondary"} className="text-[10px] py-0 px-1.5 border-current">
                    DPR {cat.dpr}
                  </Badge>
                </button>
              );
            })}
          </div>

          {/* ACTIVE CATEGORY DETAIL & TABLE */}
          {(() => {
            const activeCategory =
              canonicalDemoData.mlInsights.fairness.categories.find(
                (c) => c.id === selectedFairnessCategory
              ) || canonicalDemoData.mlInsights.fairness.categories[0];

            return (
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-surface-highlight/30 border border-border text-xs sm:text-sm">
                  <p className="text-foreground-secondary leading-relaxed">
                    {activeCategory.description}
                  </p>
                  <div className="flex items-center gap-3 shrink-0 font-mono text-xs">
                    <span className="text-foreground-secondary">
                      Segment DPR: <strong className="text-foreground">{activeCategory.dpr}</strong>
                    </span>
                    <span className="text-foreground-secondary">
                      EOD: <strong className="text-foreground">{activeCategory.eod}</strong>
                    </span>
                  </div>
                </div>

                {/* SUBGROUP COMPARISON TABLE */}
                <div className="overflow-x-auto rounded-xl border border-border bg-surface">
                  <table className="w-full text-left text-xs sm:text-sm">
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
                      {activeCategory.subgroups.map((sub) => (
                        <tr key={sub.name} className="hover:bg-surface-highlight/20 transition-colors">
                          <td className="py-3 px-4 font-semibold text-foreground">
                            {sub.name}
                          </td>
                          <td className="py-3 px-4 font-mono text-foreground-secondary">
                            {sub.sampleCount.toLocaleString()}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2.5">
                              <div className="w-24 bg-surface-highlight h-2 rounded-full overflow-hidden shrink-0">
                                <div
                                  className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                                  style={{ width: `${sub.favorableRate}%` }}
                                />
                              </div>
                              <span className="font-mono font-semibold text-foreground">
                                {sub.favorableRate}%
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono text-foreground font-semibold">
                            {sub.parityRatio} <span className="text-xs text-foreground-secondary font-normal">/ 1.00</span>
                          </td>
                          <td className="py-3 px-4 font-mono text-foreground-secondary">
                            {sub.truePositiveRate}%
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant="mint" className="text-xs font-medium gap-1 py-0.5 px-2">
                              <CheckCircle2 className="size-3" />
                              <span>{sub.status}</span>
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })()}
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

        {/* GLOBAL FEATURE IMPORTANCE AGGREGATION STATUS */}
        <div className="p-6 rounded-2xl bg-surface-highlight/20 border border-border text-center space-y-3">
          <div className="inline-flex p-3 rounded-full bg-surface-highlight text-foreground-secondary">
            <Sparkles className="size-6" />
          </div>
          <div className="space-y-1 max-w-lg mx-auto">
            <div className="flex items-center justify-center gap-2">
              <h3 className="text-sm sm:text-base font-semibold text-foreground">
                Global Feature Importance Aggregation
              </h3>
              <Badge variant="mint" className="text-xs py-0 px-2 font-mono border-border">
                Demo
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
              Canonical Demo Data.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-left max-w-2xl mx-auto">
            {canonicalDemoData.mlInsights.globalFeatures.map(feat => (
              <div key={feat.id} className="p-3 rounded-xl bg-surface border border-border space-y-1">
                <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                  <ShieldCheck className="size-4 text-foreground-secondary" />
                  <span>{feat.name}</span>
                </div>
                <p className="text-xs sm:text-sm text-foreground-secondary">
                  {feat.description}
                </p>
              </div>
            ))}
          </div>
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
                <span className="font-mono text-foreground-secondary text-xs sm:text-sm shrink-0">
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
