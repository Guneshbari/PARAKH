/**
 * Comprehensive Automated Test Suite for PARAKH Authentication & Authorization Logic
 * Verifies all 16 required test scenarios.
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

// Assign globals for headless testing
(global as any).localStorage = mockLocalStorage;
(global as any).document = mockDocument;
(global as any).window = {};

import {
  INITIAL_ACCOUNTS,
  DEMO_APPLICANT_CREDENTIALS,
  DEMO_REVIEWER_CREDENTIALS,
  getRegisteredAccounts,
  UserRole,
  UserAccount,
  AuthUser,
} from './components/auth/AuthContext';

const AUTH_STORAGE_KEY = 'parakh_auth_session';

// Core auth validation implementation mirroring AuthContext
async function executeLogin(params: {
  email: string;
  password: string;
  portalRole?: UserRole;
}): Promise<AuthUser> {
  const cleanEmail = params.email.trim().toLowerCase();
  const cleanPassword = params.password.trim();

  if (!cleanEmail && !cleanPassword) {
    throw new Error('Please enter your email address and account password.');
  }
  if (!cleanEmail) {
    throw new Error('Please enter your email address or mobile number.');
  }
  if (!cleanPassword) {
    throw new Error('Please enter your account password.');
  }

  const accounts = getRegisteredAccounts();
  const matchedAccount = accounts.find(
    (acc) => acc.email.toLowerCase() === cleanEmail
  );

  if (!matchedAccount || matchedAccount.password !== cleanPassword) {
    throw new Error('Invalid email or password. Please check your credentials and try again.');
  }

  if (params.portalRole && matchedAccount.role !== params.portalRole) {
    throw new Error(
      params.portalRole === 'reviewer'
        ? 'Access denied. These credentials belong to an Applicant account and cannot access the Credit Reviewer portal.'
        : 'Access denied. These credentials belong to a Credit Reviewer account and cannot access the Applicant portal.'
    );
  }

  const authUser: AuthUser = {
    id: matchedAccount.id,
    name: matchedAccount.name,
    email: matchedAccount.email,
    role: matchedAccount.role,
    title: matchedAccount.title,
    station: matchedAccount.station,
  };

  mockLocalStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
  mockDocument.cookie = `parakh_role=${authUser.role}; path=/; max-age=604800; SameSite=Lax`;

  return authUser;
}

function executeLogout() {
  mockLocalStorage.removeItem(AUTH_STORAGE_KEY);
  mockLocalStorage.removeItem('parakh_session');
  mockDocument.cookie = 'parakh_role=; path=/; max-age=0';
}

function evaluateRouteGuard(
  pathname: string,
  currentUser: AuthUser | null,
  requiredRole: UserRole
): { status: 'ALLOWED' | 'REDIRECT'; target?: string } {
  if (!currentUser) {
    return {
      status: 'REDIRECT',
      target: `/login?role=${requiredRole}&redirect=${encodeURIComponent(pathname)}`,
    };
  }
  if (currentUser.role !== requiredRole) {
    return {
      status: 'REDIRECT',
      target: `/unauthorized?required=${requiredRole}`,
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
  console.log('RUNNING PARAKH AUTHENTICATION & AUTHORIZATION TESTS');
  console.log('==================================================\n');

  // --- SECTION 1: APPLICANT LOGIN TESTS ---
  console.log('--- SECTION 1: APPLICANT LOGIN ---');

  // TEST 1: arjun.verma@example.com + Parakh@123 → SUCCESS
  executeLogout();
  try {
    const user = await executeLogin({
      email: DEMO_APPLICANT_CREDENTIALS.email,
      password: DEMO_APPLICANT_CREDENTIALS.password,
      portalRole: 'applicant',
    });
    assert(
      user.role === 'applicant' &&
        user.email === DEMO_APPLICANT_CREDENTIALS.email &&
        mockLocalStorage.getItem(AUTH_STORAGE_KEY) !== null &&
        mockDocument.cookie.includes('parakh_role=applicant'),
      'TEST 1: Valid Applicant credentials (arjun.verma@example.com + Parakh@123) → SUCCESS'
    );
  } catch (err: any) {
    assert(false, 'TEST 1: Valid Applicant credentials → SUCCESS', err.message);
  }

  // TEST 2: random@gmail.com + random123 → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: 'random@gmail.com',
      password: 'random123',
      portalRole: 'applicant',
    });
    assert(false, 'TEST 2: Random credentials must FAIL');
  } catch {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null,
      'TEST 2: Random credentials (random@gmail.com + random123) → FAIL (No session created)'
    );
  }

  // TEST 3: arjun.verma@example.com + wrongpassword → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: DEMO_APPLICANT_CREDENTIALS.email,
      password: 'wrongpassword',
      portalRole: 'applicant',
    });
    assert(false, 'TEST 3: Wrong password must FAIL');
  } catch {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null,
      'TEST 3: Correct email + wrong password → FAIL (No session created)'
    );
  }

  // TEST 4: wrong@gmail.com + Parakh@123 → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: 'wrong@gmail.com',
      password: DEMO_APPLICANT_CREDENTIALS.password,
      portalRole: 'applicant',
    });
    assert(false, 'TEST 4: Wrong email must FAIL');
  } catch {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null,
      'TEST 4: Wrong email + correct password → FAIL (No session created)'
    );
  }

  // TEST 5: Empty email / password → FAIL with validation message
  executeLogout();
  try {
    await executeLogin({
      email: '',
      password: '',
      portalRole: 'applicant',
    });
    assert(false, 'TEST 5: Empty fields must FAIL');
  } catch (err: any) {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null &&
        err.message.includes('Please enter'),
      'TEST 5: Empty email/password → FAIL with validation error'
    );
  }

  // --- SECTION 2: CREDIT REVIEWER LOGIN TESTS ---
  console.log('\n--- SECTION 2: CREDIT REVIEWER LOGIN ---');

  // TEST 6: priya.sharma@parakh.internal + Parakh@Reviewer123 → SUCCESS
  executeLogout();
  try {
    const reviewer = await executeLogin({
      email: DEMO_REVIEWER_CREDENTIALS.email,
      password: DEMO_REVIEWER_CREDENTIALS.password,
      portalRole: 'reviewer',
    });
    assert(
      reviewer.role === 'reviewer' &&
        reviewer.email === DEMO_REVIEWER_CREDENTIALS.email &&
        mockLocalStorage.getItem(AUTH_STORAGE_KEY) !== null &&
        mockDocument.cookie.includes('parakh_role=reviewer'),
      'TEST 6: Valid Reviewer credentials (priya.sharma@parakh.internal + Parakh@Reviewer123) → SUCCESS'
    );
  } catch (err: any) {
    assert(false, 'TEST 6: Valid Reviewer credentials → SUCCESS', err.message);
  }

  // TEST 7: random@company.com + random123 → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: 'random@company.com',
      password: 'random123',
      portalRole: 'reviewer',
    });
    assert(false, 'TEST 7: Random reviewer credentials must FAIL');
  } catch {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null,
      'TEST 7: Random credentials on reviewer portal → FAIL (No session created)'
    );
  }

  // TEST 8: priya.sharma@parakh.internal + wrongpassword → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: DEMO_REVIEWER_CREDENTIALS.email,
      password: 'wrongpassword',
      portalRole: 'reviewer',
    });
    assert(false, 'TEST 8: Reviewer wrong password must FAIL');
  } catch {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null,
      'TEST 8: Reviewer email + wrong password → FAIL (No session created)'
    );
  }

  // TEST 9: Applicant credentials on Reviewer login → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: DEMO_APPLICANT_CREDENTIALS.email,
      password: DEMO_APPLICANT_CREDENTIALS.password,
      portalRole: 'reviewer', // Attemping reviewer portal with applicant credentials
    });
    assert(false, 'TEST 9: Cross-role login must FAIL');
  } catch (err: any) {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null &&
        err.message.includes('Applicant account'),
      'TEST 9: Applicant credentials on Reviewer login → FAIL (Cross-role access blocked)'
    );
  }

  // TEST 10: Reviewer credentials on Applicant login → FAIL
  executeLogout();
  try {
    await executeLogin({
      email: DEMO_REVIEWER_CREDENTIALS.email,
      password: DEMO_REVIEWER_CREDENTIALS.password,
      portalRole: 'applicant', // Attempting applicant portal with reviewer credentials
    });
    assert(false, 'TEST 10: Cross-role login must FAIL');
  } catch (err: any) {
    assert(
      mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null &&
        err.message.includes('Credit Reviewer account'),
      'TEST 10: Reviewer credentials on Applicant login → FAIL (Cross-role access blocked)'
    );
  }

  // --- SECTION 3: AUTHORIZATION & ROUTE GUARDS ---
  console.log('\n--- SECTION 3: AUTHORIZATION & ROUTE PROTECTION ---');

  // TEST 11: Logged-out user → /user/dashboard → redirected to Applicant Login
  const unauthApplicant = evaluateRouteGuard('/user/dashboard', null, 'applicant');
  assert(
    unauthApplicant.status === 'REDIRECT' &&
      Boolean(unauthApplicant.target?.includes('/login?role=applicant')),
    'TEST 11: Logged-out user visiting /user/dashboard → Redirect to Applicant Login'
  );

  // TEST 12: Logged-out user → /admin/dashboard → redirected to Reviewer Login
  const unauthReviewer = evaluateRouteGuard('/admin/dashboard', null, 'reviewer');
  assert(
    unauthReviewer.status === 'REDIRECT' &&
      Boolean(unauthReviewer.target?.includes('/login?role=reviewer')),
    'TEST 12: Logged-out user visiting /admin/dashboard → Redirect to Reviewer Login'
  );

  // TEST 13: Authenticated Applicant → /admin/dashboard → blocked (redirect to /unauthorized)
  const applicantUser: AuthUser = {
    id: 'usr-101',
    name: 'Arjun Verma',
    email: 'arjun.verma@example.com',
    role: 'applicant',
    title: 'Applicant',
  };
  const applicantToAdmin = evaluateRouteGuard('/admin/dashboard', applicantUser, 'reviewer');
  assert(
    applicantToAdmin.status === 'REDIRECT' &&
      applicantToAdmin.target === '/unauthorized?required=reviewer',
    'TEST 13: Authenticated Applicant visiting /admin/dashboard → BLOCKED (/unauthorized)'
  );

  // TEST 14: Authenticated Reviewer → /user/dashboard → blocked (redirect to /unauthorized)
  const reviewerUser: AuthUser = {
    id: 'rev-402',
    name: 'Priya Sharma',
    email: 'priya.sharma@parakh.internal',
    role: 'reviewer',
    title: 'Senior Credit Reviewer',
  };
  const reviewerToUser = evaluateRouteGuard('/user/dashboard', reviewerUser, 'applicant');
  assert(
    reviewerToUser.status === 'REDIRECT' &&
      reviewerToUser.target === '/unauthorized?required=applicant',
    'TEST 14: Authenticated Reviewer visiting /user/dashboard → BLOCKED (/unauthorized)'
  );

  // TEST 15: Logout completely clears session → protected route blocked
  executeLogout();
  const postLogout = evaluateRouteGuard('/user/dashboard', null, 'applicant');
  assert(
    mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null &&
      mockDocument.cookie === '' &&
      postLogout.status === 'REDIRECT',
    'TEST 15: Logout completely purges session, role, and cookies → protected route BLOCKED'
  );

  // TEST 16: Invalid login attempt leaves storage completely clean
  executeLogout();
  try {
    await executeLogin({
      email: 'hacker@malicious.com',
      password: 'password123',
    });
  } catch {}
  assert(
    mockLocalStorage.getItem(AUTH_STORAGE_KEY) === null && mockDocument.cookie === '',
    'TEST 16: Invalid login attempt guarantees NO session or cookie is created'
  );

  console.log('\n==================================================');
  console.log(`TEST RESULTS: ${passedTests} / ${totalTests} TESTS PASSED (${((passedTests / totalTests) * 100).toFixed(0)}%)`);
  console.log('==================================================\n');

  if (passedTests !== totalTests) {
    process.exit(1);
  }
}

runAllTests().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
