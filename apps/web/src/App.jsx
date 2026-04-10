import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket.js';
import { useTTS } from './hooks/useTTS.js';
import { useLiveKit } from './hooks/useLiveKit.js';
import { useMicrophone } from './hooks/useMicrophone.js';
import { useAuth } from './hooks/useAuth.js';
import { useSavedSessions } from './hooks/useSavedSessions.js';
import VoiceSession from './components/VoiceSession.jsx';
import ReviewScreen from './components/ReviewScreen.jsx';
import HallSelection from './components/HallSelection.jsx';
import Visualization from './components/Visualization.jsx';
import ExportBrief from './components/ExportBrief.jsx';
import StartupScreen from './components/StartupScreen.jsx';
import AuthModal from './components/AuthModal.jsx';
import GenerationScreen from './components/GenerationScreen.jsx';
import SessionRename from './components/SessionRename.jsx';
import { getNextEmptySlot, getSlotProgress } from './slotConfig.js';
import { generateAndWait } from './services/imageGeneration.js';

/**
 * Maya — South Indian Wedding Decoration Planner
 *
 * Stage machine:
 *   startup → landing → session → review → hall_selection
 *   → generating → visualization → export
 */
export default function App() {
  // ── Auth ─────────────────────────────────────────────────────
  const { user, status: authStatus, error: authError, signInEmail, signInGoogle, signOut } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);

  // ── Session persistence ───────────────────────────────────────
  const {
    currentSession,
    recentSessions,
    createNewSession,
    restoreSession,
    updateSession,
    renameSession,
  } = useSavedSessions(user);

  // ── Stage machine ────────────────────────────────────────────
  // 'startup' until auth resolves; then 'landing' if no sessions
  const [stage, setStage] = useState('startup');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [selectedHall, setSelectedHall] = useState(null);

  // ── Image generation ─────────────────────────────────────────
  const [genStatus, setGenStatus] = useState('idle'); // idle | generating | complete | error
  const [genImageUrl, setGenImageUrl] = useState(null);
  const [genError, setGenError] = useState(null);

  // ── LiveKit ───────────────────────────────────────────────────
  const { connected: lkConnected, room, connect: lkConnect, disconnect: lkDisconnect } = useLiveKit(sessionId);

  // ── WebSocket ─────────────────────────────────────────────────
  const {
    connected,
    transcript,
    partialText,
    state,
    confirmation,
    latestPrompt,
    speechInterrupted,
    reviewProceedEvent,
    reviewModifySlotEvent,
    sendTranscript,
    sendStateUpdate,
    sendConfirmation,
    sendBargeIn,
    sendIdleTimeout,
  } = useWebSocket(sessionId);

  // ── TTS ───────────────────────────────────────────────────────
  const { speak, stop: stopTTS, isSpeaking, cancelForBargeIn, clearSpokenSentences } = useTTS();

  // ── Mic ───────────────────────────────────────────────────────
  const { micState, errorMessage: micErrorMessage, requestMic } = useMicrophone();

  const idleTimerRef = useRef(null);

  // Derived slot state
  const currentSlot = getNextEmptySlot(state);
  const slotsAllFilled = state != null && currentSlot === null;
  const slotProgress = getSlotProgress(state);

  // ── Startup: wait for auth, then decide initial stage ─────────
  useEffect(() => {
    if (authStatus === 'loading') return;
    if (stage !== 'startup') return;

    // If there are saved sessions, show startup picker
    if (recentSessions.length > 0) {
      setStage('startup_picker');
    } else {
      setStage('landing');
    }
  }, [authStatus, recentSessions.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Persist session state on every WS state update ────────────
  useEffect(() => {
    if (!sessionId || !state) return;
    updateSession({ state, stage, transcript });
  }, [state, stage]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Persist hall selection ─────────────────────────────────────
  useEffect(() => {
    if (selectedHall) updateSession({ selectedHall });
  }, [selectedHall]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Persist generated image ────────────────────────────────────
  useEffect(() => {
    if (genImageUrl) updateSession({ generatedImageUrl: genImageUrl });
  }, [genImageUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── TTS: speak Maya prompts ────────────────────────────────────
  useEffect(() => {
    if (!latestPrompt) return;
    clearSpokenSentences();
    speak(latestPrompt);

    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    if (!latestPrompt.startsWith('Are you still there?')) {
      idleTimerRef.current = setTimeout(() => sendIdleTimeout(), 60_000);
    }
  }, [latestPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Barge-in ──────────────────────────────────────────────────
  useEffect(() => {
    if (!speechInterrupted) return;
    const last = cancelForBargeIn();
    sendBargeIn(last);
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
  }, [speechInterrupted]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── WS review-stage signals ────────────────────────────────────
  useEffect(() => {
    if (!reviewProceedEvent) return;
    setStage('hall_selection');
  }, [reviewProceedEvent]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!reviewModifySlotEvent) return;
    setStage('session');
  }, [reviewModifySlotEvent]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Start session ─────────────────────────────────────────────
  const handleStartSession = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch('/session', { method: 'POST' });
      const data = await resp.json();
      if (data.livekit_token && data.livekit_url) {
        await lkConnect(data.livekit_token, data.livekit_url);
      }
      setSessionId(data.session_id);
      createNewSession(data.session_id, user?.id || null);
      setStage('session');
    } catch (err) {
      console.error('Failed to create session:', err);
      alert('Failed to connect to Maya. Make sure the orchestrator is running on port 8000.');
    } finally {
      setLoading(false);
    }
  }, [lkConnect, user, createNewSession]);

  // ── Resume session ────────────────────────────────────────────
  const handleContinueSession = useCallback((savedSession) => {
    restoreSession(savedSession.id);
    setSelectedHall(savedSession.selectedHall || null);
    if (savedSession.generatedImageUrl) {
      setGenImageUrl(savedSession.generatedImageUrl);
      setGenStatus('complete');
    }
    // We start a fresh WS session (server is in-memory; state restored visually)
    handleStartSession();
  }, [restoreSession, handleStartSession]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Text send ─────────────────────────────────────────────────
  const handleSendText = useCallback(() => {
    const text = inputText.trim();
    if (!text) return;
    if (isSpeaking) {
      const last = cancelForBargeIn();
      sendBargeIn(last);
    }
    sendTranscript(text, true);
    setInputText('');
  }, [inputText, sendTranscript, isSpeaking, cancelForBargeIn, sendBargeIn]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') handleSendText();
  }, [handleSendText]);

  // ── Option tile select ─────────────────────────────────────────
  const handleOptionSelect = useCallback((label) => {
    if (isSpeaking) {
      const last = cancelForBargeIn();
      sendBargeIn(last);
    }
    sendTranscript(label, true);
  }, [sendTranscript, isSpeaking, cancelForBargeIn, sendBargeIn]);

  // ── Navigation ────────────────────────────────────────────────
  const handleProceedToReview = useCallback(() => setStage('review'), []);
  const handleEditFromReview = useCallback(() => setStage('session'), []);
  const handleProceedToHall = useCallback(() => setStage('hall_selection'), []);

  const handleHallSelected = useCallback((hall) => {
    setSelectedHall(hall);
    setStage('visualization');
  }, []);

  const handleBackToReview = useCallback(() => setStage('review'), []);
  const handleChangeHall = useCallback(() => setStage('hall_selection'), []);
  const handleEditDecorFromViz = useCallback(() => setStage('session'), []);

  // ── Image generation ──────────────────────────────────────────
  const handleStartGeneration = useCallback(async () => {
    if (!state || !selectedHall) return;
    setGenStatus('generating');
    setGenError(null);
    setStage('generating');
    try {
      const result = await generateAndWait(state, selectedHall.id, ({ status }) => {
        // Could surface more granular status here if desired
        console.log('[GEN] status:', status);
      });
      setGenImageUrl(result.image_url);
      setGenStatus('complete');
    } catch (err) {
      setGenError(err.message || 'Image generation failed.');
      setGenStatus('error');
    }
  }, [state, selectedHall]);

  const handleRetryGeneration = useCallback(() => {
    handleStartGeneration();
  }, [handleStartGeneration]);

  const handleExportFromViz = useCallback(async () => {
    if (sessionId) {
      try {
        await fetch(`/session/${sessionId}/export`, { method: 'POST' });
      } catch (err) {
        console.error('Export call failed:', err);
      }
    }
    setStage('export');
  }, [sessionId]);

  const handleEndSession = useCallback(() => {
    stopTTS();
    lkDisconnect();
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    setSessionId(null);
    setStage('landing');
  }, [stopTTS, lkDisconnect]);

  // ── Auth actions ──────────────────────────────────────────────
  const handleSignInSuccess = useCallback(() => {
    setShowAuthModal(false);
  }, []);

  const handleSignInEmail = useCallback(async (email, password) => {
    await signInEmail(email, password);
    handleSignInSuccess();
  }, [signInEmail, handleSignInSuccess]);

  // ── Startup stage ─────────────────────────────────────────────
  if (stage === 'startup' || authStatus === 'loading') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="ambient-bg">
          <div className="ambient-bg__glow ambient-bg__glow--gold" />
          <div className="ambient-bg__glow ambient-bg__glow--purple" />
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <span className="loading-dots" style={{ display: 'flex', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)' }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)', animationDelay: '0.2s' }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--primary)', animationDelay: '0.4s' }} />
          </span>
        </div>
      </div>
    );
  }

  if (stage === 'startup_picker') {
    return (
      <>
        {showAuthModal && (
          <AuthModal
            onSignInEmail={handleSignInEmail}
            onSignInGoogle={signInGoogle}
            onClose={() => setShowAuthModal(false)}
            error={authError}
          />
        )}
        <StartupScreen
          sessions={recentSessions}
          onContinue={handleContinueSession}
          onNew={() => setStage('landing')}
          onSignIn={() => setShowAuthModal(true)}
          user={user}
        />
      </>
    );
  }

  // ── Landing ───────────────────────────────────────────────────
  if (stage === 'landing') {
    return (
      <>
        {showAuthModal && (
          <AuthModal
            onSignInEmail={handleSignInEmail}
            onSignInGoogle={signInGoogle}
            onClose={() => setShowAuthModal(false)}
            error={authError}
          />
        )}
        <div className="ambient-bg">
          <div className="ambient-bg__glow ambient-bg__glow--gold" />
          <div className="ambient-bg__glow ambient-bg__glow--purple" />
        </div>
        <div className="landing">
          <div className="landing__eyebrow">South Indian Wedding Planner</div>
          <div className="landing__logo">Maya</div>
          <p className="landing__subtitle">
            Your AI concierge for planning South Indian wedding hall decorations.
            Speak your vision and get a complete decoration brief.
          </p>
          <p className="landing__tagline">Powered by voice · Built for beauty</p>
          <button className="btn-gold" onClick={handleStartSession} disabled={loading}>
            {loading
              ? <span className="loading-dots"><span /><span /><span /></span>
              : '🎤 Begin Planning'}
          </button>
          {!user && (
            <button className="startup-signin-btn" style={{ marginTop: 16 }} onClick={() => setShowAuthModal(true)}>
              Sign in to save sessions
            </button>
          )}
        </div>
      </>
    );
  }

  // ── Export ────────────────────────────────────────────────────
  if (stage === 'export') {
    return (
      <ExportBrief
        state={state}
        hall={selectedHall}
        imageUrl={genImageUrl}
        onBack={() => setStage('visualization')}
      />
    );
  }

  // ── Generating ────────────────────────────────────────────────
  if (stage === 'generating' || (stage === 'visualization' && genStatus === 'generating')) {
    return (
      <GenerationScreen
        status={genStatus}
        imageUrl={genImageUrl}
        errorMessage={genError}
        hallName={selectedHall?.name || 'Wedding Hall'}
        onRetry={handleRetryGeneration}
        onEditDecor={handleEditDecorFromViz}
        onChangeHall={handleChangeHall}
      />
    );
  }

  // ── Visualization ─────────────────────────────────────────────
  if (stage === 'visualization') {
    return (
      <>
        <AppHeader
          connected={connected}
          isSpeaking={isSpeaking}
          slotProgress={slotProgress}
          stage="visualization"
          user={user}
          onSignIn={() => setShowAuthModal(true)}
          onSignOut={signOut}
        />
        <Visualization
          state={state}
          hall={selectedHall}
          generatedImageUrl={genImageUrl}
          onGenerate={handleStartGeneration}
          onChangeHall={handleChangeHall}
          onEditDecor={handleEditDecorFromViz}
          onExport={handleExportFromViz}
        />
        {showAuthModal && (
          <AuthModal
            onSignInEmail={handleSignInEmail}
            onSignInGoogle={signInGoogle}
            onClose={() => setShowAuthModal(false)}
            error={authError}
          />
        )}
      </>
    );
  }

  // ── Hall selection ────────────────────────────────────────────
  if (stage === 'hall_selection') {
    return (
      <>
        <AppHeader
          connected={connected}
          isSpeaking={isSpeaking}
          slotProgress={slotProgress}
          stage="hall_selection"
          user={user}
          onSignIn={() => setShowAuthModal(true)}
          onSignOut={signOut}
        />
        <HallSelection
          onSelect={handleHallSelected}
          onBack={handleBackToReview}
        />
      </>
    );
  }

  // ── Review ────────────────────────────────────────────────────
  if (stage === 'review') {
    return (
      <>
        <AppHeader
          connected={connected}
          isSpeaking={isSpeaking}
          slotProgress={slotProgress}
          stage="review"
          user={user}
          onSignIn={() => setShowAuthModal(true)}
          onSignOut={signOut}
        />
        <ReviewScreen
          state={state}
          onEdit={handleEditFromReview}
          onProceed={handleProceedToHall}
        />
      </>
    );
  }

  // ── Session ───────────────────────────────────────────────────
  return (
    <>
      <AppHeader
        connected={connected}
        isSpeaking={isSpeaking}
        slotProgress={slotProgress}
        stage="session"
        session={currentSession}
        onRename={renameSession}
        user={user}
        onSignIn={() => setShowAuthModal(true)}
        onSignOut={signOut}
      />
      <VoiceSession
        transcript={transcript}
        partialText={partialText}
        state={state}
        confirmation={confirmation}
        connected={connected}
        currentSlot={currentSlot}
        slotsAllFilled={slotsAllFilled}
        isSpeaking={isSpeaking}
        lkConnected={lkConnected}
        room={room}
        micState={micState}
        errorMessage={micErrorMessage}
        onRequestMic={requestMic}
        inputText={inputText}
        onInputChange={setInputText}
        onInputKeyDown={handleKeyDown}
        onSendText={handleSendText}
        onOptionSelect={handleOptionSelect}
        onConfirm={sendConfirmation}
        onMute={() => {}}
        onEndSession={handleEndSession}
        onProceedToReview={handleProceedToReview}
        onStateUpdate={sendStateUpdate}
      />
      {showAuthModal && (
        <AuthModal
          onSignInEmail={handleSignInEmail}
          onSignInGoogle={signInGoogle}
          onClose={() => setShowAuthModal(false)}
          error={authError}
        />
      )}
    </>
  );
}

/** Shared header — shown on all post-landing screens. */
function AppHeader({ connected, isSpeaking, slotProgress, stage, session, onRename, user, onSignIn, onSignOut }) {
  const stageLabels = {
    session:        'Planning',
    review:         'Review',
    hall_selection: 'Hall Selection',
    visualization:  'Visualization',
    generating:     'Generating',
  };

  return (
    <header className="app-header">
      <div className="app-header__logo">Maya</div>

      {/* Progress bar */}
      {stage === 'session' && slotProgress > 0 && (
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 2, background: 'var(--outline-variant)' }}>
          <div style={{
            height: '100%',
            width: `${slotProgress * 100}%`,
            background: 'linear-gradient(90deg, var(--primary-dark), var(--primary))',
            transition: 'width 0.6s ease',
          }} />
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
        {/* Session name + rename (session stage only) */}
        {stage === 'session' && session && onRename && (
          <SessionRename
            autoName={session.autoName}
            customName={session.customName}
            onRename={onRename}
          />
        )}

        {/* Stage label (non-session stages) */}
        {stage !== 'session' && (
          <span style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--on-surface-muted)' }}>
            {stageLabels[stage] ?? stage}
          </span>
        )}

        {isSpeaking && (
          <span className="speaking-badge">
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--primary)', display: 'inline-block', animation: 'dotPulse 1.2s infinite' }} />
            Maya speaking
          </span>
        )}

        {/* Auth button */}
        {user ? (
          <button className="header-auth-btn" onClick={onSignOut} title="Sign out">
            {user.name?.split(' ')[0] || 'Account'} ✕
          </button>
        ) : (
          <button className="header-auth-btn" onClick={onSignIn}>
            Sign in
          </button>
        )}

        <div className="app-header__status">
          <span className={`status-dot${connected ? '' : ' status-dot--off'}`} />
          {connected ? 'Live' : 'Offline'}
        </div>
      </div>
    </header>
  );
}
