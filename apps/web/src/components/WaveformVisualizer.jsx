import { useEffect, useRef } from 'react';

/**
 * WaveformVisualizer — premium state-aware voice indicator.
 *
 * voiceState: 'idle' | 'listening' | 'thinking' | 'speaking'
 *
 * - idle:      soft single flat wave, slow gold pulse
 * - listening: animated frequency bars (user speaking)
 * - thinking:  bouncing purple dots
 * - speaking:  two animated sinusoidal SVG waves
 */
export default function WaveformVisualizer({ voiceState = 'idle' }) {
  return (
    <div className="waveform-wrap" aria-label={`Maya is ${voiceState}`}>
      {/* Ambient glow behind the waveform */}
      <div
        className="waveform-glow-ring waveform-glow-ring--gold"
        style={{ opacity: voiceState === 'speaking' ? 1 : 0.5 }}
      />
      <div
        className="waveform-glow-ring waveform-glow-ring--purple"
        style={{ opacity: voiceState === 'thinking' ? 1 : 0.4 }}
      />

      {/* Dynamic waveform based on state */}
      <div style={{ position: 'relative', zIndex: 2 }}>
        {voiceState === 'idle'      && <IdleWave />}
        {voiceState === 'listening' && <ListeningBars />}
        {voiceState === 'thinking'  && <ThinkingDots />}
        {voiceState === 'speaking'  && <SpeakingWaves />}
      </div>
    </div>
  );
}

/* ── Idle: flat gently breathing wave ───────────────────────── */
function IdleWave() {
  return (
    <svg
      className="waveform-svg"
      viewBox="0 0 280 120"
      style={{ overflow: 'visible' }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="waveGradIdle" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#f2ca50" stopOpacity="0.2" />
          <stop offset="50%"  stopColor="#f2ca50" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#f2ca50" stopOpacity="0.2" />
        </linearGradient>
      </defs>
      <path
        className="waveform-path"
        d="M 20,60 Q 70,50 140,60 T 260,60"
        stroke="url(#waveGradIdle)"
        strokeWidth="2"
        style={{ animation: 'pulse-glow 3s ease-in-out infinite' }}
      />
    </svg>
  );
}

/* ── Listening: animated frequency bars ─────────────────────── */
function ListeningBars() {
  const BARS = 18;
  const DELAYS = Array.from({ length: BARS }, (_, i) => `${(i * 0.08).toFixed(2)}s`);

  return (
    <div className="listen-bars" aria-hidden="true">
      {DELAYS.map((delay, i) => (
        <div
          key={i}
          className="listen-bar"
          style={{
            animationDelay: delay,
            animationDuration: `${0.9 + (i % 3) * 0.15}s`,
            opacity: 0.6 + (i % 4) * 0.1,
          }}
        />
      ))}
    </div>
  );
}

/* ── Thinking: bouncing dots ─────────────────────────────────── */
function ThinkingDots() {
  return (
    <div className="think-dots" aria-hidden="true">
      {[0, 1, 2].map(i => (
        <div
          key={i}
          className="think-dot"
          style={{ animationDelay: `${i * 0.4}s` }}
        />
      ))}
    </div>
  );
}

/* ── Speaking: animated sinusoidal waves ─────────────────────── */
function SpeakingWaves() {
  return (
    <svg
      className="waveform-svg speaking-wave"
      viewBox="0 0 280 120"
      style={{ overflow: 'visible' }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="waveGradSpeak" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#f2ca50" stopOpacity="0.1" />
          <stop offset="50%"  stopColor="#f2ca50" stopOpacity="1.0" />
          <stop offset="100%" stopColor="#e9c7c0" stopOpacity="0.1" />
        </linearGradient>
        <linearGradient id="waveGradSpeak2" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#ddb7ff" stopOpacity="0.1" />
          <stop offset="50%"  stopColor="#ddb7ff" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#ddb7ff" stopOpacity="0.1" />
        </linearGradient>
      </defs>

      {/* Background glow layer */}
      <path
        d="M 20,60 Q 70,20 140,60 T 260,60"
        fill="none"
        stroke="#f2ca50"
        strokeWidth="8"
        strokeLinecap="round"
        opacity="0.06"
        style={{
          animation: 'wave1 2.5s ease-in-out infinite',
        }}
      />

      {/* Secondary wave (purple) */}
      <path
        d="M 20,60 Q 80,10 140,60 T 260,60"
        fill="none"
        stroke="url(#waveGradSpeak2)"
        strokeWidth="1.5"
        strokeLinecap="round"
        style={{
          animation: 'wave2 3.2s ease-in-out infinite',
          opacity: 0.5,
        }}
      />

      {/* Primary wave (gold) */}
      <path
        d="M 20,60 Q 60,25 140,60 T 260,60"
        fill="none"
        stroke="url(#waveGradSpeak)"
        strokeWidth="2.5"
        strokeLinecap="round"
        style={{
          animation: 'wave3 2s ease-in-out infinite',
        }}
      />
    </svg>
  );
}
