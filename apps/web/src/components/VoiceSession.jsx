import { useCallback } from 'react';
import Transcript from './Transcript.jsx';
import StatePanel from './StatePanel.jsx';
import WaveformVisualizer from './WaveformVisualizer.jsx';
import OptionRail from './OptionRail.jsx';
import AudioWaveform from './AudioWaveform.jsx';
import { SLOT_CONFIG } from '../slotConfig.js';

/**
 * VoiceSession — three-column live planning screen.
 *
 * Layout:
 *   [Transcript 280px] | [Voice center flex] | [State panel 300px]
 *
 * voiceState: 'idle' | 'listening' | 'thinking' | 'speaking'
 */
export default function VoiceSession({
  // WebSocket state
  transcript,
  partialText,
  state,
  confirmation,
  connected,
  currentSlot,
  slotsAllFilled,
  // TTS
  isSpeaking,
  // LiveKit
  lkConnected,
  room,
  // Mic permission
  micState,
  errorMessage: micErrorMessage,
  onRequestMic,
  // Actions
  inputText,
  onInputChange,
  onInputKeyDown,
  onSendText,
  onOptionSelect,
  onConfirm,
  onMute,
  onEndSession,
  onProceedToReview,
  onStateUpdate,
}) {
  // Derive voice state for the waveform
  const voiceState = isSpeaking
    ? 'speaking'
    : partialText
    ? 'listening'
    : connected
    ? 'idle'
    : 'idle';

  const stateLabel = {
    idle:      'Listening…',
    listening: 'Hearing you…',
    thinking:  'Processing…',
    speaking:  'Designing your atmosphere…',
  }[voiceState];

  const stateSub = {
    idle:      'Voice active',
    listening: 'Voice input detected',
    thinking:  'NLU · Slot filling',
    speaking:  'TTS · OpenAI voice',
  }[voiceState];

  const micGranted = micState === 'granted' || micState === 'unknown';

  return (
    <>
      {/* Three-column layout */}
      <div className="session-layout">
        {/* Left: Transcript */}
        <Transcript transcript={transcript} partialText={partialText} />

        {/* Center: Voice interaction area */}
        <div className="voice-center" style={{ position: 'relative' }}>
          {/* Mic permission overlay */}
          {!micGranted && <MicBanner micState={micState} errorMessage={micErrorMessage} onRequest={onRequestMic} />}

          {/* Waveform */}
          <WaveformVisualizer voiceState={voiceState} />

          {/* Maya state label */}
          <div className="maya-state">
            <div className="maya-state__label">{stateLabel}</div>
            <div className="maya-state__sub">
              {isSpeaking && (
                <span className="speaking-badge">
                  <span
                    style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: 'var(--primary)', display: 'inline-block',
                      animation: 'dotPulse 1.2s infinite',
                    }}
                  />
                  Maya speaking
                </span>
              )}
              {!isSpeaking && stateSub}
            </div>
          </div>

          {/* Contextual option rail */}
          <OptionRail currentSlot={currentSlot} onSelect={onOptionSelect} />

          {/* Text input fallback */}
          <div style={{
            width: '100%', maxWidth: 420,
            display: 'flex', gap: 8, alignItems: 'center',
          }}>
            {lkConnected && (
              <AudioWaveform room={room} />
            )}
            <input
              type="text"
              value={inputText}
              onChange={e => onInputChange(e.target.value)}
              onKeyDown={onInputKeyDown}
              placeholder="Type here or speak…"
              style={{
                flex: 1,
                padding: '10px 16px',
                background: 'var(--surface-container)',
                border: '1px solid var(--outline-variant)',
                borderRadius: 'var(--radius-full)',
                color: 'var(--on-surface)',
                fontFamily: 'var(--font-body)',
                fontSize: '0.82rem',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--primary)')}
              onBlur={e => (e.target.style.borderColor = 'var(--outline-variant)')}
            />
            <button
              onClick={onSendText}
              style={{
                padding: '10px 18px',
                background: 'linear-gradient(135deg, var(--primary), var(--primary-dark))',
                color: 'var(--on-primary)',
                border: 'none',
                borderRadius: 'var(--radius-full)',
                fontFamily: 'var(--font-body)',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                letterSpacing: '0.06em',
              }}
            >
              Send
            </button>
          </div>

          {/* Proceed hint when all slots filled */}
          {slotsAllFilled && (
            <div className="session-proceed-hint">
              <button className="btn-gold" onClick={onProceedToReview}>
                Review Your Selections →
              </button>
            </div>
          )}
        </div>

        {/* Right: State panel */}
        <StatePanel
          state={state}
          currentSlot={currentSlot}
          onStateUpdate={onStateUpdate}
        />
      </div>

      {/* Confirmation banner (floats above bottom bar) */}
      {confirmation && (
        <div className="confirmation-bar">
          <div className="confirmation-bar__text">{confirmation.message}</div>
          <div className="confirmation-bar__actions">
            {(confirmation.options || ['replace', 'add', 'remove']).map(opt => (
              <button
                key={opt}
                className={`confirmation-bar__btn${opt === 'add' ? ' confirmation-bar__btn--primary' : ''}`}
                onClick={() => onConfirm(opt)}
              >
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Bottom floating controls */}
      <nav className="bottom-bar">
        <MicButton micState={micState} voiceState={voiceState} onMute={onMute} onRequestMic={onRequestMic} />

        {/* Central CTA */}
        <button
          className="bottom-bar__cta"
          onClick={onSendText}
          title="Send / Ask Maya"
        >
          ✦
        </button>

        {slotsAllFilled ? (
          <button
            className="bottom-bar__btn bottom-bar__btn--active"
            onClick={onProceedToReview}
            title="Review selections"
          >
            <span className="bottom-bar__btn-icon">📋</span>
            <span className="bottom-bar__btn-label">Review</span>
          </button>
        ) : (
          <button className="bottom-bar__btn" title="Connection status">
            <span className="bottom-bar__btn-icon">{connected ? '🟢' : '🔴'}</span>
            <span className="bottom-bar__btn-label">{connected ? 'Live' : 'Offline'}</span>
          </button>
        )}

        <button
          className="bottom-bar__btn bottom-bar__btn--danger"
          onClick={onEndSession}
          title="End session"
        >
          <span className="bottom-bar__btn-icon">✕</span>
          <span className="bottom-bar__btn-label">End</span>
        </button>
      </nav>
    </>
  );
}

/** Mic permission overlay shown in the voice center when mic is not granted. */
function MicBanner({ micState, errorMessage, onRequest }) {
  if (micState === 'denied') {
    return (
      <div className="mic-banner">
        <div className="mic-banner__card">
          <div className="mic-banner__icon">🚫</div>
          <div className="mic-banner__title">Microphone blocked</div>
          <div className="mic-banner__desc mic-banner__desc--error">
            {errorMessage || 'Microphone access is blocked.'}
          </div>
          <div className="mic-banner__desc">
            To fix this, click the lock icon in your browser's address bar and allow microphone access, then refresh.
          </div>
        </div>
      </div>
    );
  }

  if (micState === 'unavailable') {
    return (
      <div className="mic-banner">
        <div className="mic-banner__card">
          <div className="mic-banner__icon">🎙</div>
          <div className="mic-banner__title">No microphone found</div>
          <div className="mic-banner__desc">
            {errorMessage || 'Please connect a microphone and refresh the page.'}
          </div>
          <div className="mic-banner__desc">
            You can still type using the text input below.
          </div>
        </div>
      </div>
    );
  }

  if (micState === 'error') {
    return (
      <div className="mic-banner">
        <div className="mic-banner__card">
          <div className="mic-banner__icon">⚠️</div>
          <div className="mic-banner__title">Microphone error</div>
          <div className="mic-banner__desc mic-banner__desc--error">
            {errorMessage}
          </div>
        </div>
      </div>
    );
  }

  // 'requesting' or any transient state — show the enable prompt
  return (
    <div className="mic-banner">
      <div className="mic-banner__card">
        <div className="mic-banner__icon">🎤</div>
        <div className="mic-banner__title">Microphone access required</div>
        <div className="mic-banner__desc">
          Microphone access is required to speak with Maya. Please enable your mic to continue.
        </div>
        <button
          className="btn-gold"
          onClick={onRequest}
          disabled={micState === 'requesting'}
          style={{ marginTop: 4 }}
        >
          {micState === 'requesting'
            ? <span className="loading-dots"><span /><span /><span /></span>
            : 'Enable Microphone'}
        </button>
        <div className="mic-banner__desc" style={{ marginTop: 4 }}>
          You can also type your responses below.
        </div>
      </div>
    </div>
  );
}

/** Bottom bar mic button — reflects permission + voice state. */
function MicButton({ micState, voiceState, onMute, onRequestMic }) {
  if (micState === 'denied') {
    return (
      <button
        className="bottom-bar__btn bottom-bar__btn--danger"
        title="Microphone blocked — click to see how to fix"
        style={{ cursor: 'default' }}
      >
        <span className="bottom-bar__btn-icon">🚫</span>
        <span className="bottom-bar__btn-label">Blocked</span>
      </button>
    );
  }

  if (micState === 'unavailable') {
    return (
      <button className="bottom-bar__btn" style={{ cursor: 'default' }} title="No microphone found">
        <span className="bottom-bar__btn-icon">🎙</span>
        <span className="bottom-bar__btn-label">No mic</span>
      </button>
    );
  }

  if (micState === 'requesting') {
    return (
      <button className="bottom-bar__btn" disabled title="Requesting microphone…">
        <span className="bottom-bar__btn-icon">⏳</span>
        <span className="bottom-bar__btn-label">Allowing…</span>
      </button>
    );
  }

  // unknown → offer one-click grant
  if (micState === 'unknown') {
    return (
      <button
        className="bottom-bar__btn"
        onClick={onRequestMic}
        title="Enable microphone"
      >
        <span className="bottom-bar__btn-icon">🎤</span>
        <span className="bottom-bar__btn-label">Allow Mic</span>
      </button>
    );
  }

  // granted — normal mute toggle
  return (
    <button
      className={`bottom-bar__btn${voiceState === 'listening' ? ' bottom-bar__btn--active' : ''}`}
      onClick={onMute}
      title="Toggle mute"
    >
      <span className="bottom-bar__btn-icon">
        {voiceState === 'listening' ? '🎙' : '🎤'}
      </span>
      <span className="bottom-bar__btn-label">
        {voiceState === 'listening' ? 'Hearing' : 'Mic'}
      </span>
    </button>
  );
}
