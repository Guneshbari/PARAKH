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
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  ApiError,
  type BackendApplicantProfile,
  type BackendApplication,
} from '@parakh/api';

const STEPS = [
  { id: 1, label: 'Personal', icon: User },
  { id: 2, label: 'Work Profile', icon: Briefcase },
  { id: 3, label: 'Cashflow Rhythm', icon: Activity },
  { id: 4, label: 'Obligations', icon: CreditCard },
  { id: 5, label: 'Consent & Review', icon: FileCheck2 },
];

export default function NewApplicationPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionPhase, setSubmissionPhase] = useState('');
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [createdApp, setCreatedApp] = useState<BackendApplication | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Form State initialized with realistic defaults for a smooth test run
  const [formData, setFormData] = useState<ApplicationFormData>({
    fullName: user?.name || 'Arjun Verma',
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
      if (formData.lowestMonthIncome > formData.averageMonthlyIncome) {
        stepErrors.lowestMonthIncome = 'Lowest month income cannot exceed average income';
      }
      if (!formData.typicalRecoveryDays || formData.typicalRecoveryDays < 1) {
        stepErrors.typicalRecoveryDays = 'Recovery days must be at least 1';
      }
    } else if (currentStep === 4) {
      if (formData.monthlyRent < 0) {
        stepErrors.monthlyRent = 'Monthly rent cannot be negative';
      }
      if (formData.utilityExpenses < 0) {
        stepErrors.utilityExpenses = 'Utility expenses cannot be negative';
      }
      if (formData.existingEmiObligations < 0) {
        stepErrors.existingEmiObligations = 'EMI obligations cannot be negative';
      }
      if (formData.requestedAmount < 1000) {
        stepErrors.requestedAmount = 'Minimum loan requested is ₹1,000';
      }
      if (!formData.purpose || formData.purpose.length < 5) {
        stepErrors.purpose = 'Please provide a clear loan purpose (min 5 characters)';
      }
    } else if (currentStep === 5) {
      if (!formData.consentGiven) {
        stepErrors.consentGiven = 'Voluntary consent is required to process assessment';
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

    if (!user) {
      setSubmissionError('You must be signed in to submit an evaluation application.');
      return;
    }

    setIsSubmitting(true);
    setSubmissionError(null);

    try {
      // Step 1: Ensure ApplicantProfile exists
      setSubmissionPhase('1/5: Verifying applicant identity & profile...');
      let profile: BackendApplicantProfile;
      try {
        profile = await api.getApplicantByUserId(user.id);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 404) {
          profile = await api.createApplicant({
            gig_work_type: formData.employmentType || 'GIG_WORKER',
            work_type: formData.employmentType || 'GIG_WORKER',
            years_working: Number((formData.tenureMonths / 12).toFixed(1)),
            business_or_loan_purpose: formData.purpose,
            full_name: formData.fullName,
            phone_number: formData.phone,
            city: formData.city,
            experience_months: formData.tenureMonths,
            declared_monthly_income: formData.averageMonthlyIncome,
            preferred_loan_purpose: formData.purpose,
          });
        } else {
          throw err;
        }
      }

      // Step 2: Create Credit Application
      setSubmissionPhase('2/5: Registering credit evaluation application...');
      let activeApp = createdApp;
      if (!activeApp) {
        activeApp = await api.createApplication({
          applicant_profile_id: profile.id,
          requested_loan_amount: formData.requestedAmount,
          loan_purpose: formData.purpose,
          preferred_repayment_period: 12,
        });
        setCreatedApp(activeApp);
      }

      // Step 3: Register DPDP Statutory Consent
      setSubmissionPhase('3/5: Registering statutory DPDP Act consent...');
      try {
        await api.createConsent({
          application_id: activeApp.id,
          applicant_profile_id: profile.id,
          data_source: 'PLATFORM',
          purpose: 'Alternative credit assessment and risk evaluation under DPDP Act 2023',
          granted: true,
        });
      } catch (consentErr: unknown) {
        // If consent was already granted on a previous retry, ignore conflict
        if (!(consentErr instanceof ApiError && consentErr.status === 409)) {
          throw consentErr;
        }
      }

      // Step 4: Ingest Aggregated Financial Telemetry Signals
      setSubmissionPhase('4/5: Ingesting verified platform & cashflow telemetry...');
      const incomeVol =
        formData.lowestMonthIncome && formData.averageMonthlyIncome > 0
          ? Math.max(
              0,
              Math.min(
                1,
                (formData.averageMonthlyIncome - formData.lowestMonthIncome) /
                  formData.averageMonthlyIncome
              )
            )
          : 0.18;
      const totalObligation =
        (formData.monthlyRent || 0) +
        (formData.utilityExpenses || 0) +
        (formData.existingEmiObligations || 0);

      await api.recordFinancialSignals(activeApp.id, {
        source: 'PLATFORM',
        average_income: formData.averageMonthlyIncome,
        median_income: Math.round(formData.averageMonthlyIncome * 0.95),
        income_volatility: Number(incomeVol.toFixed(2)),
        income_trend: 'STABLE',
        active_days: 24,
        payment_regularity: 0.95,
        cashflow_buffer: Math.max(0, formData.averageMonthlyIncome - totalObligation),
        existing_obligation: totalObligation,
        platform_rating: 4.85,
        repayment_reliability: 0.96,
        signal_metadata: {
          primary_platform: formData.primaryPlatform,
          income_frequency: formData.incomeFrequency,
          typical_recovery_days: formData.typicalRecoveryDays,
        },
      });

      // Step 5: Execute MockAssessmentEngine Evaluation
      setSubmissionPhase('5/5: Executing alternative credit assessment...');
      await api.triggerAssessment(activeApp.id);

      // Verify assessment was persisted
      await api.getLatestAssessmentByApplication(activeApp.id);

      // Successfully finished! Route to results dossier
      router.push(`/user/results/${activeApp.id}`);
    } catch (err: unknown) {
      setIsSubmitting(false);
      const msg =
        err instanceof ApiError
          ? err.userMessage
          : err instanceof Error
          ? err.message
          : 'Application submission encountered an error. Please try again.';
      setSubmissionError(msg);
    }
  };

  if (isSubmitting) {
    return (
      <PageTransition className="max-w-xl mx-auto py-24 px-4 text-center space-y-6">
        <div className="size-16 rounded-2xl bg-surface-highlight border border-border flex items-center justify-center mx-auto text-foreground animate-pulse shadow-sm">
          <Sparkles className="size-8 opacity-80" />
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-foreground tracking-tight">
            Synthesizing PARAKH Assessment
          </h2>
          <p className="text-sm text-foreground-secondary font-mono animate-pulse">
            {submissionPhase}
          </p>
        </div>

        <div className="h-1.5 w-full bg-surface-highlight rounded-full overflow-hidden max-w-sm mx-auto">
          <div className="h-full bg-primary rounded-full animate-pulse w-3/4" />
        </div>

        <p className="text-xs text-foreground-muted pt-4">
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
          <Badge variant="outline" className="text-xs">
            <Sparkles className="size-3 opacity-70" />
            <span>Guided Assessment Flow</span>
          </Badge>
          <span className="text-xs font-mono font-semibold text-foreground-muted">
            Step {currentStep} of 5
          </span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
          Alternative Credit Evaluation Intake
        </h1>
        <p className="text-xs sm:text-sm text-foreground-muted leading-relaxed">
          PARAKH doesn&apos;t require traditional credit bureau history. Share your verified platform and cashflow rhythm
          to generate an explainable, volatility-aware assessment.
        </p>
      </div>

      {/* 2. PROGRESS STEPPER WITH RESTRAINED MONOCHROME INDICATORS */}
      <div className="grid grid-cols-5 gap-2 pt-2">
        {STEPS.map((s) => {
          const isActive = s.id === currentStep;
          const isCompleted = s.id < currentStep;

          return (
            <div
              key={s.id}
              onClick={() => s.id < currentStep && setCurrentStep(s.id)}
              className={`flex flex-col items-center gap-1.5 p-2.5 rounded-2xl border transition-all cursor-pointer ${
                isActive
                  ? 'bg-[#472393] text-white border-[#472393] shadow-xs dark:bg-foreground dark:text-background dark:border-foreground'
                  : isCompleted
                  ? 'bg-[#F5F1FF] border-[rgba(71,35,147,0.25)] text-[#472393] dark:bg-surface-highlight dark:border-border dark:text-foreground'
                  : 'bg-surface border-border text-foreground-muted opacity-60'
              }`}
            >
              <div
                className={`size-6 rounded-full flex items-center justify-center font-bold text-xs ${
                  isActive
                    ? 'bg-white text-[#472393] dark:bg-background dark:text-foreground'
                    : isCompleted
                    ? 'bg-[#472393] text-white dark:bg-foreground dark:text-background'
                    : 'bg-surface-highlight text-foreground-muted'
                }`}
              >
                {isCompleted ? '✓' : s.id}
              </div>
              <span className="text-xs font-semibold text-center hidden sm:inline truncate w-full">
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* 3. STEP CONTENT CARDS */}
      <Card className="p-7 sm:p-9 space-y-6 bg-surface border-border">
        {/* STEP 1: PERSONAL INFORMATION */}
        {currentStep === 1 && (
          <div className="space-y-5">
            <div className="space-y-1 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-surface-highlight border border-border text-foreground flex items-center justify-center text-xs font-bold">
                  1
                </span>
                <h2 className="text-xl font-bold text-foreground tracking-tight">
                  Personal Information
                </h2>
              </div>
              <p className="text-xs text-foreground-muted">
                Your verified contact credentials used to aggregate alternative financial feeds.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  Full Legal Name
                </label>
                <Input
                  value={formData.fullName}
                  onChange={(e) => updateField('fullName', e.target.value)}
                  placeholder="e.g. Arjun Verma"
                />
                {errors.fullName && (
                  <span className="text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {errors.fullName}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                    Mobile Number (UPI Linked)
                  </label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => updateField('phone', e.target.value)}
                    placeholder="9845128910"
                    maxLength={10}
                  />
                  {errors.phone && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.phone}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                    Operating City
                  </label>
                  <Input
                    value={formData.city}
                    onChange={(e) => updateField('city', e.target.value)}
                    placeholder="e.g. Bengaluru, Mumbai, Delhi"
                  />
                  {errors.city && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
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
            <div className="space-y-1 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-surface-highlight border border-border text-foreground flex items-center justify-center text-xs font-bold">
                  2
                </span>
                <h2 className="text-xl font-bold text-foreground tracking-tight">
                  Work & Platform Profile
                </h2>
              </div>
              <p className="text-xs text-foreground-muted">
                We reward verified platform tenure rather than demanding traditional salary slips.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
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
                      className={`p-3 rounded-2xl border text-xs font-medium text-center transition-all cursor-pointer ${
                        formData.employmentType === cat.id
                          ? 'bg-[#472393] text-white font-semibold shadow-xs border-[#472393] dark:bg-foreground dark:text-background dark:border-foreground'
                          : 'bg-surface-highlight border-border text-foreground-muted hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                    Primary Platforms / Trade
                  </label>
                  <Input
                    value={formData.primaryPlatform}
                    onChange={(e) => updateField('primaryPlatform', e.target.value)}
                    placeholder="e.g. Swiggy, Zomato, Urban Company, Kirana"
                  />
                  {errors.primaryPlatform && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.primaryPlatform}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                    Active Duration (Months)
                  </label>
                  <Input
                    type="number"
                    value={formData.tenureMonths || ''}
                    onChange={(e) => updateField('tenureMonths', parseInt(e.target.value) || 0)}
                    placeholder="e.g. 18"
                  />
                  {errors.tenureMonths && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
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
            <div className="space-y-1 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-surface-highlight border border-border text-foreground flex items-center justify-center text-xs font-bold">
                  3
                </span>
                <h2 className="text-xl font-bold text-foreground tracking-tight">
                  Income Inflow & Volatility Rhythm
                </h2>
              </div>
              <p className="text-xs text-foreground-muted">
                Crucial for PARAKH&apos;s volatility-aware engine. We model your natural dips alongside your rebound speed.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
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
                      className={`p-2.5 rounded-2xl border text-xs font-medium text-center transition-all cursor-pointer ${
                        formData.incomeFrequency === freq.id
                          ? 'bg-[#472393] text-white font-semibold shadow-xs border-[#472393] dark:bg-foreground dark:text-background dark:border-foreground'
                          : 'bg-surface-highlight border-border text-foreground-muted hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                      }`}
                    >
                      {freq.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                    Average Monthly Inflow (₹)
                  </label>
                  <Input
                    type="number"
                    value={formData.averageMonthlyIncome || ''}
                    onChange={(e) => updateField('averageMonthlyIncome', parseInt(e.target.value) || 0)}
                    placeholder="e.g. 52000"
                  />
                  {errors.averageMonthlyIncome && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.averageMonthlyIncome}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                    Lowest Month Inflow (₹)
                  </label>
                  <Input
                    type="number"
                    value={formData.lowestMonthIncome || ''}
                    onChange={(e) => updateField('lowestMonthIncome', parseInt(e.target.value) || 0)}
                    placeholder="e.g. 34000 (rainy season/downtime)"
                  />
                  {errors.lowestMonthIncome && (
                    <span className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="size-3" /> {errors.lowestMonthIncome}
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted flex items-center justify-between">
                  <span>Typical Days to Rebound to Normal Earnings</span>
                  <span className="text-foreground font-mono font-semibold">
                    {formData.typicalRecoveryDays} Days
                  </span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={30}
                  value={formData.typicalRecoveryDays}
                  onChange={(e) => updateField('typicalRecoveryDays', parseInt(e.target.value))}
                  className="w-full accent-foreground cursor-pointer"
                />
                <div className="flex justify-between text-xs text-foreground-secondary">
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
            <div className="space-y-1 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-surface-highlight border border-border text-foreground flex items-center justify-center text-xs font-bold">
                  4
                </span>
                <h2 className="text-xl font-bold text-foreground tracking-tight">
                  Existing Obligations & Bill Punctuality
                </h2>
              </div>
              <p className="text-xs text-foreground-muted">
                We assess your disposable margin after mandatory living expenses and utility bills.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
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
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
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
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
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

            <div className="p-4 rounded-2xl bg-surface-highlight/50 border border-border flex items-start gap-3">
              <CheckCircle2 className="size-4 text-foreground shrink-0 mt-0.5" />
              <p className="text-xs text-foreground-secondary leading-relaxed">
                <strong className="text-foreground">Punctuality Bonus:</strong> Verified on-time payment of electricity, gas cylinders, and mobile recharges serves as primary positive credit proof in our alternative model.
              </p>
            </div>
          </div>
        )}

        {/* STEP 5: REVIEW, PURPOSE & CONSENT */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div className="space-y-1 pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="size-6 rounded-full bg-surface-highlight border border-border text-foreground flex items-center justify-center text-xs font-bold">
                  5
                </span>
                <h2 className="text-xl font-bold text-foreground tracking-tight">
                  Assessment Purpose & Applicant Consent
                </h2>
              </div>
              <p className="text-xs text-foreground-muted">
                State your intended use of funds and provide voluntary authorization for alternative evaluation.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  Evaluation Amount Benchmark (₹)
                </label>
                <Input
                  type="number"
                  value={formData.requestedAmount || ''}
                  onChange={(e) => updateField('requestedAmount', parseInt(e.target.value) || 0)}
                  placeholder="e.g. 35000"
                />
                {errors.requestedAmount && (
                  <span className="text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {errors.requestedAmount}
                  </span>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  Productive Purpose
                </label>
                <Input
                  value={formData.purpose}
                  onChange={(e) => updateField('purpose', e.target.value)}
                  placeholder="e.g. EV Battery Swap, Inventory, Tools"
                />
                {errors.purpose && (
                  <span className="text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {errors.purpose}
                  </span>
                )}
              </div>
            </div>

            {/* Summary Preview Pills */}
            <div className="p-4 rounded-2xl bg-surface-highlight/40 border border-border space-y-2 text-xs sm:text-sm">
              <span className="font-semibold text-foreground-secondary uppercase tracking-wider text-xs">
                Application Summary
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-foreground-secondary">
                <div>
                  <span className="text-foreground-secondary block text-xs">Applicant</span>
                  <span className="font-semibold text-foreground">{formData.fullName}</span>
                </div>
                <div>
                  <span className="text-foreground-secondary block text-xs">Platforms</span>
                  <span className="font-semibold text-foreground">{formData.primaryPlatform}</span>
                </div>
                <div>
                  <span className="text-foreground-secondary block text-xs">Recovery Speed</span>
                  <span className="font-semibold text-foreground">{formData.typicalRecoveryDays} Days</span>
                </div>
              </div>
            </div>

            {/* Consent Checkbox */}
            <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consentGiven}
                  onChange={(e) => updateField('consentGiven', e.target.checked)}
                  className="size-4 rounded accent-[#472393] dark:accent-foreground mt-0.5 cursor-pointer"
                />
                <span className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
                  I grant voluntary consent for PARAKH to evaluate my alternative cashflow frequency,
                  shock recovery metrics, and platform telemetry. I understand that PARAKH is an explainable assessment
                  intelligence prototype and does not represent an automated legal lending decision.
                </span>
              </label>
              {errors.consentGiven && (
                <span className="text-xs text-red-500 block pl-7">
                  {errors.consentGiven}
                </span>
              )}
            </div>
          </div>
        )}

        {/* SUBMISSION ERROR ALERT */}
        {submissionError && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs flex items-start gap-2.5">
            <AlertCircle className="size-4 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold block">Submission Error</span>
              <span>{submissionError}</span>
            </div>
          </div>
        )}

        {/* NAVIGATION ACTIONS (BACK & CONTINUE) */}
        <div className="flex items-center justify-between pt-4 border-t border-border">
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
              <Button type="button" variant="ghost" className="rounded-full text-xs text-foreground-muted hover:text-foreground">
                Cancel
              </Button>
            </Link>
          )}

          <Button
            type="button"
            variant="default"
            onClick={handleNext}
            className="rounded-full gap-2 text-xs font-semibold px-6 shadow-xs cursor-pointer"
          >
            <span>{currentStep === 5 ? 'Submit for Assessment' : 'Continue'}</span>
            <ArrowRight className="size-3.5" />
          </Button>
        </div>
      </Card>
    </PageTransition>
  );
}
