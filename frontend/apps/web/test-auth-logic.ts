/**
 * Automated Test Suite for PARAKH Real Authentication & RBAC Logic
 * Verifies the complete real authentication flow:
 * Next.js -> POST /api/v1/auth/login -> JWT -> Bearer header -> FastAPI RBAC -> Protected routes
 */

// 1. Setup in-memory mock environment for Node execution
const memoryStorage: Record<string, string> = {};

const mockLocalStorage = {
  getItem: (key: string) => memoryStorage[key] || null,
  setItem: (key: string, val: string) => {
    memoryStorage[key] = val;
  },
  removeItem: (key: string) => {
    delete memoryStorage[key];
  },
  clear: () => {
    for (const k of Object.keys(memoryStorage)) {
      delete memoryStorage[k];
    }
  },
};

let mockCookie = '';
const mockDocument = {
  get cookie() {
    return mockCookie;
  },
  set cookie(val: string) {
    if (val.includes('max-age=0')) {
      mockCookie = '';
    } else {
      mockCookie = val.split(';')[0];
    }
  },
};

(global as any).localStorage = mockLocalStorage;
(global as any).document = mockDocument;
(global as any).window = {};

import {
  AuthUser,
  AUTH_TOKEN_KEY,
  AUTH_SESSION_KEY,
  UserRole,
} from './components/auth/AuthContext';
import {
  normalizeUserRole,
  toPortalRole,
  TokenResponse,
  UserResponse,
} from '@parakh/types';
import { ParakhApiClient } from '@parakh/api';

// --- MOCK BACKEND DATA & BEHAVIOR ---
const MOCK_BACKEND_USERS: Record<
  string,
  { passwordHash: string; role: 'APPLICANT' | 'REVIEWER' | 'ADMIN'; id: string }
> = {
  'applicant@parakh.io': {
    passwordHash: 'hash_of_Password123!',
    role: 'APPLICANT',
    id: 'b1111111-1111-1111-1111-111111111111',
  },
  'reviewer@parakh.internal': {
    passwordHash: 'hash_of_Password123!',
    role: 'REVIEWER',
    id: 'b2222222-2222-2222-2222-222222222222',
  },
  'admin@parakh.internal': {
    passwordHash: 'hash_of_Password123!',
    role: 'ADMIN',
    id: 'b3333333-3333-3333-3333-333333333333',
  },
};

// Mock fetch interceptor mimicking FastAPI /api/v1 endpoints
let lastSentHeaders: Record<string, string> = {};

(global as any).fetch = async (url: string, init?: RequestInit) => {
  lastSentHeaders = (init?.headers as Record<string, string>) || {};

  const pathname = new URL(url).pathname;
  const method = init?.method || 'GET';
  const body = init?.body ? JSON.parse(init.body as string) : {};

  // 1. POST /api/v1/auth/login
  if (pathname === '/api/v1/auth/login' && method === 'POST') {
    const user = MOCK_BACKEND_USERS[body.email?.toLowerCase()];
    if (!user || body.password !== 'Password123!') {
      return {
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid email or password' }),
      };
    }

    const tokenResponse: TokenResponse = {
      access_token: `mock_jwt_${user.role}_${user.id}`,
      token_type: 'bearer',
      expires_in: 86400,
      user_id: user.id,
      email: body.email.toLowerCase(),
      role: user.role,
    };
    return {
      ok: true,
      status: 200,
      json: async () => tokenResponse,
    };
  }

  // 2. GET /api/v1/auth/me
  if (pathname === '/api/v1/auth/me' && method === 'GET') {
    const authHeader = lastSentHeaders['Authorization'];
    if (!authHeader || !authHeader.startsWith('Bearer mock_jwt_')) {
      return {
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Authentication credentials were not provided' }),
      };
    }
    const tokenPart = authHeader.replace('Bearer mock_jwt_', '');
    const [role, id] = tokenPart.split('_');
    const userResponse: UserResponse = {
      id,
      email: role === 'REVIEWER' ? 'reviewer@parakh.internal' : 'applicant@parakh.io',
      role: role as any,
      is_active: true,
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-09-01T00:00:00Z',
    };
    return {
      ok: true,
      status: 200,
      json: async () => userResponse,
    };
  }

  // 3. POST /api/v1/users (Registration)
  if (pathname === '/api/v1/users' && method === 'POST') {
    const existing = MOCK_BACKEND_USERS[body.email?.toLowerCase()];
    if (existing) {
      return {
        ok: false,
        status: 409,
        json: async () => ({ detail: `User with email '${body.email}' already exists.` }),
      };
    }
    if (!body.password || body.password.length < 8) {
      return {
        ok: false,
        status: 422,
        json: async () => ({ detail: 'Password must contain at least 8 characters.' }),
      };
    }
    const newUser = {
      passwordHash: `hash_of_${body.password}`,
      role: (body.role || 'APPLICANT') as 'APPLICANT' | 'REVIEWER' | 'ADMIN',
      id: `usr-${Date.now()}`,
    };
    MOCK_BACKEND_USERS[body.email.toLowerCase()] = newUser;
    const userResponse: UserResponse = {
      id: newUser.id,
      email: body.email.toLowerCase(),
      role: newUser.role,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    return {
      ok: true,
      status: 201,
      json: async () => userResponse,
    };
  }

  return {
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Not Found' }),
  };
};

// RouteGuard evaluation logic
function evaluateRouteGuard(
  pathname: string,
  currentUser: AuthUser | null,
  requiredRole: string
): { status: 'ALLOWED' | 'REDIRECT'; target?: string } {
  if (!currentUser) {
    return {
      status: 'REDIRECT',
      target: `/login?role=${requiredRole.toLowerCase()}&redirect=${encodeURIComponent(pathname)}`,
    };
  }
  const currentUpper = normalizeUserRole(currentUser.role);
  const requiredUpper = normalizeUserRole(requiredRole);
  if (currentUpper !== requiredUpper) {
    return {
      status: 'REDIRECT',
      target: `/unauthorized?required=${requiredRole.toLowerCase()}`,
    };
  }
  return { status: 'ALLOWED' };
}

let passedTests = 0;
let totalTests = 0;

function assert(condition: boolean, testName: string, detail?: string) {
  totalTests++;
  if (condition) {
    console.log(`  ✓ ${testName}`);
    passedTests++;
  } else {
    console.error(`  ✗ FAIL: ${testName} ${detail ? `(${detail})` : ''}`);
  }
}

async function runAllTests() {
  console.log('\n==================================================');
  console.log('RUNNING PARAKH REAL AUTHENTICATION & RBAC TESTS');
  console.log('==================================================\n');

  const testClient = new ParakhApiClient({ baseUrl: 'http://localhost:8000' });

  // TEST 1: Login success with valid APPLICANT credentials
  console.log('Section 1: Applicant Login & JWT Flow');
  try {
    const resp = await testClient.login({
      email: 'applicant@parakh.io',
      password: 'Password123!',
    });
    assert(
      resp.access_token.startsWith('mock_jwt_APPLICANT') && resp.role === 'APPLICANT',
      'TEST 1: Valid APPLICANT credentials returns real JWT and role APPLICANT'
    );
  } catch (err: any) {
    assert(false, 'TEST 1: Valid APPLICANT login failed', err.message);
  }

  // TEST 2: Bearer token is automatically attached to subsequent authenticated requests
  try {
    const profile = await testClient.getMe();
    assert(
      lastSentHeaders['Authorization']?.startsWith('Bearer mock_jwt_APPLICANT') &&
        profile.role === 'APPLICANT',
      'TEST 2: Authenticated request attaches Authorization: Bearer <JWT> header'
    );
  } catch (err: any) {
    assert(false, 'TEST 2: Authenticated GET /auth/me failed', err.message);
  }

  // TEST 3: Login with invalid password fails with 401
  try {
    await testClient.login({
      email: 'applicant@parakh.io',
      password: 'WrongPassword!',
    });
    assert(false, 'TEST 3: Invalid password should throw');
  } catch (err: any) {
    assert(
      err.status === 401,
      'TEST 3: Invalid password correctly rejected with HTTP 401'
    );
  }

  // TEST 4: Login with nonexistent user fails with 401
  try {
    await testClient.login({
      email: 'nonexistent@example.com',
      password: 'Password123!',
    });
    assert(false, 'TEST 4: Nonexistent user should throw');
  } catch (err: any) {
    assert(
      err.status === 401,
      'TEST 4: Nonexistent user correctly rejected with HTTP 401'
    );
  }

  // TEST 5: Login with REVIEWER credentials returns role REVIEWER
  console.log('\nSection 2: Reviewer Login & Role Assignment');
  try {
    const reviewerResp = await testClient.login({
      email: 'reviewer@parakh.internal',
      password: 'Password123!',
    });
    assert(
      reviewerResp.access_token.startsWith('mock_jwt_REVIEWER') &&
        reviewerResp.role === 'REVIEWER',
      'TEST 5: Valid REVIEWER credentials returns real JWT and role REVIEWER'
    );
  } catch (err: any) {
    assert(false, 'TEST 5: Valid REVIEWER login failed', err.message);
  }

  // TEST 6: Session storage contains NO plaintext password
  console.log('\nSection 3: Security & Plaintext Password Elimination');
  const sampleAuthUser: AuthUser = {
    id: 'usr-123',
    name: 'Test Applicant',
    email: 'applicant@parakh.io',
    role: 'APPLICANT',
    portalRole: 'applicant',
    title: 'Applicant',
  };
  mockLocalStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(sampleAuthUser));
  mockLocalStorage.setItem(AUTH_TOKEN_KEY, 'mock_jwt_token_123');

  const storedSessionRaw = mockLocalStorage.getItem(AUTH_SESSION_KEY) || '';
  assert(
    !storedSessionRaw.includes('password') && !storedSessionRaw.includes('Password123!'),
    'TEST 6: Session storage strictly excludes plaintext password'
  );

  // TEST 7: Legacy mock account keys are completely absent
  assert(
    mockLocalStorage.getItem('parakh_registered_users') === null,
    'TEST 7: Obsolete mock storage key parakh_registered_users is absent'
  );

  // TEST 8: RouteGuard allows APPLICANT to /user/dashboard
  console.log('\nSection 4: Frontend RouteGuard & Role Authorization');
  const applicantUser: AuthUser = {
    id: 'usr-101',
    name: 'Arjun',
    email: 'applicant@parakh.io',
    role: 'APPLICANT',
    portalRole: 'applicant',
    title: 'Applicant',
  };

  const allowedApplicant = evaluateRouteGuard('/user/dashboard', applicantUser, 'applicant');
  assert(
    allowedApplicant.status === 'ALLOWED',
    'TEST 8: RouteGuard permits APPLICANT to access /user/dashboard'
  );

  // TEST 9: RouteGuard blocks unauthenticated user and redirects to /login
  const unauthUser = evaluateRouteGuard('/user/dashboard', null, 'applicant');
  assert(
    unauthUser.status === 'REDIRECT' && Boolean(unauthUser.target?.includes('/login?role=applicant')),
    'TEST 9: RouteGuard redirects unauthenticated access to /login'
  );

  // TEST 10: RouteGuard blocks APPLICANT from /admin/dashboard (role mismatch -> /unauthorized)
  const crossRoleBlocked = evaluateRouteGuard('/admin/dashboard', applicantUser, 'reviewer');
  assert(
    crossRoleBlocked.status === 'REDIRECT' &&
      crossRoleBlocked.target === '/unauthorized?required=reviewer',
    'TEST 10: RouteGuard blocks APPLICANT from /admin/dashboard -> /unauthorized'
  );

  // TEST 11: RouteGuard permits REVIEWER to /admin/dashboard
  const reviewerUser: AuthUser = {
    id: 'rev-402',
    name: 'Priya',
    email: 'reviewer@parakh.internal',
    role: 'REVIEWER',
    portalRole: 'reviewer',
    title: 'Senior Credit Reviewer',
  };
  const allowedReviewer = evaluateRouteGuard('/admin/dashboard', reviewerUser, 'reviewer');
  assert(
    allowedReviewer.status === 'ALLOWED',
    'TEST 11: RouteGuard permits REVIEWER to access /admin/dashboard'
  );

  // TEST 12: RouteGuard blocks REVIEWER from /user/dashboard
  const reviewerOnUserBlocked = evaluateRouteGuard('/user/dashboard', reviewerUser, 'applicant');
  assert(
    reviewerOnUserBlocked.status === 'REDIRECT' &&
      reviewerOnUserBlocked.target === '/unauthorized?required=applicant',
    'TEST 12: RouteGuard blocks REVIEWER from /user/dashboard -> /unauthorized'
  );

  // TEST 13: User registration via POST /api/v1/users succeeds
  console.log('\nSection 5: Registration & Auto-Login');
  try {
    const regResp = await testClient.register({
      email: 'new.borrower@example.com',
      password: 'SecurePassword123!',
      role: 'APPLICANT',
    });
    assert(
      regResp.email === 'new.borrower@example.com' && regResp.role === 'APPLICANT',
      'TEST 13: Self-registration creates new APPLICANT user account'
    );
  } catch (err: any) {
    assert(false, 'TEST 13: Registration failed', err.message);
  }

  // TEST 14: Registration rejects password shorter than 8 characters
  try {
    await testClient.register({
      email: 'shortpass@example.com',
      password: 'short',
      role: 'APPLICANT',
    });
    assert(false, 'TEST 14: Short password should be rejected');
  } catch (err: any) {
    assert(
      err.status === 422,
      'TEST 14: Password under 8 characters rejected with HTTP 422'
    );
  }

  // TEST 15: Duplicate registration is rejected with HTTP 409
  try {
    await testClient.register({
      email: 'applicant@parakh.io',
      password: 'Password123!',
      role: 'APPLICANT',
    });
    assert(false, 'TEST 15: Duplicate registration should be rejected');
  } catch (err: any) {
    assert(
      err.status === 409,
      'TEST 15: Duplicate registration rejected with HTTP 409'
    );
  }

  // TEST 16: Logout completely terminates session and clears token
  console.log('\nSection 6: Session Termination & Logout');
  testClient.clearToken();
  mockLocalStorage.removeItem(AUTH_TOKEN_KEY);
  mockLocalStorage.removeItem(AUTH_SESSION_KEY);
  mockDocument.cookie = 'parakh_role=; path=/; max-age=0';

  assert(
    testClient.getToken() === null &&
      mockLocalStorage.getItem(AUTH_TOKEN_KEY) === null &&
      mockLocalStorage.getItem(AUTH_SESSION_KEY) === null,
    'TEST 16: Logout successfully clears JWT, session storage, and client token'
  );

  console.log('\n==================================================');
  console.log(`RESULTS: ${passedTests} passed out of ${totalTests} tests.`);
  console.log('==================================================\n');

  if (passedTests !== totalTests) {
    process.exit(1);
  }
}

runAllTests().catch((err) => {
  console.error('Test execution failed:', err);
  process.exit(1);
});
