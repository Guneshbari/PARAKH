'use client';

import React, { use, useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Sparkles,
  Building2,
  Calendar,
  DollarSign,
  UserCheck,
  Printer,
  ChevronRight,
  Info,
  Layers,
  AlertCircle,
  RefreshCw,
  FileText,
  Upload,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { formatCurrency } from '@/lib/utils';
import {
  api,
  adaptApplication,
  adaptAssessment,
  adaptReviewOutcome,
  adaptDocumentRequest,
  ApiError,
  type BackendApplication,
  type BackendApplicantProfile,
} from '@parakh/api';
import type {
  AllowedFileType,
  ApplicationStatus,
  CreditApplication,
  DocumentRequest,
  DocumentType,
} from '@parakh/types';

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  BANK_STATEMENT: 'Bank Statement',
  INCOME_PROOF: 'Income Proof',
  TRANSACTION_STATEMENT: 'Transaction Statement',
  BUSINESS_RECORD: 'Business Record',
  OTHER: 'Other',
};

interface ApplicationDetailPageProps {
  params: Promise<{ id: string }>;
}

interface TimelineStage {
  id: string;
  title: string;
  description: string;
  status: 'COMPLETED' | 'ACTIVE' | 'PENDING';
  timestamp?: string;
}

export default function ApplicationDetailPage({ params }: ApplicationDetailPageProps) {
  const { id } = use(params);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [application, setApplication] = useState<CreditApplication | null>(null);
  const [documentRequests, setDocumentRequests] = useState<DocumentRequest[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Record<string, File>>({});
  const [uploadErrors, setUploadErrors] = useState<Record<string, string | null>>({});
  const [submittingIds, setSubmittingIds] = useState<Record<string, boolean>>({});
  const [submissionSuccess, setSubmissionSuccess] = useState<
    Record<string, { filename: string; timestamp: string }>
  >({});

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getAcceptAttribute = (allowedTypes: AllowedFileType[]): string => {
    const mimes: string[] = [];
    if (allowedTypes.includes('PDF')) {
      mimes.push('.pdf', 'application/pdf');
    }
    if (allowedTypes.includes('XLS')) {
      mimes.push('.xls', 'application/vnd.ms-excel');
    }
    if (allowedTypes.includes('XLSX')) {
      mimes.push(
        '.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      );
    }
    return mimes.join(',');
  };

  const validateFile = (file: File, allowedTypes: AllowedFileType[]): string | null => {
    if (!file) return 'Please choose a file.';
    if (file.size === 0) return 'The selected file is empty.';
    if (file.size > 10 * 1024 * 1024) return 'File exceeds maximum allowed size of 10 MB.';

    const ext = file.name.split('.').pop()?.toUpperCase();
    if (!ext || !['PDF', 'XLS', 'XLSX'].includes(ext)) {
      return 'Invalid file extension. Only PDF, XLS, and XLSX files are accepted.';
    }

    if (!allowedTypes.includes(ext as AllowedFileType)) {
      return `File format .${ext.toLowerCase()} is not allowed for this request. Accepted formats: ${allowedTypes.join(', ')}`;
    }

    return null;
  };

  const handleFileChange = (requestId: string, file: File | null, allowedTypes: AllowedFileType[]) => {
    if (!file) {
      setSelectedFiles((prev) => {
        const next = { ...prev };
        delete next[requestId];
        return next;
      });
      setUploadErrors((prev) => ({ ...prev, [requestId]: null }));
      return;
    }

    const validationErr = validateFile(file, allowedTypes);
    if (validationErr) {
      setUploadErrors((prev) => ({ ...prev, [requestId]: validationErr }));
      setSelectedFiles((prev) => {
        const next = { ...prev };
        delete next[requestId];
        return next;
      });
      return;
    }

    setUploadErrors((prev) => ({ ...prev, [requestId]: null }));
    setSelectedFiles((prev) => ({ ...prev, [requestId]: file }));
  };

  const handleRemoveFile = (requestId: string) => {
    setSelectedFiles((prev) => {
      const next = { ...prev };
      delete next[requestId];
      return next;
    });
    setUploadErrors((prev) => ({ ...prev, [requestId]: null }));
  };

  const handleSubmitDocument = async (requestId: string) => {
    const file = selectedFiles[requestId];
    if (!file) {
      setUploadErrors((prev) => ({ ...prev, [requestId]: 'Please select a file to submit.' }));
      return;
    }

    try {
      setSubmittingIds((prev) => ({ ...prev, [requestId]: true }));
      setUploadErrors((prev) => ({ ...prev, [requestId]: null }));

      const res = await api.submitDocumentRequest(id, requestId, file);

      setSubmissionSuccess((prev) => ({
        ...prev,
        [requestId]: { filename: res.filename, timestamp: res.submitted_at },
      }));

      // Update local request state
      setDocumentRequests((prev) =>
        prev.map((r) =>
          r.id === requestId
            ? {
                ...r,
                status: 'SUBMITTED',
                submittedDocument: {
                  id: res.document_id,
                  applicationId: id,
                  documentRequestId: requestId,
                  originalFilename: res.filename,
                  storedFilename: '',
                  fileType: '',
                  mimeType: '',
                  fileSize: res.file_size,
                  uploadedBy: '',
                  createdAt: res.submitted_at,
                },
              }
            : r
        )
      );

      // Remove selected file from state
      setSelectedFiles((prev) => {
        const next = { ...prev };
        delete next[requestId];
        return next;
      });

      // Refetch application details to ensure synchronicity
      await fetchApplicationDetails();
    } catch (err: any) {
      console.error('Document submission error:', err);
      const msg =
        err?.userMessage || err?.message || 'Failed to submit document. Please try again.';
      setUploadErrors((prev) => ({ ...prev, [requestId]: msg }));
    } finally {
      setSubmittingIds((prev) => ({ ...prev, [requestId]: false }));
    }
  };

  const fetchApplicationDetails = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // 1. Fetch Application Record
      const rawApp = await api.getApplicationById(id);

      // 2. Fetch Associated Applicant Profile
      let rawProfile: BackendApplicantProfile | null = null;
      if (rawApp.applicant_profile_id) {
        try {
          rawProfile = await api.getApplicantProfile(rawApp.applicant_profile_id);
        } catch {
          rawProfile = null;
        }
      }

      // 3. Fetch Assessment if available
      let assessment = null;
      try {
        const rawAssessment = await api.getLatestAssessmentByApplication(id);
        assessment = adaptAssessment(rawAssessment, rawProfile?.full_name || undefined);
      } catch {
        assessment = null;
      }

      // 4. Fetch Reviews if available
      let reviewOutcome = null;
      try {
        const reviews = await api.getReviewsByApplication(id);
        if (reviews.length > 0) {
          reviewOutcome = adaptReviewOutcome(reviews[0]);
        }
      } catch {
        reviewOutcome = null;
      }

      // 5. Fetch Document Requests (Phase 1 read-only display)
      let docReqs: DocumentRequest[] = [];
      try {
        const rawDocs = await api.getDocumentRequests(id);
        docReqs = rawDocs.map(adaptDocumentRequest);
      } catch {
        docReqs = [];
      }
      setDocumentRequests(docReqs);

      const adapted = adaptApplication(rawApp, rawProfile, assessment, reviewOutcome);
      setApplication(adapted);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 404) {
        setError('Application not found');
      } else {
        const msg = err instanceof ApiError ? err.userMessage : 'Failed to load application details.';
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchApplicationDetails();
  }, [fetchApplicationDetails]);

  // Derive timeline stages based on application status
  const getTimelineStages = (status: ApplicationStatus, app: CreditApplication): TimelineStage[] => {
    const isStage2 =
      status === 'DATA_VALIDATION' ||
      status === 'FINANCIAL_ANALYSIS' ||
      status === 'ASSESSMENT_COMPLETED' ||
      status === 'MANUAL_REVIEW_REQUIRED' ||
      status === 'REVIEW_COMPLETED';
    const isStage3 =
      status === 'FINANCIAL_ANALYSIS' ||
      status === 'ASSESSMENT_COMPLETED' ||
      status === 'MANUAL_REVIEW_REQUIRED' ||
      status === 'REVIEW_COMPLETED';
    const isStage4 =
      status === 'ASSESSMENT_COMPLETED' ||
      status === 'MANUAL_REVIEW_REQUIRED' ||
      status === 'REVIEW_COMPLETED';

    return [
      {
        id: 's1',
        title: 'Application Intake & Consent',
        description: 'Personal profile, gig credentials, and statutory DPDP consent artifact registered.',
        status: isStage2 ? 'COMPLETED' : status === 'SUBMITTED' ? 'ACTIVE' : 'COMPLETED',
        timestamp: new Date(app.submittedAt).toLocaleDateString('en-IN', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
      },
      {
        id: 's2',
        title: 'Alternative Data Ingestion',
        description: 'KYC attestation verified; active telemetry linked across platform APIs.',
        status: isStage3
          ? 'COMPLETED'
          : status === 'DATA_VALIDATION'
          ? 'ACTIVE'
          : isStage2
          ? 'ACTIVE'
          : 'PENDING',
        timestamp: isStage3 ? 'Telemetry verified' : undefined,
      },
      {
        id: 's3',
        title: 'Cashflow Volatility Modeling',
        description: 'Income trends, cyclical dip rebounds, and micro-obligation cadences calculated.',
        status: isStage4
          ? 'COMPLETED'
          : status === 'FINANCIAL_ANALYSIS'
          ? 'ACTIVE'
          : 'PENDING',
        timestamp: isStage4 ? 'Model executed' : undefined,
      },
      {
        id: 's4',
        title: 'Explainable Score Synthesis',
        description: 'Alternative score generated with transparent positive & attention feature factors.',
        status:
          status === 'ASSESSMENT_COMPLETED' || status === 'REVIEW_COMPLETED'
            ? 'COMPLETED'
            : status === 'MANUAL_REVIEW_REQUIRED'
            ? 'COMPLETED'
            : 'PENDING',
        timestamp: app.assessment
          ? `Score: ${app.assessment.score} / 850`
          : undefined,
      },
      {
        id: 's5',
        title:
          status === 'MANUAL_REVIEW_REQUIRED'
            ? 'Human Credit Reviewer In-Loop Review'
            : status === 'REVIEW_COMPLETED'
            ? 'Credit Reviewer Outcome Recorded'
            : 'Institutional Credit Review Readout',
        description:
          status === 'MANUAL_REVIEW_REQUIRED'
            ? 'A certified credit reviewer is reviewing telemetry cross-checks and variance indicators.'
            : status === 'REVIEW_COMPLETED'
            ? 'Credit reviewer verified platform continuity and recorded final assessment outcome.'
            : 'Assessment ready for participating institutional credit reviewer without automated decisions.',
        status:
          status === 'REVIEW_COMPLETED'
            ? 'COMPLETED'
            : status === 'MANUAL_REVIEW_REQUIRED'
            ? 'ACTIVE'
            : status === 'ASSESSMENT_COMPLETED'
            ? 'COMPLETED'
            : 'PENDING',
        timestamp: app.review?.recordedAt
          ? new Date(app.review.recordedAt).toLocaleDateString('en-IN', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })
          : undefined,
      },
    ];
  };

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <h2 className="text-base font-semibold text-foreground">Loading Application Details...</h2>
        <p className="text-xs text-foreground-muted">Retrieving pipeline status and evaluation records.</p>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4">
        <Card className="p-8 border-border bg-surface space-y-4 text-center">
          <AlertCircle className="size-10 text-red-500 mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">
              {error === 'Application not found' ? 'Application Not Found' : 'Unable to Load Application'}
            </h2>
            <p className="text-xs text-foreground-secondary">
              {error === 'Application not found'
                ? `No credit evaluation application exists with identifier ${id}.`
                : error}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link href="/user/applications">
              <Button variant="outline" size="sm" className="rounded-full text-xs">
                <ArrowLeft className="size-3.5 mr-1" /> All Applications
              </Button>
            </Link>
            {error !== 'Application not found' && (
              <Button
                variant="default"
                size="sm"
                onClick={() => fetchApplicationDetails()}
                className="rounded-full text-xs"
              >
                <RefreshCw className="size-3.5 mr-1" /> Retry
              </Button>
            )}
          </div>
        </Card>
      </div>
    );
  }

  const stages = getTimelineStages(application.status, application);

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/user/applications">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs sm:text-sm px-4 cursor-pointer">
              <ArrowLeft className="size-3.5" /> Back to Applications
            </Button>
          </Link>
          <span className="text-xs sm:text-sm text-foreground-secondary font-mono">
            {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs sm:text-sm text-foreground-secondary hover:text-foreground px-3.5 cursor-pointer"
          >
            <Printer className="size-3.5" /> Print Summary
          </Button>

          {application.assessment && (
            <Link href={`/user/results/${application.id}`}>
              <Button variant="default" size="sm" className="rounded-full gap-1.5 text-xs sm:text-sm px-4 font-semibold cursor-pointer">
                <span>View Full Assessment Dossier</span>
                <ChevronRight className="size-3.5" />
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* 2. APPLICATION SUMMARY HERO CARD */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface dark:bg-surface-elevated border border-border shadow-xs space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs sm:text-sm font-mono text-foreground-secondary uppercase tracking-wider">
                Credit Evaluation Request
              </span>
              <StatusBadge status={application.status} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              {application.purpose}
            </h1>
          </div>

          <div className="text-left md:text-right">
            <div className="text-xs sm:text-sm text-foreground-secondary">Requested Amount</div>
            <div className="text-2xl sm:text-3xl font-extrabold text-foreground">
              {formatCurrency(application.requestedAmount)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
          <div className="space-y-1">
            <span className="text-xs text-foreground-secondary flex items-center gap-1">
              <Building2 className="size-3" /> Borrower Profile
            </span>
            <div className="text-sm font-semibold text-foreground">
              {application.applicantName}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-foreground-secondary flex items-center gap-1">
              <UserCheck className="size-3" /> Employment Model
            </span>
            <div className="text-sm font-semibold text-foreground">
              {application.employmentType.replace('_', ' ')}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-foreground-secondary flex items-center gap-1">
              <Calendar className="size-3" /> Submitted Date
            </span>
            <div className="text-sm font-semibold text-foreground">
              {new Date(application.submittedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-foreground-secondary flex items-center gap-1">
              <Sparkles className="size-3" /> Evaluation Tier
            </span>
            <div>
              <RiskBadge riskLevel={application.assessment?.riskLevel || 'MODERATE_ESTIMATED RISK'} />
            </div>
          </div>
        </div>
      </div>

      {/* 3. STEP-BY-STEP EVALUATION PIPELINE LIFECYCLE */}
      <section className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg sm:text-xl font-bold text-foreground">
            Evaluation Pipeline Progress
          </h2>
          <p className="text-xs sm:text-sm text-foreground-secondary">
            Auditable tracking of each stage in the PARAKH alternative assessment workflow.
          </p>
        </div>

        <div className="space-y-3">
          {stages.map((stage, index) => (
            <Card
              key={stage.id}
              className={`p-5 transition-all border ${
                stage.status === 'ACTIVE'
                  ? 'border-primary/40 bg-primary/5 shadow-xs'
                  : stage.status === 'COMPLETED'
                  ? 'border-border bg-surface'
                  : 'border-border/60 bg-surface/50 opacity-65'
              }`}
            >
              <div className="flex items-start gap-4">
                {/* Step indicator */}
                <div
                  className={`size-8 rounded-full flex items-center justify-center shrink-0 font-mono font-bold text-xs sm:text-sm ${
                    stage.status === 'COMPLETED'
                      ? 'bg-primary text-primary-foreground'
                      : stage.status === 'ACTIVE'
                      ? 'bg-primary/20 text-primary border-2 border-primary animate-pulse'
                      : 'bg-surface-highlight border border-border text-foreground-secondary'
                  }`}
                >
                  {stage.status === 'COMPLETED' ? (
                    <CheckCircle2 className="size-4.5 stroke-[2.5]" />
                  ) : (
                    index + 1
                  )}
                </div>

                <div className="flex-1 space-y-1">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <h3
                      className={`text-sm sm:text-base font-semibold ${
                        stage.status === 'ACTIVE' ? 'text-foreground' : 'text-foreground-secondary'
                      }`}
                    >
                      {stage.title}
                    </h3>
                    {stage.timestamp && (
                      <span className="text-xs text-foreground-secondary font-mono">
                        {stage.timestamp}
                      </span>
                    )}
                  </div>
                  <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
                    {stage.description}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* 4. ADDITIONAL INFORMATION REQUIRED (DOCUMENT REQUESTS) */}
      {documentRequests && documentRequests.length > 0 && (
        <section className="space-y-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <FileText className="size-5 text-amber-500" />
              <h2 className="text-lg sm:text-xl font-bold text-foreground">
                Additional Information Required
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Reviewer verification documents for this application.
            </p>
          </div>

          <div className="space-y-4">
            {documentRequests.map((req) => {
              const selectedFile = selectedFiles[req.id];
              const uploadError = uploadErrors[req.id];
              const isSubmitting = submittingIds[req.id];
              const successData =
                submissionSuccess[req.id] ||
                (req.submittedDocument
                  ? {
                      filename: req.submittedDocument.originalFilename,
                      timestamp: req.submittedDocument.createdAt,
                    }
                  : null);

              return (
                <Card
                  key={req.id}
                  className={`p-6 space-y-4 border transition-all ${
                    req.status === 'PENDING'
                      ? 'border-amber-500/30 bg-surface'
                      : req.status === 'REJECTED'
                      ? 'border-destructive/30 bg-surface'
                      : 'border-emerald-500/30 bg-surface'
                  }`}
                >
                  {/* Header: Document Type & Status */}
                  <div className="flex items-center justify-between pb-3 border-b border-border">
                    <div className="space-y-0.5">
                      <span className="text-[11px] font-mono uppercase tracking-wider text-foreground-secondary">
                        Document
                      </span>
                      <div className="text-base font-bold text-foreground">
                        {DOCUMENT_TYPE_LABELS[req.documentType] || req.documentType}
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-xs font-mono uppercase px-2.5 py-0.5 rounded-full ${
                        req.status === 'PENDING'
                          ? 'border-amber-500/40 text-amber-600 bg-amber-500/10 dark:text-amber-400'
                          : req.status === 'SUBMITTED'
                          ? 'border-blue-500/40 text-blue-600 bg-blue-500/10 dark:text-blue-400'
                          : req.status === 'ACCEPTED'
                          ? 'border-emerald-500/40 text-emerald-600 bg-emerald-500/10 dark:text-emerald-400'
                          : 'border-destructive/40 text-destructive bg-destructive/10'
                      }`}
                    >
                      {req.status === 'REJECTED' ? 'REPLACEMENT REQUIRED' : req.status}
                    </Badge>
                  </div>

                  {/* Request details */}
                  <div className="space-y-1">
                    <span className="text-xs font-medium text-foreground-secondary">
                      Request
                    </span>
                    <p className="text-sm text-foreground bg-surface-highlight/40 p-3.5 rounded-xl border border-border leading-relaxed">
                      {req.description}
                    </p>
                  </div>

                  {/* Metadata: Formats & Max Size */}
                  <div className="grid grid-cols-2 gap-4 text-xs text-foreground-secondary py-1">
                    <div>
                      <span className="font-medium text-foreground-secondary block">
                        Accepted formats
                      </span>
                      <span className="font-mono font-medium text-foreground">
                        {req.allowedFileTypes.join(', ')}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium text-foreground-secondary block">
                        Maximum size
                      </span>
                      <span className="font-mono font-medium text-foreground">10 MB</span>
                    </div>
                  </div>

                  {/* ACCEPTED State */}
                  {req.status === 'ACCEPTED' && (
                    <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs sm:text-sm flex items-start gap-3">
                      <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <span className="font-semibold text-emerald-600 dark:text-emerald-400 block">
                          Accepted
                        </span>
                        <p className="text-xs text-foreground-secondary">
                          Your document has been reviewed and accepted.
                        </p>
                        {req.reviewerNotes && (
                          <div className="text-xs text-foreground bg-surface-highlight/60 p-2.5 rounded-lg border border-border mt-2">
                            <span className="font-medium text-foreground-secondary block mb-0.5">Reviewer note:</span>
                            <p className="leading-relaxed">{req.reviewerNotes}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* REJECTED State: Show reviewer note and replacement upload */}
                  {req.status === 'REJECTED' && (
                    <div className="space-y-4">
                      <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-xs sm:text-sm flex items-start gap-3">
                        <AlertCircle className="size-4 text-destructive shrink-0 mt-0.5" />
                        <div className="space-y-1 flex-1">
                          <span className="font-semibold text-destructive block">
                            Replacement Required
                          </span>
                          <p className="text-xs text-foreground-secondary">
                            The submitted document requires replacement. Please review the reviewer note below and upload an updated document.
                          </p>
                          {req.reviewerNotes && (
                            <div className="text-xs text-foreground bg-surface-highlight/80 p-3 rounded-lg border border-border mt-2">
                              <span className="font-semibold text-foreground-secondary block mb-1">Reviewer note:</span>
                              <p className="leading-relaxed text-foreground font-medium">{req.reviewerNotes}</p>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Choose Replacement Document File Control */}
                      <div className="pt-2 border-t border-border space-y-3">
                        <span className="text-xs font-semibold text-foreground block">Upload Replacement Document</span>
                        {!selectedFile ? (
                          <div>
                            <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-border rounded-xl bg-surface-highlight/20 hover:bg-surface-highlight/40 cursor-pointer transition-colors text-center group">
                              <Upload className="size-6 text-foreground-secondary group-hover:text-foreground transition-colors mb-2" />
                              <span className="text-xs sm:text-sm font-semibold text-foreground">
                                Choose Replacement Document
                              </span>
                              <span className="text-[11px] text-foreground-muted mt-1">
                                {req.allowedFileTypes.join(', ')} up to 10 MB
                              </span>
                              <input
                                type="file"
                                className="hidden"
                                accept={getAcceptAttribute(req.allowedFileTypes)}
                                onChange={(e) => {
                                  const file = e.target.files?.[0] || null;
                                  handleFileChange(req.id, file, req.allowedFileTypes);
                                }}
                              />
                            </label>
                          </div>
                        ) : (
                          <div className="p-3.5 rounded-xl bg-surface-highlight/50 border border-border flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <FileText className="size-4 text-primary shrink-0" />
                              <div className="truncate">
                                <span className="text-xs sm:text-sm font-semibold text-foreground truncate block">
                                  {selectedFile.name}
                                </span>
                                <span className="text-[11px] font-mono text-foreground-muted">
                                  {formatFileSize(selectedFile.size)}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                disabled={isSubmitting}
                                onClick={() => handleRemoveFile(req.id)}
                                className="text-xs h-8 px-2.5 rounded-full text-foreground-secondary hover:text-destructive cursor-pointer"
                              >
                                <X className="size-3.5 mr-1" /> Remove
                              </Button>

                              <Button
                                type="button"
                                variant="default"
                                size="sm"
                                disabled={isSubmitting}
                                onClick={() => handleSubmitDocument(req.id)}
                                className="text-xs font-semibold h-8 px-4 rounded-full shadow-xs cursor-pointer"
                              >
                                {isSubmitting ? (
                                  <>
                                    <Loader2 className="size-3.5 animate-spin mr-1" /> Submitting...
                                  </>
                                ) : (
                                  'Submit Document'
                                )}
                              </Button>
                            </div>
                          </div>
                        )}

                        {uploadError && (
                          <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                            <AlertCircle className="size-4 shrink-0" />
                            <span>{uploadError}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* PENDING State: File upload control */}
                  {req.status === 'PENDING' && (
                    <div className="pt-2 border-t border-border space-y-3">
                      {!selectedFile ? (
                        <div>
                          <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-border rounded-xl bg-surface-highlight/20 hover:bg-surface-highlight/40 cursor-pointer transition-colors text-center group">
                            <Upload className="size-6 text-foreground-secondary group-hover:text-foreground transition-colors mb-2" />
                            <span className="text-xs sm:text-sm font-semibold text-foreground">
                              Upload / Choose File
                            </span>
                            <span className="text-[11px] text-foreground-muted mt-1">
                              {req.allowedFileTypes.join(', ')} up to 10 MB
                            </span>
                            <input
                              type="file"
                              className="hidden"
                              accept={getAcceptAttribute(req.allowedFileTypes)}
                              onChange={(e) => {
                                const file = e.target.files?.[0] || null;
                                handleFileChange(req.id, file, req.allowedFileTypes);
                              }}
                            />
                          </label>
                        </div>
                      ) : (
                        <div className="p-3.5 rounded-xl bg-surface-highlight/50 border border-border flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <FileText className="size-4 text-primary shrink-0" />
                            <div className="truncate">
                              <span className="text-xs sm:text-sm font-semibold text-foreground truncate block">
                                {selectedFile.name}
                              </span>
                              <span className="text-[11px] font-mono text-foreground-muted">
                                {formatFileSize(selectedFile.size)}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={isSubmitting}
                              onClick={() => handleRemoveFile(req.id)}
                              className="text-xs h-8 px-2.5 rounded-full text-foreground-secondary hover:text-destructive cursor-pointer"
                            >
                              <X className="size-3.5 mr-1" /> Remove
                            </Button>

                            <Button
                              type="button"
                              variant="default"
                              size="sm"
                              disabled={isSubmitting}
                              onClick={() => handleSubmitDocument(req.id)}
                              className="text-xs font-semibold h-8 px-4 rounded-full shadow-xs cursor-pointer"
                            >
                              {isSubmitting ? (
                                <>
                                  <Loader2 className="size-3.5 animate-spin mr-1" /> Submitting...
                                </>
                              ) : (
                                'Submit Document'
                              )}
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Client/Server Validation Error Banner */}
                      {uploadError && (
                        <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                          <AlertCircle className="size-4 shrink-0" />
                          <span>{uploadError}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* SUBMITTED State: Read-only submitted summary */}
                  {req.status === 'SUBMITTED' && (
                    <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs sm:text-sm flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <div>
                          <span className="font-semibold text-foreground block">
                            Submitted
                          </span>
                          <span className="text-xs text-foreground-secondary font-mono">
                            {successData?.filename || 'Uploaded verification document'}
                          </span>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono text-foreground-muted">
                        Awaiting review
                      </span>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* 5. UNDERWRITER REVIEW SECTION IF RECORDED */}
      {application.review && (
        <section className="space-y-3">
          <h2 className="text-lg sm:text-xl font-bold text-foreground">
            Credit Reviewer Readout
          </h2>
          <Card className="p-5 space-y-3 border-border bg-surface">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">
                Review Status: {application.review.status.replace(/_/g, ' ')}
              </span>
              <span className="text-xs sm:text-sm text-foreground-secondary">
                Reviewer: {application.review.underwriterName || 'Underwriting Officer'}
              </span>
            </div>
            {application.review.decisionNotes && (
              <p className="text-sm text-foreground-secondary bg-surface-highlight p-3 rounded-lg border border-border">
                &ldquo;{application.review.decisionNotes}&rdquo;
              </p>
            )}
          </Card>
        </section>
      )}
    </PageTransition>
  );
}
