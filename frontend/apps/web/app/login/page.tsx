'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Sparkles,
  ShieldCheck,
  User,
  Lock,
  Mail,
  ArrowRight,
  Sun,
  Moon,
  Info,
  CheckCircle2,
  AlertCircle,
  KeyRound,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/components/theme/ThemeProvider';
import { cn } from '@/lib/utils';
import {
  useAuth,
  UserRole,
  DEMO_APPLICANT,
  DEMO_REVIEWER,
  DEMO_APPLICANT_CREDENTIALS,
  DEMO_REVIEWER_CREDENTIALS,
} from '@/components/auth/AuthContext';
import {
  AuthFormCard,
  AuthSubmitButton,
  AuthAlert,
  getAuthInputClassName,
  AuthStatus,
} from '@/components/auth/AuthFeedback';

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialRole = (searchParams.get('role') as UserRole) || 'applicant';
  const redirectUrl = searchParams.get('redirect');

  const [activeRole, setActiveRole] = useState<UserRole>(
    initialRole === 'reviewer' ? 'reviewer' : 'applicant'
  );
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus>('idle');
  const [shakeKey, setShakeKey] = useState(0);

  const { isDark, toggleTheme } = useTheme();
  const { login, isAuthenticated, role: userRole } = useAuth();

  // If already authenticated in current role, redirect immediately
  useEffect(() => {
    if (isAuthenticated) {
      if (userRole === 'reviewer') {
        router.push(redirectUrl || '/admin/dashboard');
      } else if (userRole === 'applicant') {
        router.push(redirectUrl || '/user/dashboard');
      }
    }
  }, [isAuthenticated, userRole, redirectUrl, router]);

  // Sync role when URL param changes
  useEffect(() => {
    const roleParam = searchParams.get('role');
    if (roleParam === 'reviewer' || roleParam === 'applicant') {
      setActiveRole(roleParam);
      setError(null);
      setAuthStatus('idle');
    }
  }, [searchParams]);

  // Reset error state when typing (ensures no shake or error border while typing)
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

    if (!email.trim() && !password.trim()) {
      setError('Please enter your email/mobile and account password.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }
    if (!email.trim()) {
      setError('Please enter your email address or mobile number.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }
    if (!password.trim()) {
      setError('Please enter your account password.');
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      return;
    }

    setAuthStatus('submitting');
    setIsSubmitting(true);

    try {
      const authUser = await login({
        email,
        password,
        portalRole: activeRole,
      });

      // Verification passed!
      setAuthStatus('success');
      setError(null);

      // Brief 400ms confirmation window to showcase "Credentials Verified" check ring
      setTimeout(() => {
        if (authUser.role === 'reviewer') {
          router.push(redirectUrl || '/admin/dashboard');
        } else {
          router.push(redirectUrl || '/user/dashboard');
        }
      }, 400);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Invalid email or password. Please check your credentials and try again.';
      setError(msg);
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      setIsSubmitting(false);
    }
  };

  const handleFillDemo = (role: UserRole) => {
    setError(null);
    setAuthStatus('idle');
    if (role === 'applicant') {
      setEmail(DEMO_APPLICANT_CREDENTIALS.email);
      setPassword(DEMO_APPLICANT_CREDENTIALS.password);
      setActiveRole('applicant');
    } else {
      setEmail(DEMO_REVIEWER_CREDENTIALS.email);
      setPassword(DEMO_REVIEWER_CREDENTIALS.password);
      setActiveRole('reviewer');
    }
  };

  const handleDemoLogin = async (role: UserRole) => {
    setError(null);
    const demoEmail =
      role === 'applicant'
        ? DEMO_APPLICANT_CREDENTIALS.email
        : DEMO_REVIEWER_CREDENTIALS.email;
    const demoPassword =
      role === 'applicant'
        ? DEMO_APPLICANT_CREDENTIALS.password
        : DEMO_REVIEWER_CREDENTIALS.password;

    // Populate UI fields
    setEmail(demoEmail);
    setPassword(demoPassword);
    setActiveRole(role);

    setAuthStatus('submitting');
    setIsSubmitting(true);

    try {
      // Explicitly route through standard credential validation
      const authUser = await login({
        email: demoEmail,
        password: demoPassword,
        portalRole: role,
      });

      setAuthStatus('success');
      setError(null);

      setTimeout(() => {
        if (authUser.role === 'reviewer') {
          router.push(redirectUrl || '/admin/dashboard');
        } else {
          router.push(redirectUrl || '/user/dashboard');
        }
      }, 400);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Demo authentication failed.';
      setError(msg);
      setAuthStatus('error');
      setShakeKey((k) => k + 1);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex flex-col justify-between bg-background text-foreground transition-colors duration-200 overflow-x-hidden">
      {/* Subtle Background Silk Line Motifs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-35 dark:opacity-20">
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-gradient-to-br from-blue-400/20 to-indigo-500/10 blur-3xl" />
        <div className="absolute top-1/2 -right-32 w-96 h-96 rounded-full bg-gradient-to-bl from-purple-400/15 to-transparent blur-3xl" />
        <svg
          className="absolute inset-0 w-full h-full stroke-foreground/[0.04] dark:stroke-white/[0.04]"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M-100,100 C300,50 600,250 1200,150 S1800,400 2400,200" fill="none" strokeWidth="1" />
          <path d="M-100,250 C400,180 700,400 1300,280 S1700,500 2400,380" fill="none" strokeWidth="1" />
        </svg>
      </div>

      {/* Top Header Bar */}
      <header className="relative z-10 w-full border-b border-border bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#472393] text-white dark:bg-foreground dark:text-background font-black shadow-xs transition-transform group-hover:scale-105">
              <Sparkles className="size-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-black tracking-tight text-foreground flex items-center gap-1.5">
                PARAKH
                <span className="text-[10px] font-mono uppercase tracking-wider text-foreground-muted px-1.5 py-0.2 rounded-full bg-surface-elevated border border-border">
                  Access Control
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
            <Link href="/">
              <Button variant="ghost" size="sm" className="text-xs text-foreground-secondary hover:text-foreground">
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Authentication Container */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-6">
          {/* Role Switcher Pills */}
          <div className="flex p-1 rounded-2xl bg-surface-elevated border border-border shadow-xs">
            <button
              type="button"
              onClick={() => {
                setActiveRole('applicant');
                setError(null);
              }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                activeRole === 'applicant'
                  ? 'bg-[#472393] text-white shadow-xs dark:bg-surface dark:text-foreground dark:border dark:border-border'
                  : 'text-foreground-secondary hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
              }`}
            >
              <User className="size-3.5" />
              <span>Applicant Portal</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveRole('reviewer');
                setError(null);
              }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                activeRole === 'reviewer'
                  ? 'bg-[#472393] text-white shadow-xs dark:bg-surface dark:text-foreground dark:border dark:border-border'
                  : 'text-foreground-secondary hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
              }`}
            >
              <ShieldCheck className="size-3.5" />
              <span>Credit Reviewer</span>
            </button>
          </div>

          {/* Form Card */}
          <AuthFormCard status={authStatus} shakeKey={shakeKey}>
            {/* Header copy */}
            <div className="space-y-1 mb-6">
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  {activeRole === 'applicant' ? 'Applicant Sign In' : 'Credit Reviewer Authentication'}
                </h1>
                <Badge variant={activeRole === 'applicant' ? 'secondary' : 'default'} className="text-[10px]">
                  {activeRole === 'applicant' ? 'Public Access' : 'Institutional'}
                </Badge>
              </div>
              <p className="text-xs text-foreground-secondary leading-relaxed">
                {activeRole === 'applicant'
                  ? 'Access your alternative credit assessments, verification status, and profile.'
                  : 'Certified fiduciary workstation. Session actions are logged and cryptographically audited.'}
              </p>
            </div>

            {/* Error / Success Feedback Alert */}
            <AuthAlert
              status={authStatus}
              error={error}
              successMessage="Credentials verified. Redirecting to workspace..."
            />

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground-secondary">
                  {activeRole === 'applicant' ? 'Mobile Number or Email' : 'Enterprise Work Email'}
                </label>
                <div className="relative">
                  <Mail className="size-4 text-foreground-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <Input
                    type="text"
                    placeholder={
                      activeRole === 'applicant' ? 'e.g. arjun.verma@example.com' : 'name@parakh.internal'
                    }
                    value={email}
                    onChange={handleInputChange(setEmail)}
                    className={cn(
                      'pl-9 text-xs h-10 bg-background text-foreground placeholder:text-foreground-muted',
                      getAuthInputClassName(authStatus)
                    )}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-foreground-secondary">Password</label>
                  <button
                    type="button"
                    onClick={() => setError('Password reset instructions will be sent to verified contact.')}
                    className="text-[11px] text-foreground-muted hover:text-foreground transition-colors cursor-pointer"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="size-4 text-foreground-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <Input
                    type="password"
                    placeholder="••••••••••••"
                    value={password}
                    onChange={handleInputChange(setPassword)}
                    className={cn(
                      'pl-9 text-xs h-10 bg-background text-foreground placeholder:text-foreground-muted',
                      getAuthInputClassName(authStatus)
                    )}
                  />
                </div>
              </div>

              {/* MFA Field for Reviewer */}
              {activeRole === 'reviewer' && (
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-foreground-secondary flex items-center gap-1">
                      <KeyRound className="size-3 text-foreground-muted" /> Security Token / MFA Code
                    </label>
                    <span className="text-[10px] text-foreground-muted">Station 04 Required</span>
                  </div>
                  <Input
                    type="text"
                    placeholder="6-digit authenticator code (optional in demo)"
                    value={mfaCode}
                    onChange={handleInputChange(setMfaCode)}
                    maxLength={6}
                    className={cn(
                      'text-xs h-10 font-mono tracking-widest bg-background text-foreground placeholder:text-foreground-muted',
                      getAuthInputClassName(authStatus)
                    )}
                  />
                </div>
              )}

              {/* Remember checkbox */}
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary size-3.5 accent-primary"
                  />
                  <span className="text-xs text-foreground-secondary">Remember session</span>
                </label>
              </div>

              {/* Submit Button with Animated Verification State */}
              <AuthSubmitButton
                status={authStatus}
                disabled={isSubmitting}
                idleText={
                  activeRole === 'applicant'
                    ? 'Sign In to Applicant Portal'
                    : 'Authenticate as Credit Reviewer'
                }
                submittingText={
                  activeRole === 'applicant'
                    ? 'Verifying Applicant Credentials...'
                    : 'Verifying Reviewer Credentials...'
                }
                successText="Credentials Verified"
              />
            </form>

            {/* Bottom Links */}
            <div className="mt-6 pt-4 border-t border-border text-center">
              {activeRole === 'applicant' ? (
                <p className="text-xs text-foreground-secondary">
                  Don&apos;t have an Applicant account?{' '}
                  <Link
                    href="/signup?role=applicant"
                    className="font-semibold text-[#472393] hover:text-[#3B1B7A] dark:text-foreground hover:underline underline-offset-4"
                  >
                    Create Applicant Account
                  </Link>
                </p>
              ) : (
                <p className="text-[11px] text-foreground-muted leading-relaxed">
                  Notice: Credit Reviewer credentials are strictly issued and managed by enterprise risk administration.
                  Public registration is disabled by policy.
                </p>
              )}
            </div>
          </AuthFormCard>

          {/* ==========================================================
              ⚡ HACKATHON DEMO MODE: ONE-CLICK EVALUATOR SIGN-IN
              ========================================================== */}
          <div className="rounded-2xl border border-border bg-surface-elevated p-4 sm:p-5 shadow-xs space-y-3 transition-colors duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex h-5 w-5 items-center justify-center rounded-md bg-[#472393] text-white dark:bg-foreground dark:text-background text-[10px] font-black">
                  ⚡
                </div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-foreground">
                  Demo Mode • Pre-provisioned Credentials
                </h2>
              </div>
              <Badge variant="outline" className="text-[9px] font-mono">
                Validated Auth
              </Badge>
            </div>
            <p className="text-[11px] text-foreground-secondary leading-relaxed">
              For evaluation convenience, you can test authentication using the prototype&apos;s registered demo credentials.
              All actions pass through strict credential and role verification.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
              {/* Applicant Demo Card */}
              <div className="flex flex-col justify-between p-3 rounded-xl border border-border bg-surface text-left space-y-2">
                <div>
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs font-bold text-foreground">
                      Applicant Demo
                    </span>
                    <Badge variant="outline" className="text-[9px] py-0 px-1.5">
                      User
                    </Badge>
                  </div>
                  <p className="text-[11px] text-foreground-secondary mt-1 font-medium">
                    {DEMO_APPLICANT.name}
                  </p>
                  <div className="text-[10px] font-mono text-foreground-muted space-y-0.5 mt-1 bg-surface-highlight/50 p-1.5 rounded-md border border-border">
                    <div><span className="text-foreground-secondary">Email:</span> {DEMO_APPLICANT_CREDENTIALS.email}</div>
                    <div><span className="text-foreground-secondary">Pass:</span> {DEMO_APPLICANT_CREDENTIALS.password}</div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 pt-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleFillDemo('applicant')}
                    className="flex-1 text-[10px] h-7 px-2"
                  >
                    Fill Form
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleDemoLogin('applicant')}
                    disabled={isSubmitting}
                    className="flex-1 text-[10px] h-7 px-2 font-semibold"
                  >
                    Sign In
                  </Button>
                </div>
              </div>

              {/* Reviewer Demo Card */}
              <div className="flex flex-col justify-between p-3 rounded-xl border border-border bg-surface text-left space-y-2">
                <div>
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs font-bold text-foreground">
                      Credit Reviewer Demo
                    </span>
                    <Badge variant="outline" className="text-[9px] py-0 px-1.5">
                      Reviewer
                    </Badge>
                  </div>
                  <p className="text-[11px] text-foreground-secondary mt-1 font-medium">
                    {DEMO_REVIEWER.name}
                  </p>
                  <div className="text-[10px] font-mono text-foreground-muted space-y-0.5 mt-1 bg-surface-highlight/50 p-1.5 rounded-md border border-border">
                    <div><span className="text-foreground-secondary">Email:</span> {DEMO_REVIEWER_CREDENTIALS.email}</div>
                    <div><span className="text-foreground-secondary">Pass:</span> {DEMO_REVIEWER_CREDENTIALS.password}</div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 pt-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleFillDemo('reviewer')}
                    className="flex-1 text-[10px] h-7 px-2"
                  >
                    Fill Form
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => handleDemoLogin('reviewer')}
                    disabled={isSubmitting}
                    className="flex-1 text-[10px] h-7 px-2 font-semibold"
                  >
                    Authenticate
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Institutional Footer */}
      <footer className="relative z-10 w-full border-t border-border py-4 text-center">
        <p className="text-[11px] text-foreground-muted">
          © 2026 PARAKH Protocol • Volatility-Aware Credit Intelligence • Human Fiduciary Governance
        </p>
      </footer>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full flex items-center justify-center bg-background text-foreground">
          <div className="flex items-center gap-2 text-xs font-mono text-foreground-muted">
            <Sparkles className="size-4 animate-spin text-foreground" />
            Loading authentication station...
          </div>
        </div>
      }
    >
      <LoginFormContent />
    </Suspense>
  );
}
