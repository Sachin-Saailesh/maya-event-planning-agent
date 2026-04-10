import { useState, useCallback } from 'react';

/**
 * AuthModal — minimal email + Google sign-in modal.
 * Matches the premium dark luxury theme.
 */
export default function AuthModal({ onSignInEmail, onSignInGoogle, onClose, error }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  const handleEmail = useCallback(async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setLocalError('Please enter your email and password.');
      return;
    }
    setLocalError('');
    setSubmitting(true);
    try {
      await onSignInEmail(email.trim(), password);
    } catch (err) {
      setLocalError(err.message || 'Sign-in failed.');
    } finally {
      setSubmitting(false);
    }
  }, [email, password, onSignInEmail]);

  const displayError = localError || error;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>

        <div className="modal-header">
          <div className="modal-title">Sign in to Maya</div>
          <div className="modal-sub">Save and restore your planning sessions</div>
        </div>

        {/* Google */}
        <button className="auth-google-btn" onClick={onSignInGoogle}>
          <GoogleIcon />
          Continue with Google
        </button>

        <div className="auth-divider"><span>or</span></div>

        {/* Email form */}
        <form onSubmit={handleEmail} className="auth-form">
          <input
            className="auth-input"
            type="email"
            placeholder="Email address"
            value={email}
            onChange={e => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
          <input
            className="auth-input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {displayError && (
            <div className="auth-error">{displayError}</div>
          )}
          <button
            type="submit"
            className="btn-gold"
            disabled={submitting}
            style={{ width: '100%' }}
          >
            {submitting
              ? <span className="loading-dots"><span /><span /><span /></span>
              : 'Sign In'}
          </button>
        </form>

        <div className="auth-guest-note">
          You can also continue as a guest — your session will be saved locally.
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" style={{ flexShrink: 0 }}>
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z"/>
      <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"/>
    </svg>
  );
}
