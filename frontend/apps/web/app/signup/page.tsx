'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  User,
  Lock,
  Mail,
  ArrowRight,
  Sun,
  Moon,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/components/theme/ThemeProvider';
import { useAuth } from '@/components/auth/AuthContext';
import { cn } from '@/lib/utils';
import {
  AuthFormCard,
  AuthSubmitButton,
  AuthAlert,
  getAuthInputClassName,
  AuthStatus,
} from '@/components/auth/AuthFeedback';

function SignupFormContent() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [emailOrPhone, setEmailOrPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus>('idle');
  const [shakeKey, setShakeKey] = useState(0);

  const { isDark, toggleTheme } = useTheme();
  const { signup } = useAuth();

  const handleInputChange = (setter: (val: string) => void) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setter(e.target.value);
    if (authStatus === 'error') {
      setAuthStatus('idle');
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!fullName.trim()) {
      setError('Please enter your full legal name.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }
    if (!emailOrPhone.trim() || !emailOrPhone.includes('@')) {
      setError('Please enter a valid email address.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }
    if (password.length < 8) {
      setError('Password must contain at least 8 characters.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }
    if (!consent) {
      setError('You must accept the alternative credit evaluation terms and data consent.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }

    setAuthStatus('submitting');
    setIsSubmitting(true);
    try {
      await signup({
        name: fullName,
        email: emailOrPhone,
        password,
        confirmPassword,
        consent,
      });

      setAuthStatus('success');
      setError(null);

      // Brief 400ms confirmation window to showcase "Registration Verified"
      setTimeout(() => {
        router.push('/user/dashboard');
      }, 400);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setError(msg);
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex flex-col justify-between bg-background text-foreground transition-colors duration-200 overflow-x-hidden">
      {/* Background silk lines */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-35 dark:opacity-20">
        <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-gradient-to-br from-blue-400/20 to-indigo-500/10 blur-3xl" />
        <div className="absolute bottom-1/3 -left-32 w-96 h-96 rounded-full bg-gradient-to-tr from-purple-400/15 to-transparent blur-3xl" />
      </div>

      {/* Header */}
      <header className="relative z-10 w-full border-b border-border bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#472393] text-white dark:bg-foreground dark:text-background font-black shadow-xs transition-transform group-hover:scale-105">
              <Sparkles className="size-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-base sm:text-lg font-black tracking-tight text-foreground flex items-center gap-1.5">
                PARAKH
                <span className="text-xs font-mono uppercase tracking-wider text-foreground-secondary px-1.5 py-0.5 rounded-full bg-surface-elevated border border-border">
                  Registration
                </span>
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle Theme"
              className="flex items-center justify-center size-8 rounded-full bg-surface-elevated border border-border text-foreground-secondary hover:text-foreground hover:bg-surface-highlight transition-colors cursor-pointer"
            >
              {isDark ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
            </button>
            <Link href="/login?role=applicant">
              <Button variant="ghost" size="sm" className="text-xs sm:text-sm text-foreground-secondary hover:text-foreground">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Form Content */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-6">
          <AuthFormCard status={authStatus} shakeKey={shakeKey}>
            <div className="space-y-1 mb-6">
              <div className="flex items-center justify-between">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">Create Applicant Account</h1>
                <Badge variant="secondary" className="text-xs">
                  Applicant Portal
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
                Connect your gig platform streams and unlock fair, volatility-aware alternative credit evaluation.
              </p>
            </div>

            {/* Error / Success Feedback Alert */}
            <AuthAlert
              status={authStatus}
              error={error}
              successMessage="Applicant registration verified. Establishing workspace session..."
            />

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-foreground-secondary">Full Legal Name</label>
                <div className="relative">
                  <User className="size-4 text-foreground-secondary absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <Input
                    type="text"
                    placeholder="e.g. Arjun Verma"
                    value={fullName}
                    onChange={handleInputChange(setFullName)}
                    className={cn(
                      'pl-9 text-sm h-10 bg-background text-foreground placeholder:text-foreground-muted',
                      getAuthInputClassName(authStatus)
                    )}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-foreground-secondary">Mobile Number or Email</label>
                <div className="relative">
                  <Mail className="size-4 text-foreground-secondary absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <Input
                    type="text"
                    placeholder="e.g. +91 98765 43210 or arjun@example.com"
                    value={emailOrPhone}
                    onChange={handleInputChange(setEmailOrPhone)}
                    className={cn(
                      'pl-9 text-sm h-10 bg-background text-foreground placeholder:text-foreground-muted',
                      getAuthInputClassName(authStatus)
                    )}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs sm:text-sm font-medium text-foreground-secondary">Password</label>
                  <div className="relative">
                    <Lock className="size-4 text-foreground-secondary absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <Input
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={handleInputChange(setPassword)}
                      className={cn(
                        'pl-9 text-sm h-10 bg-background text-foreground placeholder:text-foreground-muted',
                        getAuthInputClassName(authStatus)
                      )}
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs sm:text-sm font-medium text-foreground-secondary">Confirm</label>
                  <div className="relative">
                    <Lock className="size-4 text-foreground-secondary absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <Input
                      type="password"
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={handleInputChange(setConfirmPassword)}
                      className={cn(
                        'pl-9 text-sm h-10 bg-background text-foreground placeholder:text-foreground-muted',
                        getAuthInputClassName(authStatus)
                      )}
                    />
                  </div>
                </div>
              </div>

              {/* Consent Checkbox */}
              <div className="pt-2">
                <label className="flex items-start gap-2.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary size-4 mt-0.5 accent-primary"
                  />
                  <span className="text-xs sm:text-sm text-foreground-secondary leading-normal">
                    I consent to PARAKH securely ingesting verified platform activity for alternative credit assessment,
                    governed under RBI alternative data guidelines.
                  </span>
                </label>
              </div>

              <AuthSubmitButton
                status={authStatus}
                disabled={isSubmitting}
                idleText="Complete Applicant Registration"
                submittingText="Creating Account..."
                successText="Registration Verified"
              />
            </form>

            <div className="mt-6 pt-4 border-t border-border text-center">
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Already registered?{' '}
                <Link
                  href="/login?role=applicant"
                  className="font-semibold text-[#472393] hover:text-[#3B1B7A] dark:text-foreground hover:underline underline-offset-4"
                >
                  Sign in here
                </Link>
              </p>
            </div>
          </AuthFormCard>

          {/* Institutional Credit Reviewer Note */}
          <div className="rounded-2xl border border-border bg-surface-elevated p-4 text-center">
            <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
              Institutional Credit Reviewer access is restricted to licensed underwriting officers. Accounts are
              provisioned directly by enterprise risk desks.
            </p>
          </div>
        </div>
      </main>

      <footer className="relative z-10 w-full border-t border-border py-4 text-center">
        <p className="text-xs sm:text-sm text-foreground-secondary">
          © 2026 PARAKH Protocol • Financial Inclusion for India&apos;s 15 Million Gig Workers
        </p>
      </footer>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full flex items-center justify-center bg-background text-foreground">
          <div className="flex items-center gap-2 text-xs font-mono text-foreground-muted">
            <Sparkles className="size-4 animate-spin text-foreground" />
            Loading registration station...
          </div>
        </div>
      }
    >
      <SignupFormContent />
    </Suspense>
  );
}
