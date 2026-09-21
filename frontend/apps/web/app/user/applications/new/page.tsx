'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  User,
  Activity,
  CreditCard,
  FileCheck2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { ApplicationFormSchema, type ApplicationFormData } from '@parakh/validation';

const STEPS = [
  { id: 1, label: 'Personal', icon: User },
  { id: 2, label: 'Work Profile', icon: Briefcase },
  { id: 3, label: 'Cashflow Rhythm', icon: Activity },
  { id: 4, label: 'Obligations', icon: CreditCard },
  { id: 5, label: 'Consent & Review', icon: FileCheck2 },
];

export default function NewApplicationPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionPhase, setSubmissionPhase] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Form State initialized with realistic defaults for a smooth test run
  const [formData, setFormData] = useState<ApplicationFormData>({
    fullName: 'Arjun Verma',
    phone: '9845128910',
    city: 'Bengaluru',
    employmentType: 'GIG_WORKER',
    primaryPlatform: 'Swiggy & Urban Company',
    tenureMonths: 18,
    incomeFrequency: 'weekly',
    averageMonthlyIncome: 52000,
    lowestMonthIncome: 34000,
    typicalRecoveryDays: 10,
    monthlyRent: 8000,
    utilityExpenses: 3200,
    existingEmiObligations: 2500,
    requestedAmount: 35000,
    purpose: 'Two-Wheeler EV Battery Upgrade & Gear',
    consentGiven: true,
  });

  const updateField = <K extends keyof ApplicationFormData>(
    field: K,
    value: ApplicationFormData[K]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const validateCurrentStep = (): boolean => {
    const stepErrors: Record<string, string> = {};

    if (currentStep === 1) {
      if (!formData.fullName || formData.fullName.length < 3) {
        stepErrors.fullName = 'Full name must be at least 3 characters';
      }
      if (!formData.phone || !/^[6-9]\d{9}$/.test(formData.phone)) {
        stepErrors.phone = 'Valid 10-digit Indian phone number required';
      }
      if (!formData.city) {
        stepErrors.city = 'City is required';
      }
    } else if (currentStep === 2) {
      if (!formData.primaryPlatform) {
        stepErrors.primaryPlatform = 'Primary platform is required';
      }
      if (!formData.tenureMonths || formData.tenureMonths < 1) {
        stepErrors.tenureMonths = 'Minimum tenure is 1 month';
      }
    } else if (currentStep === 3) {
      if (formData.averageMonthlyIncome < 5000) {
        stepErrors.averageMonthlyIncome = 'Minimum average income is ₹5,000';
      }
      if (formData.lowestMonthIncome < 0) {
        stepErrors.lowestMonthIncome = 'Lowest month income cannot be negative';
      }
      if (formData.typicalRecoveryDays < 1 || formData.typicalRecoveryDays > 60) {
        stepErrors.typicalRecoveryDays = 'Recovery window must be between 1 and 60 days';
      }
    } else if (currentStep === 4) {
      if (formData.monthlyRent < 0) stepErrors.monthlyRent = 'Cannot be negative';
      if (formData.utilityExpenses < 0) stepErrors.utilityExpenses = 'Cannot be negative';
      if (formData.existingEmiObligations < 0) stepErrors.existingEmiObligations = 'Cannot be negative';
    } else if (currentStep === 5) {
      if (formData.requestedAmount < 5000) {
        stepErrors.requestedAmount = 'Minimum requested amount is ₹5,000';
      }
      if (!formData.purpose || formData.purpose.length < 3) {
        stepErrors.purpose = 'Please describe the intended purpose';
      }
      if (!formData.consentGiven) {
        stepErrors.consentGiven = 'Consent is required to run alternative assessment';
      }
    }

    setErrors(stepErrors);
    return Object.keys(stepErrors).length === 0;
  };

  const handleNext = () => {
    if (validateCurrentStep()) {
      if (currentStep < 5) {
        setCurrentStep((prev) => prev + 1);
      } else {
        handleSubmit();
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleSubmit = async () => {
    const result = ApplicationFormSchema.safeParse(formData);
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      result.error.issues.forEach((issue) => {
        if (issue.path[0]) {
          fieldErrors[issue.path[0] as string] = issue.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    setIsSubmitting(true);
    setSubmissionPhase('Ingesting alternative platform & UPI telemetry...');
    await new Promise((r) => setTimeout(r, 900));

    setSubmissionPhase('Calculating Volatility Index & Shock Recovery velocity...');
    await new Promise((r) => setTimeout(r, 900));

    setSubmissionPhase('Synthesizing explainable SHAP feature contributions...');
    await new Promise((r) => setTimeout(r, 900));

    // Route to generated assessment report
    router.push('/user/results/demo');
  };

  if (isSubmitting) {
    return (
      <PageTransition className="max-w-xl mx-auto py-24 px-4 text-center space-y-6">
        <div className="size-16 rounded-2xl bg-teal-400/10 border border-teal-400/30 flex items-center justify-center mx-auto text-teal-300 animate-pulse shadow-xl shadow-teal-500/10">
          <Sparkles className="size-8" />
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl font-extrabold text-white tracking-tight">
            Synthesizing PARAKH Assessment
          </h2>
          <p className="text-sm text-teal-300 font-mono animate-pulse">
            {submissionPhase}
          </p>
        </div>

        <div className="h-1.5 w-full bg-white/[0.05] rounded-full overflow-hidden max-w-sm mx-auto">
          <div className="h-full bg-gradient-to-r from-teal-400 to-purple-400 rounded-full animate-pulse w-3/4" />
        </div>

        <p className="text-xs text-muted-foreground pt-4">
          Normalizing gig earning volatility • Verifying 10-day recovery dynamics
        </p>
      </PageTransition>
    );
  }

  return (
    <PageTransition className="max-w-3xl mx-auto space-y-8 pb-12">
      {/* 1. EDITORIAL HEADER */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Badge variant="lavender" className="text-xs">
            <Sparkles className="size-3" />
            <span>Guided Assessment Flow</span>
          </Badge>
          <span className="text-xs font-mono font-bold text-muted-foreground">
            Step {currentStep} of 5
          </span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Alternative Credit Evaluation Intake
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
          PARAKH doesn&apos;t require traditional credit bureau history. Share your verified platform and cashflow rhythm
          to generate an explainable, volatility-aware assessment.
        </p>
      </div>

      {/* 2. PROGRESS STEPPER WITH NUMBERED INDICATORS */}
      <div className="grid grid-cols-5 gap-2 pt-2">
        {STEPS.map((s) => {
          const isActive = s.id === currentStep;
          const isCompleted = s.id < currentStep;

          return (
            <div
              key={s.id}
              onClick={() => s.id < currentStep && setCurrentStep(s.id)}
              className={`flex flex-col items-center gap-1.5 p-2 rounded-2xl border transition-all cursor-pointer ${
                isActive
                  ? 'bg-white/[0.06] border-teal-400/50 text-white'
                  : isCompleted
                  ? 'bg-teal-500/10 border-teal-500/20 text-teal-300'
                  : 'bg-white/[0.02] border-white/[0.05] text-muted-foreground'
              }`}
            >
              <div
                className={`size-6 rounded-full flex items-center justify-center font-bold text-xs ${
                  isCompleted
                    ? 'bg-teal-400 text-slate-950'
                    : isActive
                    ? 'bg-teal-400/20 text-teal-300 border border-teal-400'
                    : 'bg-white/[0.05] text-muted-foreground'
                }`}
              >
                {isCompleted ? '✓' : s.id}
              </div>
              <span className="text-[10px] font-semibold text-center hidden sm:inline truncate w-full">
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* 3. STEP CONTENT CARDS */}
      <Card className="p-7 sm:p-9 space-y-6 bg-[#0A162E] border-white/[0.08]">
        {/* STEP 1: PERSONAL INFORMATION */}
        {currentStep === 1 && (
          <div className="space-y-5">
            <div className="space-y-1 pb-2 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-teal-400/20 text-teal-300 flex items-center justify-center text-xs font-bold">
                  1
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Personal Information
                </h2>
              </div>
              <p className="text-xs text-muted-foreground">
                Your verified contact credentials used to aggregate alternative financial feeds.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Full Legal Name
                </label>
                <Input
                  value={formData.fullName}
                  onChange={(e) => updateField('fullName', e.target.value)}
                  placeholder="e.g. Arjun Verma"
                />
                {errors.fullName && (
                  <span className="text-xs text-red-400 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {errors.fullName}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Mobile Number (UPI Linked)
                  </label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => updateField('phone', e.target.value)}
                    placeholder="9845128910"
                    maxLength={10}
                  />
                  {errors.phone && (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.phone}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Operating City
                  </label>
                  <Input
                    value={formData.city}
                    onChange={(e) => updateField('city', e.target.value)}
                    placeholder="e.g. Bengaluru, Mumbai, Delhi"
                  />
                  {errors.city && (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.city}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: WORK PROFILE */}
        {currentStep === 2 && (
          <div className="space-y-5">
            <div className="space-y-1 pb-2 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-teal-400/20 text-teal-300 flex items-center justify-center text-xs font-bold">
                  2
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Work & Platform Profile
                </h2>
              </div>
              <p className="text-xs text-muted-foreground">
                We reward verified platform tenure rather than demanding traditional salary slips.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Work Category
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'GIG_WORKER', label: 'Gig / Delivery' },
                    { id: 'INFORMAL_VENDOR', label: 'Local Vendor / Shop' },
                    { id: 'FREELANCER', label: 'Freelancer' },
                    { id: 'DAILY_WAGE', label: 'Daily Wage' },
                  ].map((cat) => (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => updateField('employmentType', cat.id as ApplicationFormData['employmentType'])}
                      className={`p-3 rounded-2xl border text-xs font-semibold text-center transition-all cursor-pointer ${
                        formData.employmentType === cat.id
                          ? 'bg-teal-400/15 border-teal-400 text-teal-300 shadow-sm'
                          : 'bg-white/[0.03] border-white/[0.06] text-muted-foreground hover:text-white'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Primary Platforms / Trade
                  </label>
                  <Input
                    value={formData.primaryPlatform}
                    onChange={(e) => updateField('primaryPlatform', e.target.value)}
                    placeholder="e.g. Swiggy, Zomato, Urban Company, Kirana"
                  />
                  {errors.primaryPlatform && (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.primaryPlatform}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Active Duration (Months)
                  </label>
                  <Input
                    type="number"
                    value={formData.tenureMonths || ''}
                    onChange={(e) => updateField('tenureMonths', parseInt(e.target.value) || 0)}
                    placeholder="e.g. 18"
                  />
                  {errors.tenureMonths && (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.tenureMonths}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: INCOME BEHAVIOR & VOLATILITY DYNAMICS */}
        {currentStep === 3 && (
          <div className="space-y-5">
            <div className="space-y-1 pb-2 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-teal-400/20 text-teal-300 flex items-center justify-center text-xs font-bold">
                  3
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Income Inflow & Volatility Rhythm
                </h2>
              </div>
              <p className="text-xs text-muted-foreground">
                Crucial for PARAKH&apos;s volatility-aware engine. We model your natural dips alongside your rebound speed.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Inflow Settlement Frequency
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { id: 'daily', label: 'Daily' },
                    { id: 'weekly', label: 'Weekly' },
                    { id: 'irregular', label: 'Irregular' },
                    { id: 'monthly', label: 'Monthly' },
                  ].map((freq) => (
                    <button
                      key={freq.id}
                      type="button"
                      onClick={() => updateField('incomeFrequency', freq.id as ApplicationFormData['incomeFrequency'])}
                      className={`p-2.5 rounded-2xl border text-xs font-semibold text-center transition-all cursor-pointer ${
                        formData.incomeFrequency === freq.id
                          ? 'bg-teal-400/15 border-teal-400 text-teal-300'
                          : 'bg-white/[0.03] border-white/[0.06] text-muted-foreground hover:text-white'
                      }`}
                    >
                      {freq.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Average Monthly Inflow (₹)
                  </label>
                  <Input
                    type="number"
                    value={formData.averageMonthlyIncome || ''}
                    onChange={(e) => updateField('averageMonthlyIncome', parseInt(e.target.value) || 0)}
                    placeholder="e.g. 52000"
                  />
                  {errors.averageMonthlyIncome && (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.averageMonthlyIncome}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Lowest Month Inflow (₹)
                  </label>
                  <Input
                    type="number"
                    value={formData.lowestMonthIncome || ''}
                    onChange={(e) => updateField('lowestMonthIncome', parseInt(e.target.value) || 0)}
                    placeholder="e.g. 34000 (rainy season/downtime)"
                  />
                  {errors.lowestMonthIncome && (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.lowestMonthIncome}
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
                  <span>Typical Days to Rebound to Normal Earnings</span>
                  <span className="text-teal-300 font-mono font-bold">
                    {formData.typicalRecoveryDays} Days
                  </span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={formData.typicalRecoveryDays}
                  onChange={(e) => updateField('typicalRecoveryDays', parseInt(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>1 day (Rapid rebound)</span>
                  <span>14 days (Standard gig cycle)</span>
                  <span>30 days (Extended)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: EXISTING OBLIGATIONS */}
        {currentStep === 4 && (
          <div className="space-y-5">
            <div className="space-y-1 pb-2 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-teal-400/20 text-teal-300 flex items-center justify-center text-xs font-bold">
                  4
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Existing Obligations & Bill Punctuality
                </h2>
              </div>
              <p className="text-xs text-muted-foreground">
                We assess your disposable margin after mandatory living expenses and utility bills.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Monthly Rent (₹)
                </label>
                <Input
                  type="number"
                  value={formData.monthlyRent || ''}
                  onChange={(e) => updateField('monthlyRent', parseInt(e.target.value) || 0)}
                  placeholder="e.g. 8000"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Utility Bills (₹)
                </label>
                <Input
                  type="number"
                  value={formData.utilityExpenses || ''}
                  onChange={(e) => updateField('utilityExpenses', parseInt(e.target.value) || 0)}
                  placeholder="Electricity, LPG, Mobile (e.g. 3200)"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Existing EMIs (₹)
                </label>
                <Input
                  type="number"
                  value={formData.existingEmiObligations || ''}
                  onChange={(e) => updateField('existingEmiObligations', parseInt(e.target.value) || 0)}
                  placeholder="e.g. 2500"
                />
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-teal-500/10 border border-teal-500/20 flex items-start gap-3">
              <CheckCircle2 className="size-4 text-teal-300 shrink-0 mt-0.5" />
              <p className="text-xs text-teal-200/90 leading-relaxed">
                <strong className="text-white">Punctuality Bonus:</strong> Verified on-time payment of electricity, gas cylinders, and mobile recharges serves as primary positive credit proof in our alternative model.
              </p>
            </div>
          </div>
        )}

        {/* STEP 5: REVIEW, PURPOSE & CONSENT */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div className="space-y-1 pb-2 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-teal-400/20 text-teal-300 flex items-center justify-center text-xs font-bold">
                  5
                </span>
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Assessment Purpose & Applicant Consent
                </h2>
              </div>
              <p className="text-xs text-muted-foreground">
                State your intended use of funds and provide voluntary authorization for alternative evaluation.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Evaluation Amount Benchmark (₹)
                </label>
                <Input
                  type="number"
                  value={formData.requestedAmount || ''}
                  onChange={(e) => updateField('requestedAmount', parseInt(e.target.value) || 0)}
                  placeholder="e.g. 35000"
                />
                {errors.requestedAmount && (
                  <span className="text-xs text-red-400 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {errors.requestedAmount}
                  </span>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Productive Purpose
                </label>
                <Input
                  value={formData.purpose}
                  onChange={(e) => updateField('purpose', e.target.value)}
                  placeholder="e.g. EV Battery Swap, Inventory, Tools"
                />
                {errors.purpose && (
                  <span className="text-xs text-red-400 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {errors.purpose}
                  </span>
                )}
              </div>
            </div>

            {/* Summary Preview Pills */}
            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs">
              <span className="font-bold text-muted-foreground uppercase tracking-wider text-[11px]">
                Application Summary
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-slate-300">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Applicant</span>
                  <span className="font-semibold text-white">{formData.fullName}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Platforms</span>
                  <span className="font-semibold text-white">{formData.primaryPlatform}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Recovery Speed</span>
                  <span className="font-semibold text-teal-300">{formData.typicalRecoveryDays} Days</span>
                </div>
              </div>
            </div>

            {/* Consent Checkbox */}
            <div className="p-4 rounded-2xl bg-[#0E1F3D] border border-cyan-500/25 space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consentGiven}
                  onChange={(e) => updateField('consentGiven', e.target.checked)}
                  className="size-4 rounded accent-cyan-400 mt-0.5 cursor-pointer"
                />
                <span className="text-xs text-slate-200 leading-relaxed">
                  I grant voluntary consent for PARAKH to evaluate my alternative cashflow frequency,
                  shock recovery metrics, and platform telemetry. I understand that PARAKH is an explainable assessment
                  intelligence prototype and does not represent an automated legal lending decision.
                </span>
              </label>
              {errors.consentGiven && (
                <span className="text-xs text-red-400 block pl-7">
                  {errors.consentGiven}
                </span>
              )}
            </div>
          </div>
        )}

        {/* NAVIGATION ACTIONS (BACK & CONTINUE) */}
        <div className="flex items-center justify-between pt-4 border-t border-white/[0.06]">
          {currentStep > 1 ? (
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              className="rounded-full gap-2 text-xs font-semibold px-5"
            >
              <ArrowLeft className="size-3.5" /> Back
            </Button>
          ) : (
            <Link href="/user/dashboard">
              <Button type="button" variant="ghost" className="rounded-full text-xs text-muted-foreground">
                Cancel
              </Button>
            </Link>
          )}

          <Button
            type="button"
            variant="lime"
            onClick={handleNext}
            className="rounded-full gap-2 text-xs font-bold px-6 shadow-md"
          >
            <span>{currentStep === 5 ? 'Submit for Assessment' : 'Continue'}</span>
            <ArrowRight className="size-3.5" />
          </Button>
        </div>
      </Card>
    </PageTransition>
  );
}
