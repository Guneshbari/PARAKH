'use client';

/**
 * PARAKH Real Authentication Context
 * Connects frontend sessions to FastAPI JWT backend (/api/v1/auth/login, /api/v1/auth/me, /api/v1/users).
 *
 * Security Architecture & Tradeoffs:
 * - JWT Access Token is persisted in localStorage under 'parakh_auth_token'.
 *   Tradeoff: Storing tokens in localStorage is susceptible to XSS if third-party scripts execute in the browser.
 *   In production, httpOnly SameSite cookies via an API proxy are recommended.
 * - Sensitive credentials (passwords) are NEVER persisted in localStorage or session storage.
 * - User identity and RBAC role ('APPLICANT' | 'REVIEWER' | 'ADMIN') are verified by FastAPI on every session initialization.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@parakh/api';
import {
  UserRole as CanonicalUserRole,
  PortalRole,
  normalizeUserRole,
  toPortalRole,
  UserResponse,
} from '@parakh/types';

export type BackendUserRole = CanonicalUserRole;
export type UserRole = BackendUserRole | PortalRole;

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: BackendUserRole;
  portalRole: PortalRole;
  title: string;
  station?: string;
}

export interface LoginParams {
  email: string;
  password: string;
  portalRole?: string;
}

export interface SignupParams {
  name: string;
  email: string;
  password: string;
  confirmPassword?: string;
  consent?: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  role: BackendUserRole | null;
  portalRole: PortalRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    paramsOrEmail: LoginParams | string,
    maybePassword?: string,
    maybePortalRole?: string
  ) => Promise<AuthUser>;
  signup: (
    paramsOrName: SignupParams | string,
    maybeEmail?: string,
    maybePassword?: string,
    maybeConfirmPassword?: string,
    maybeConsent?: boolean
  ) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  role: null,
  portalRole: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {
    throw new Error('AuthProvider not mounted');
  },
  signup: async () => {
    throw new Error('AuthProvider not mounted');
  },
  logout: () => {},
});

// Storage keys
export const AUTH_TOKEN_KEY = 'parakh_auth_token';
export const AUTH_SESSION_KEY = 'parakh_auth_session';

function setSessionCookie(role: PortalRole | BackendUserRole | null) {
  if (typeof document === 'undefined') return;
  if (role) {
    const portal = typeof role === 'string' ? role.toLowerCase() : '';
    document.cookie = `parakh_role=${portal}; path=/; max-age=86400; SameSite=Lax`;
  } else {
    document.cookie = 'parakh_role=; path=/; max-age=0; SameSite=Lax';
  }
}

function deriveDisplayName(email: string, role: BackendUserRole): string {
  if (!email) return role === 'REVIEWER' ? 'Credit Reviewer' : 'Applicant';
  const prefix = email.split('@')[0];
  const parts = prefix.split(/[._-]/).filter(Boolean);
  if (parts.length > 0) {
    return parts.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
  }
  return role === 'REVIEWER' ? 'Credit Reviewer' : 'Applicant';
}

function deriveTitle(role: BackendUserRole): string {
  switch (role) {
    case 'REVIEWER':
      return 'Senior Credit Reviewer';
    case 'ADMIN':
      return 'System Administrator';
    case 'APPLICANT':
    default:
      return 'Applicant';
  }
}

function formatUserFromResponse(res: UserResponse, storedName?: string): AuthUser {
  const portal = toPortalRole(res.role) || 'applicant';
  return {
    id: res.id,
    email: res.email,
    role: res.role,
    portalRole: portal,
    name: storedName || deriveDisplayName(res.email, res.role),
    title: deriveTitle(res.role),
    station: res.role === 'REVIEWER' ? 'Desk 04 • Tier-1 Institutional Review' : undefined,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load session from FastAPI on initial mount using stored JWT
  useEffect(() => {
    let isMounted = true;

    async function initializeSession() {
      if (typeof window === 'undefined') {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
        if (!storedToken) {
          api.clearToken();
          if (isMounted) {
            setUser(null);
            setSessionCookie(null);
          }
          return;
        }

        // Attach stored JWT to API client
        api.setToken(storedToken);

        // Fetch current active user profile from backend /api/v1/auth/me
        try {
          const profile = await api.getMe();
          if (!isMounted) return;

          // Retrieve cached name if available
          let cachedName: string | undefined;
          try {
            const cachedSession = localStorage.getItem(AUTH_SESSION_KEY);
            if (cachedSession) {
              const parsed = JSON.parse(cachedSession);
              cachedName = parsed.name;
            }
          } catch {}

          const authUser = formatUserFromResponse(profile, cachedName);
          setUser(authUser);
          localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(authUser));
          setSessionCookie(authUser.role);
        } catch (err: unknown) {
          if (!isMounted) return;
          // Status 401: Token invalid or expired -> purge session
          const status = (err as { status?: number })?.status;
          if (status === 401) {
            api.clearToken();
            localStorage.removeItem(AUTH_TOKEN_KEY);
            localStorage.removeItem(AUTH_SESSION_KEY);
            localStorage.removeItem('parakh_session');
            setUser(null);
            setSessionCookie(null);
          } else {
            // Backend unreachable (e.g. temporary network offline): check cached session
            try {
              const cached = localStorage.getItem(AUTH_SESSION_KEY);
              if (cached) {
                const parsed: AuthUser = JSON.parse(cached);
                setUser(parsed);
                setSessionCookie(parsed.role);
              } else {
                setUser(null);
                setSessionCookie(null);
              }
            } catch {
              setUser(null);
              setSessionCookie(null);
            }
          }
        }
      } catch {
        if (isMounted) {
          setUser(null);
          setSessionCookie(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    initializeSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(
    async (
      paramsOrEmail: LoginParams | string,
      maybePassword?: string,
      maybePortalRole?: string
    ): Promise<AuthUser> => {
      setIsLoading(true);

      let email = '';
      let password = '';
      let portalRole: string | undefined;

      if (typeof paramsOrEmail === 'object' && paramsOrEmail !== null) {
        email = paramsOrEmail.email || '';
        password = paramsOrEmail.password || '';
        portalRole = paramsOrEmail.portalRole;
      } else {
        email = paramsOrEmail || '';
        password = maybePassword || '';
        portalRole = maybePortalRole;
      }

      const cleanEmail = email.trim().toLowerCase();
      const cleanPassword = password.trim();

      if (!cleanEmail && !cleanPassword) {
        setIsLoading(false);
        throw new Error('Please enter your email address and account password.');
      }
      if (!cleanEmail) {
        setIsLoading(false);
        throw new Error('Please enter your email address.');
      }
      if (!cleanPassword) {
        setIsLoading(false);
        throw new Error('Please enter your account password.');
      }

      try {
        // Authenticate with real FastAPI endpoint: POST /api/v1/auth/login
        const tokenResp = await api.login({
          email: cleanEmail,
          password: cleanPassword,
        });

        // Verify that account role aligns with portal role if specified
        if (portalRole) {
          const expectedBackendRole = normalizeUserRole(portalRole);
          if (expectedBackendRole && tokenResp.role !== expectedBackendRole) {
            api.clearToken();
            setIsLoading(false);
            throw new Error(
              portalRole.toLowerCase() === 'reviewer'
                ? 'Access denied. These credentials belong to an Applicant account and cannot access the Credit Reviewer portal.'
                : 'Access denied. These credentials belong to a Credit Reviewer account and cannot access the Applicant portal.'
            );
          }
        }

        const authUser: AuthUser = {
          id: tokenResp.user_id,
          email: tokenResp.email,
          role: tokenResp.role,
          portalRole: toPortalRole(tokenResp.role) || 'applicant',
          name: deriveDisplayName(tokenResp.email, tokenResp.role),
          title: deriveTitle(tokenResp.role),
          station: tokenResp.role === 'REVIEWER' ? 'Desk 04 • Tier-1 Institutional Review' : undefined,
        };

        setUser(authUser);
        if (typeof window !== 'undefined') {
          localStorage.setItem(AUTH_TOKEN_KEY, tokenResp.access_token);
          localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(authUser));
          // Clean legacy mock keys
          localStorage.removeItem('parakh_registered_users');
          localStorage.removeItem('parakh_session');
        }
        setSessionCookie(authUser.role);
        setIsLoading(false);
        return authUser;
      } catch (err: unknown) {
        setIsLoading(false);
        const status = (err as { status?: number })?.status;
        if (status === 401) {
          throw new Error('Invalid email or password. Please check your credentials and try again.');
        }
        if (status === 403) {
          throw new Error('Account is inactive or access forbidden. Contact system administrator.');
        }
        if (err instanceof Error) {
          throw err;
        }
        throw new Error('Authentication request failed. Please check network connection.');
      }
    },
    []
  );

  const signup = useCallback(
    async (
      paramsOrName: SignupParams | string,
      maybeEmail?: string,
      maybePassword?: string,
      maybeConfirmPassword?: string,
      maybeConsent?: boolean
    ): Promise<AuthUser> => {
      setIsLoading(true);

      let name = '';
      let email = '';
      let password = '';
      let confirmPassword = '';
      let consent = true;

      if (typeof paramsOrName === 'object' && paramsOrName !== null) {
        name = paramsOrName.name || '';
        email = paramsOrName.email || '';
        password = paramsOrName.password || '';
        confirmPassword = paramsOrName.confirmPassword || paramsOrName.password || '';
        consent = paramsOrName.consent ?? true;
      } else {
        name = paramsOrName || '';
        email = maybeEmail || '';
        password = maybePassword || '';
        confirmPassword = maybeConfirmPassword || maybePassword || '';
        consent = maybeConsent ?? true;
      }

      const cleanName = name.trim();
      const cleanEmail = email.trim().toLowerCase();
      const cleanPassword = password.trim();

      if (!cleanName) {
        setIsLoading(false);
        throw new Error('Please enter your full legal name.');
      }
      if (!cleanEmail || !cleanEmail.includes('@')) {
        setIsLoading(false);
        throw new Error('Please enter a valid email address.');
      }
      if (!cleanPassword || cleanPassword.length < 8) {
        setIsLoading(false);
        throw new Error('Password must contain at least 8 characters.');
      }
      if (cleanPassword !== confirmPassword.trim()) {
        setIsLoading(false);
        throw new Error('Passwords do not match. Please re-enter.');
      }
      if (!consent) {
        setIsLoading(false);
        throw new Error('You must accept the alternative credit evaluation terms and data consent.');
      }

      try {
        // Register user via backend API: POST /api/v1/users
        await api.register({
          email: cleanEmail,
          password: cleanPassword,
          role: 'APPLICANT',
        });

        // Immediately authenticate with newly created account: POST /api/v1/auth/login
        const tokenResp = await api.login({
          email: cleanEmail,
          password: cleanPassword,
        });

        const authUser: AuthUser = {
          id: tokenResp.user_id,
          email: tokenResp.email,
          role: tokenResp.role,
          portalRole: 'applicant',
          name: cleanName,
          title: 'Applicant',
        };

        setUser(authUser);
        if (typeof window !== 'undefined') {
          localStorage.setItem(AUTH_TOKEN_KEY, tokenResp.access_token);
          localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(authUser));
          localStorage.removeItem('parakh_registered_users');
          localStorage.removeItem('parakh_session');
        }
        setSessionCookie('applicant');
        setIsLoading(false);
        return authUser;
      } catch (err: unknown) {
        setIsLoading(false);
        const status = (err as { status?: number })?.status;
        const respData = (err as { responseData?: unknown })?.responseData;
        const errDetail =
          typeof respData === 'object' && respData !== null
            ? (respData as { detail?: string }).detail
            : undefined;

        if (status === 409 || (errDetail && String(errDetail).toLowerCase().includes('already exists'))) {
          throw new Error('An account with this email address already exists. Please sign in.');
        }
        if (errDetail) {
          throw new Error(String(errDetail));
        }
        if (err instanceof Error) {
          throw err;
        }
        throw new Error('Registration failed. Please verify your details and try again.');
      }
    },
    []
  );

  const logout = useCallback(() => {
    api.clearToken();
    setUser(null);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_SESSION_KEY);
      localStorage.removeItem('parakh_session');
      localStorage.removeItem('parakh_registered_users');
    }
    setSessionCookie(null);
    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user ? user.role : null,
        portalRole: user ? user.portalRole : null,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
