/**
 * StartupScreen — shown at app start when prior sessions exist.
 *
 * Offers: Continue [session], Start New, or Sign In.
 * Matches the premium dark luxury theme.
 */

function formatDate(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

const STAGE_LABELS = {
  session:        'Planning in progress',
  review:         'Ready to review',
  hall_selection: 'Selecting hall',
  visualization:  'Visualizing',
  export:         'Completed',
};

export default function StartupScreen({ sessions, onContinue, onNew, onSignIn, user }) {
  const hasSessions = sessions && sessions.length > 0;

  return (
    <>
      <div className="ambient-bg">
        <div className="ambient-bg__glow ambient-bg__glow--gold" />
        <div className="ambient-bg__glow ambient-bg__glow--purple" />
      </div>

      <div className="startup-screen">
        <div className="startup-card">
          {/* Header */}
          <div className="startup-header">
            <div className="startup-logo">Maya</div>
            <p className="startup-sub">South Indian Wedding Planner</p>
          </div>

          {hasSessions ? (
            <>
              <div className="startup-section-label">Continue where you left off</div>

              <div className="startup-sessions">
                {sessions.slice(0, 4).map(s => (
                  <button
                    key={s.id}
                    className="startup-session-row"
                    onClick={() => onContinue(s)}
                  >
                    <div className="startup-session-info">
                      <div className="startup-session-name">
                        {s.customName || s.autoName}
                      </div>
                      <div className="startup-session-meta">
                        {STAGE_LABELS[s.stage] || s.stage} · {formatDate(s.updatedAt)}
                      </div>
                    </div>
                    <span className="startup-session-arrow">→</span>
                  </button>
                ))}
              </div>

              <div className="startup-divider"><span>or</span></div>
            </>
          ) : (
            <p className="startup-welcome">
              Plan your perfect South Indian wedding hall decoration with Maya.
              Speak your vision and get a complete styled preview.
            </p>
          )}

          <button className="btn-gold startup-new-btn" onClick={onNew}>
            {hasSessions ? 'Start a New Session' : '🎤 Begin Planning'}
          </button>

          {!user && (
            <button className="startup-signin-btn" onClick={onSignIn}>
              Sign in to save sessions to your account
            </button>
          )}

          {user && (
            <div className="startup-user-badge">
              Signed in as {user.name || user.email}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
