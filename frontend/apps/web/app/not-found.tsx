import React from 'react';
import Link from 'next/link';
import { FileQuestion, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-8 border-border bg-surface text-center space-y-4">
        <FileQuestion className="size-12 text-foreground-muted mx-auto" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-foreground">Page Not Found</h2>
          <p className="text-xs text-foreground-muted">
            The requested page or credit resource could not be found or has been moved.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Link href="/">
            <Button variant="default" size="sm" className="rounded-full text-xs gap-1.5">
              <Home className="size-3.5" /> Return Home
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
}
