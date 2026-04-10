/**
 * Auth service — email + Google sign-in backed by a lightweight
 * localStorage token store.
 *
 * For production replace the fetch calls with your real auth backend
 * (Supabase, Firebase, Clerk, etc.). The interface is intentionally
 * backend-agnostic — swap the _callApi helpers below.
 *
 * Auth state shape:
 *   { user: { id, email, name, avatar } | null, status: 'loading'|'guest'|'authenticated' }
 */

const AUTH_KEY = 'maya_auth_v1';

// ── Persistence ────────────────────────────────────────────────

function saveAuth(user) {
  try {
    localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  } catch (_) {}
}

function loadAuth() {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function clearAuth() {
  try {
    localStorage.removeItem(AUTH_KEY);
  } catch (_) {}
}

// ── Public API ─────────────────────────────────────────────────

/**
 * Returns persisted user or null.
 */
export function getPersistedUser() {
  return loadAuth();
}

/**
 * Sign in with email + password (or magic-link token).
 * Replace with real backend call.
 */
export async function signInWithEmail(email, password) {
  const baseUrl = import.meta.env.VITE_AUTH_BASE_URL;
  if (!baseUrl) {
    throw new Error('VITE_AUTH_BASE_URL is not set. Configure your auth backend.');
  }
  const resp = await fetch(`${baseUrl}/auth/signin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.message || 'Sign-in failed.');
  }
  const data = await resp.json();
  const user = {
    id: data.user?.id || data.id,
    email: data.user?.email || email,
    name: data.user?.name || data.user?.email || email,
    avatar: data.user?.avatar || null,
    token: data.access_token || data.token,
  };
  saveAuth(user);
  return user;
}

/**
 * Initiate Google OAuth flow.
 * Redirects to the backend OAuth URL; on return the backend should
 * redirect to /auth/callback?token=... which you intercept in handleOAuthCallback.
 */
export function initiateGoogleSignIn() {
  const baseUrl = import.meta.env.VITE_AUTH_BASE_URL;
  if (!baseUrl) {
    throw new Error('VITE_AUTH_BASE_URL is not set.');
  }
  const callbackUrl = encodeURIComponent(`${window.location.origin}/auth/callback`);
  window.location.href = `${baseUrl}/auth/google?redirect_uri=${callbackUrl}`;
}

/**
 * Handle OAuth callback — call this on the /auth/callback page/route.
 * Reads ?token= from the URL, validates, stores, returns user.
 */
export async function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (!token) throw new Error('No token in OAuth callback.');

  const baseUrl = import.meta.env.VITE_AUTH_BASE_URL;
  const resp = await fetch(`${baseUrl}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error('Failed to fetch user from token.');
  const data = await resp.json();
  const user = {
    id: data.id,
    email: data.email,
    name: data.name || data.email,
    avatar: data.avatar || null,
    token,
  };
  saveAuth(user);
  return user;
}

/**
 * Sign out — clears local auth state.
 */
export function signOut() {
  clearAuth();
}
