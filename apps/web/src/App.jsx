import { useState, useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "./hooks/useWebSocket.js";
import { useTTS } from "./hooks/useTTS.js";
import { useLiveKit } from "./hooks/useLiveKit.js";
import Transcript from "./components/Transcript.jsx";
import StatePanel from "./components/StatePanel.jsx";
import ExportBrief from "./components/ExportBrief.jsx";

/**
 * Maya — South Indian Wedding Decoration Planner
 * Enhanced with barge-in, streaming, and voice clarity controls.
 */
export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [view, setView] = useState("landing"); // 'landing' | 'session' | 'export'
  const [loading, setLoading] = useState(false);
  const [inputText, setInputText] = useState("");
  const [voiceClarity, setVoiceClarity] = useState(true);

  const {
    connected: lkConnected,
    micEnabled,
    connect: lkConnect,
    toggleMic,
    disconnect: lkDisconnect,
  } = useLiveKit(sessionId);

  const {
    connected,
    transcript,
    partialText,
    state,
    confirmation,
    latestPrompt,
    speechInterrupted,
    sendTranscript,
    sendStateUpdate,
    sendConfirmation,
    sendBargeIn,
    sendIdleTimeout,
  } = useWebSocket(sessionId);

  const {
    speak,
    stop: stopTTS,
    isSpeaking,
    cancelForBargeIn,
    clearSpokenSentences,
  } = useTTS();

  const idleTimerRef = useRef(null);

  // Speak Maya's prompts via TTS + reset 60s idle timer
  useEffect(() => {
    if (!latestPrompt) return;
    clearSpokenSentences();
    
    // Split into sentences for lower TTS latency
    const sentences = latestPrompt.match(/[^.!?]+[.!?]+(?:\s|$)/g) || [latestPrompt];
    for (const sentence of sentences) {
      if (sentence.trim()) {
        speakChunk(sentence.trim());
      }
    }

    // Reset idle timer every time Maya speaks, unless it's a fallback phrase
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    
    if (!latestPrompt.startsWith("Are you still there?")) {
      idleTimerRef.current = setTimeout(() => {
        sendIdleTimeout();
      }, 60000);
    }
  }, [latestPrompt, speak, clearSpokenSentences, sendIdleTimeout]);

  // Barge-in: when VAD detects user speaking mid-TTS, stop Maya immediately
  useEffect(() => {
    if (!speechInterrupted) return;
    const lastSentence = cancelForBargeIn();
    sendBargeIn(lastSentence);
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
  }, [speechInterrupted, cancelForBargeIn, sendBargeIn]);

  // Turn on mic automatically when LiveKit connects
  useEffect(() => {
    if (lkConnected && !micEnabled) {
      toggleMic(true);
    }
  }, [lkConnected, micEnabled, toggleMic]);

  const handleStartSession = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch("/session", { method: "POST" });
      const data = await resp.json();

      if (data.livekit_token && data.livekit_url) {
        await lkConnect(data.livekit_token, data.livekit_url);
      }

      setSessionId(data.session_id);
      setView("session");
    } catch (err) {
      console.error("Failed to create session:", err);
      alert(
        "Failed to connect to Maya. Make sure the orchestrator is running on port 8000.",
      );
    } finally {
      setLoading(false);
    }
  }, [lkConnect]);

  const handleSendText = useCallback(() => {
    const text = inputText.trim();
    if (!text) return;

    // If Maya is speaking, barge-in first
    if (isSpeaking) {
      const lastSentence = cancelForBargeIn();
      sendBargeIn(lastSentence);
    }

    sendTranscript(text, true);
    setInputText("");
  }, [inputText, sendTranscript, isSpeaking, cancelForBargeIn, sendBargeIn]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") {
        handleSendText();
      }
    },
    [handleSendText],
  );

  const handleExport = useCallback(async () => {
    if (!sessionId) return;
    try {
      await fetch(`/session/${sessionId}/export`, { method: "POST" });
      setView("export");
    } catch (err) {
      console.error("Export failed:", err);
    }
  }, [sessionId]);

  const handleEndSession = useCallback(() => {
    stopTTS();
    lkDisconnect();
    setSessionId(null);
    setView("landing");
  }, [stopTTS, lkDisconnect]);

  // ── Landing ────────────────────────────────────────────
  if (view === "landing") {
    return (
      <div className="landing">
        <div className="landing__logo">✦ Maya</div>
        <p className="landing__subtitle">
          Your AI assistant for planning South Indian wedding hall decorations.
          Speak your preferences and get a complete decoration brief.
        </p>
        <p className="landing__tagline">Powered by voice · Built for beauty</p>
        <button
          className="btn-primary"
          onClick={handleStartSession}
          disabled={loading}
        >
          {loading ? (
            <span className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </span>
          ) : (
            <>🎤 Start Planning with Maya</>
          )}
        </button>
      </div>
    );
  }

  // ── Export ──────────────────────────────────────────────
  if (view === "export") {
    return <ExportBrief state={state} onBack={() => setView("session")} />;
  }

  // ── Session ────────────────────────────────────────────
  return (
    <div className="session">
      {/* Header */}
      <header className="session__header">
        <div className="session__header-left">
          <span className="session__logo">✦ Maya</span>
          <div className="session__status">
            <span
              className={`session__status-dot`}
              style={{
                background: connected ? "var(--success)" : "var(--danger)",
              }}
            ></span>
            {connected ? "Connected" : "Reconnecting..."}
          </div>
          {isSpeaking && (
            <span className="session__speaking-indicator">
              🔊 Maya is speaking...
            </span>
          )}
        </div>
        <div className="session__header-actions">
          <label
            className="voice-clarity-toggle"
            title="Enhanced audio processing"
          >
            <input
              type="checkbox"
              checked={voiceClarity}
              onChange={(e) => setVoiceClarity(e.target.checked)}
            />
            <span className="voice-clarity-label">🎧 Voice clarity</span>
          </label>
          <button className="btn-secondary" onClick={handleExport}>
            📄 Export Brief
          </button>
          <button className="btn-danger" onClick={handleEndSession}>
            End Session
          </button>
        </div>
      </header>

      {/* Transcript */}
      <Transcript transcript={transcript} partialText={partialText} />

      {/* Mic / Input bar */}
      <div className="mic-bar">
        {confirmation ? (
          <div className="confirmation" style={{ flex: 1 }}>
            <div className="confirmation__text">{confirmation.message}</div>
            <div className="confirmation__actions">
              {(confirmation.options || ["replace", "add", "remove"]).map(
                (opt) => (
                  <button
                    key={opt}
                    className={`confirmation__btn ${opt === "add" ? "confirmation__btn--primary" : ""}`}
                    onClick={() => sendConfirmation(opt)}
                  >
                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </button>
                ),
              )}
            </div>
          </div>
        ) : (
          <div className="sim-input">
            {lkConnected && (
              <button
                className={`btn-mic ${micEnabled ? "active" : ""}`}
                onClick={toggleMic}
                title={micEnabled ? "Mute Microphone" : "Enable Microphone"}
              >
                {micEnabled ? "🎙️" : "🔇"}
              </button>
            )}
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your preferences or speak..."
              autoFocus
            />
            <button onClick={handleSendText}>Send</button>
          </div>
        )}
      </div>

      {/* State Panel */}
      <StatePanel state={state} onStateUpdate={sendStateUpdate} />
    </div>
  );
}
