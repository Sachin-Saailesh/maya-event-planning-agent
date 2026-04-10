import { useState, useCallback, useEffect } from 'react';
import {
  getPersistedUser,
  signInWithEmail,
  initiateGoogleSignIn,
  signOut as _signOut,
} from '../services/auth.js';
import { migrateAllGuestSessions } from '../services/sessionStorage.js';

/**
 * Auth state hook.
 *
 * status: 'loading' | 'guest' | 'authenticated'
 * user: { id, email, name, avatar } | null
 * error: string | null
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);

  // Restore persisted session on mount
  useEffect(() => {
    const persisted = getPersistedUser();
    if (persisted?.id) {
      setUser(persisted);
      setStatus('authenticated');
    } else {
      setStatus('guest');
    }
  }, []);

  const signInEmail = useCallback(async (email, password) => {
    setError(null);
    try {
      const u = await signInWithEmail(email, password);
      setUser(u);
      setStatus('authenticated');
      migrateAllGuestSessions(u.id);
      return u;
    } catch (err) {
      setError(err.message || 'Sign-in failed.');
      throw err;
    }
  }, []);

  const signInGoogle = useCallback(() => {
    setError(null);
    try {
      initiateGoogleSignIn();
    } catch (err) {
      setError(err.message || 'Google sign-in unavailable.');
    }
  }, []);

  const signOut = useCallback(() => {
    _signOut();
    setUser(null);
    setStatus('guest');
    setError(null);
  }, []);

  return { user, status, error, signInEmail, signInGoogle, signOut };
}
