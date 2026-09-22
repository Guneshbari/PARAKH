'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

export type UserRole = 'applicant' | 'reviewer';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  title: string;
  station?: string;
}

export interface UserAccount {
  id: string;
  name: string;
  email: string;
  password: string;
  role: UserRole;
  title: string;
  station?: string;
}

export const DEMO_APPLICANT_CREDENTIALS = {
  email: 'arjun.verma@example.com',
  password: 'Parakh@123',
};

export const DEMO_REVIEWER_CREDENTIALS = {
  email: 'priya.sharma@parakh.internal',
  password: 'Parakh@Reviewer123',
};

export const INITIAL_ACCOUNTS: UserAccount[] = [
  {
    id: 'usr-101',
    name: 'Arjun Verma',
    email: DEMO_APPLICANT_CREDENTIALS.email,
    password: DEMO_APPLICANT_CREDENTIALS.password,
    role: 'applicant',
    title: 'Applicant',
  },
  {
    id: 'rev-402',
    name: 'Priya Sharma',
    email: DEMO_REVIEWER_CREDENTIALS.email,
    password: DEMO_REVIEWER_CREDENTIALS.password,
    role: 'reviewer',
    title: 'Senior Credit Reviewer',
    station: 'Desk 04 • Tier-1 Institutional Review',
  },
];

export const DEMO_APPLICANT: AuthUser = {
  id: 'usr-101',
  name: 'Arjun Verma',
  email: DEMO_APPLICANT_CREDENTIALS.email,
  role: 'applicant',
  title: 'Applicant',
};

export const DEMO_REVIEWER: AuthUser = {
  id: 'rev-402',
  name: 'Priya Sharma',
  email: DEMO_REVIEWER_CREDENTIALS.email,
  role: 'reviewer',
  title: 'Senior Credit Reviewer',
  station: 'Desk 04 • Tier-1 Institutional Review',
};

export interface LoginParams {
  email: string;
  password: string;
  portalRole?: UserRole;
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
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    paramsOrEmail: LoginParams | string,
    maybePassword?: string,
    maybePortalRole?: UserRole
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

const AUTH_STORAGE_KEY = 'parakh_auth_session';
const REGISTERED_ACCOUNTS_KEY = 'parakh_registered_users';

export function getRegisteredAccounts(): UserAccount[] {
  if (typeof window === 'undefined') return INITIAL_ACCOUNTS;
  try {
    const raw = localStorage.getItem(REGISTERED_ACCOUNTS_KEY);
    if (!raw) return INITIAL_ACCOUNTS;
    const parsed: UserAccount[] = JSON.parse(raw);
    return [...INITIAL_ACCOUNTS, ...parsed];
  } catch {
    return INITIAL_ACCOUNTS;
  }
}

function setSessionCookie(role: UserRole | null) {
  if (typeof document === 'undefined') return;
  if (role) {
    document.cookie = `parakh_role=${role}; path=/; max-age=604800; SameSite=Lax`;
  } else {
    document.cookie = 'parakh_role=; path=/; max-age=0; SameSite=Lax';
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load session from localStorage on initial mount and verify integrity
  useEffect(() => {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        const parsed: AuthUser = JSON.parse(stored);
        const accounts = getRegisteredAccounts();
        const matched = accounts.find(
          (acc) =>
            acc.id === parsed.id &&
            acc.email.toLowerCase() === parsed.email.toLowerCase() &&
            acc.role === parsed.role
        );
        if (matched) {
          setUser(parsed);
          setSessionCookie(parsed.role);
        } else {
          // Stale or invalid session - clear it
          localStorage.removeItem(AUTH_STORAGE_KEY);
          localStorage.removeItem('parakh_session');
          setUser(null);
          setSessionCookie(null);
        }
      } else {
        setSessionCookie(null);
      }
    } catch {
      setSessionCookie(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(
    async (
      paramsOrEmail: LoginParams | string,
      maybePassword?: string,
      maybePortalRole?: UserRole
    ): Promise<AuthUser> => {
      setIsLoading(true);

      // Normalize parameters
      let email = '';
      let password = '';
      let portalRole: UserRole | undefined;

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

      // Simulate brief network delay for credential verification
      await new Promise((resolve) => setTimeout(resolve, 250));

      // 1. Mandatory field checks
      if (!cleanEmail && !cleanPassword) {
        setIsLoading(false);
        throw new Error('Please enter your email address and account password.');
      }
      if (!cleanEmail) {
        setIsLoading(false);
        throw new Error('Please enter your email address or mobile number.');
      }
      if (!cleanPassword) {
        setIsLoading(false);
        throw new Error('Please enter your account password.');
      }

      // 2. Query registered accounts
      const accounts = getRegisteredAccounts();
      const matchedAccount = accounts.find(
        (acc) => acc.email.toLowerCase() === cleanEmail
      );

      // 3. Credential verification (must match both account existence and exact password)
      if (!matchedAccount || matchedAccount.password !== cleanPassword) {
        setIsLoading(false);
        // Non-sensitive error: do not reveal whether email exists or password was wrong
        throw new Error('Invalid email or password. Please check your credentials and try again.');
      }

      // 4. Role verification: ensure credentials match the portal portalRole if specified
      if (portalRole && matchedAccount.role !== portalRole) {
        setIsLoading(false);
        throw new Error(
          portalRole === 'reviewer'
            ? 'Access denied. These credentials belong to an Applicant account and cannot access the Credit Reviewer portal.'
            : 'Access denied. These credentials belong to a Credit Reviewer account and cannot access the Applicant portal.'
        );
      }

      // 5. Success! ONLY create authenticated session after successful validation
      const authUser: AuthUser = {
        id: matchedAccount.id,
        name: matchedAccount.name,
        email: matchedAccount.email,
        role: matchedAccount.role,
        title: matchedAccount.title,
        station: matchedAccount.station,
      };

      setUser(authUser);
      try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        localStorage.setItem('parakh_session', JSON.stringify(authUser));
      } catch {}
      setSessionCookie(authUser.role);
      setIsLoading(false);

      return authUser;
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

      await new Promise((resolve) => setTimeout(resolve, 300));

      const cleanName = name.trim();
      const cleanEmail = email.trim().toLowerCase();
      const cleanPassword = password.trim();

      if (!cleanName) {
        setIsLoading(false);
        throw new Error('Please enter your full legal name.');
      }
      if (!cleanEmail || (!cleanEmail.includes('@') && cleanEmail.length < 10)) {
        setIsLoading(false);
        throw new Error('Please enter a valid email address or mobile number.');
      }
      if (!cleanPassword || cleanPassword.length < 6) {
        setIsLoading(false);
        throw new Error('Password must contain at least 6 characters.');
      }
      if (cleanPassword !== confirmPassword.trim()) {
        setIsLoading(false);
        throw new Error('Passwords do not match. Please re-enter.');
      }
      if (!consent) {
        setIsLoading(false);
        throw new Error('You must accept the alternative credit evaluation terms and data consent.');
      }

      // Check for duplicate accounts
      const accounts = getRegisteredAccounts();
      const existing = accounts.find((acc) => acc.email.toLowerCase() === cleanEmail);
      if (existing) {
        setIsLoading(false);
        throw new Error('An account with this email or mobile number already exists. Please sign in.');
      }

      // Create new applicant account record (public signup is strictly applicant only)
      const newAccount: UserAccount = {
        id: `usr-${Date.now().toString().slice(-4)}`,
        name: cleanName,
        email: cleanEmail,
        password: cleanPassword,
        role: 'applicant',
        title: 'Applicant',
      };

      try {
        const raw = localStorage.getItem(REGISTERED_ACCOUNTS_KEY);
        const existingList: UserAccount[] = raw ? JSON.parse(raw) : [];
        existingList.push(newAccount);
        localStorage.setItem(REGISTERED_ACCOUNTS_KEY, JSON.stringify(existingList));
      } catch {}

      // Create authenticated session only after valid registration
      const authUser: AuthUser = {
        id: newAccount.id,
        name: newAccount.name,
        email: newAccount.email,
        role: newAccount.role,
        title: newAccount.title,
      };

      setUser(authUser);
      try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        localStorage.setItem('parakh_session', JSON.stringify(authUser));
      } catch {}
      setSessionCookie('applicant');
      setIsLoading(false);

      return authUser;
    },
    []
  );

  const logout = useCallback(() => {
    setUser(null);
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      localStorage.removeItem('parakh_session');
    } catch {}
    setSessionCookie(null);
    router.push('/');
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user ? user.role : null,
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
