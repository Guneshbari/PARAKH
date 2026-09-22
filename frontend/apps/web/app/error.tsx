'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log safe error trace internally for monitoring without leaking raw backend errors to UI
    console.error('Unhandled UI Error:', error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-8 border-border bg-surface text-center space-y-4">
        <AlertCircle className="size-12 text-destructive mx-auto" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-foreground">Something went wrong</h2>
          <p className="text-xs text-foreground-muted">
            An unexpected error occurred while rendering this page. Our platform safeguards prevent data corruption.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            variant="default"
            size="sm"
            onClick={() => reset()}
            className="rounded-full text-xs gap-1.5"
          >
            <RefreshCw className="size-3.5" /> Try Again
          </Button>
          <Link href="/">
            <Button variant="outline" size="sm" className="rounded-full text-xs gap-1.5">
              <Home className="size-3.5" /> Return Home
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
