'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, FileQuestion, ArrowRight } from 'lucide-react';
import { useAuth } from '@/components/auth/AuthContext';
import { api, ApiError, type BackendApplicantProfile, type BackendApplication } from '@parakh/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

export default function UserResultsRedirectPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function resolveLatestAssessment() {
      if (authLoading) return;
      if (!user) {
        router.replace('/login');
        return;
      }

      try {
        // 1. Fetch applicant profile
        let profile: BackendApplicantProfile | null = null;
        try {
          profile = await api.getApplicantByUserId(user.id);
        } catch (err: unknown) {
          if (err instanceof ApiError && err.status === 404) {
            profile = null;
          } else {
            throw err;
          }
        }

        if (!profile) {
          if (isMounted) router.replace('/user/applications');
          return;
        }

        // 2. Fetch applications for this profile
        const apps = await api.getApplicationsByApplicant(profile.id);
        if (!isMounted) return;

        if (apps && apps.length > 0) {
          // Sort newest first
          const sorted = [...apps].sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
          router.replace(`/user/results/${sorted[0].id}`);
        } else {
          router.replace('/user/applications');
        }
      } catch (err) {
        console.warn('Could not resolve latest application for assessment report:', err);
        if (isMounted) {
          setError('No active credit application found to display assessment dossier.');
        }
      }
    }

    resolveLatestAssessment();

    return () => {
      isMounted = false;
    };
  }, [user, authLoading, router]);

  if (error) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto px-4">
        <Card className="p-8 space-y-4 bg-surface border border-border">
          <FileQuestion className="size-10 text-foreground-secondary mx-auto" />
          <h2 className="text-base font-semibold text-foreground">No Assessment Available</h2>
          <p className="text-xs text-foreground-secondary leading-relaxed">
            {error}
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-2">
            <Link href="/user/applications">
              <Button variant="outline" size="sm" className="rounded-full text-xs">
                My Applications
              </Button>
            </Link>
            <Link href="/user/applications/new">
              <Button variant="default" size="sm" className="rounded-full text-xs gap-1">
                <span>Start New Assessment</span>
                <ArrowRight className="size-3" />
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="py-24 text-center space-y-4 max-w-md mx-auto px-4">
      <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
      <h2 className="text-base font-semibold text-foreground">Opening Verified Assessment Report...</h2>
      <p className="text-xs text-foreground-secondary">
        Resolving your latest verified credit dossier and explainable TreeSHAP factors.
      </p>
    </div>
  );
}
