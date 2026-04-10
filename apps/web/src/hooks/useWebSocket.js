import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * WebSocket hook for communicating with the Maya orchestrator.
 * Supports auto-reconnection and advanced event handling.
 */
export function useWebSocket(sessionId) {
  const [connected, setConnected] = useState(false);
  const [transcript, setTranscript] = useState([]);
  const [partialText, setPartialText] = useState('');
  const [state, setState] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [latestPrompt, setLatestPrompt] = useState('');
  const [promptChunks, setPromptChunks] = useState([]);
  const [guardrailBlocked, setGuardrailBlocked] = useState(null);
  const [speechInterrupted, setSpeechInterrupted] = useState(null);
  const [slotsFilledEvent, setSlotsFilledEvent] = useState(null);
  const [reviewProceedEvent, setReviewProceedEvent] = useState(null);
  const [reviewModifySlotEvent, setReviewModifySlotEvent] = useState(null);
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimerRef = useRef(null);
  const sessionIdRef = useRef(sessionId);
  const MAX_RECONNECT_ATTEMPTS = 5;

  // Keep sessionId ref current
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const connectWs = useCallback(() => {
    if (!sessionIdRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/session/${sessionIdRef.current}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect with exponential backoff
      if (sessionIdRef.current && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 16000);
        reconnectAttempts.current += 1;
        console.log(`WebSocket disconnected. Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})...`);
        reconnectTimerRef.current = setTimeout(() => connectWs(), delay);
      }
    };

    ws.onerror = () => setConnected(false);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleEvent(data);
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    connectWs();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [sessionId, connectWs]);

  const handleEvent = useCallback((event) => {
    const { type, payload } = event;

    switch (type) {
      case 'client.transcript.partial':
        setPartialText(payload.text || '');
        break;

      case 'client.transcript.final':
        // Voice transcript from agent worker — show user's spoken text in the UI
        console.log(`[STT_OUTPUT] Received final transcript: "${payload.text}"`);
        setPartialText('');
        setTranscript(prev => {
          // Avoid duplicate if we already added this locally via sendTranscript
          const lastEntry = prev[prev.length - 1];
          if (lastEntry && lastEntry.speaker === 'user' && lastEntry.text === payload.text) {
            return prev;
          }
          return [...prev, {
            speaker: 'user',
            text: payload.text,
            ts: Date.now(),
            isFinal: true,
          }];
        });
        break;

      case 'server.prompt':
        setPartialText('');
        setTranscript(prev => [...prev, {
          speaker: 'maya',
          text: payload.text,
          ts: Date.now(),
          isFinal: true,
        }]);
        setLatestPrompt(payload.text);
        break;

      case 'server.prompt.chunk':
        // Streaming: accumulate sentence chunks
        setPromptChunks(prev => [...prev, payload.text]);
        break;

      case 'server.state.patch':
        if (payload.state) {
          setState(payload.state);
        }
        break;

      case 'server.confirmation.request':
        setConfirmation(payload);
        setTranscript(prev => [...prev, {
          speaker: 'maya',
          text: payload.message,
          ts: Date.now(),
          isFinal: true,
        }]);
        setLatestPrompt(payload.message);
        break;

      case 'client.speech.started':
        // Fast signal from VAD that user is speaking — stop Maya instantly
        setSpeechInterrupted(Date.now());
        break;

      case 'server.speech.interrupted':
        // Maya was interrupted — payload has last_spoken_sentence
        break;

      case 'server.guardrail.blocked':
        setGuardrailBlocked(payload);
        setTranscript(prev => [...prev, {
          speaker: 'maya',
          text: payload.message || 'I can only help with wedding decoration planning.',
          ts: Date.now(),
          isFinal: true,
        }]);
        break;

      case 'server.session.restored':
        // Restore state after reconnection
        if (payload.state) setState(payload.state);
        if (payload.transcript) setTranscript(payload.transcript);
        break;

      case 'server.slots.filled':
        setSlotsFilledEvent(Date.now());
        break;

      case 'server.review.proceed':
        setReviewProceedEvent(Date.now());
        break;

      case 'server.review.modify_slot':
        // Backend cleared the slot and set current_slot.
        // State patch arrives via server.state.patch; this event tells the
        // frontend to return to the session stage.
        setReviewModifySlotEvent(Date.now());
        break;

      case 'server.summary.ready':
        break;

      default:
        break;
    }
  }, []);

  const sendTranscript = useCallback((text, isFinal = true) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const type = isFinal ? 'client.transcript.final' : 'client.transcript.partial';
    wsRef.current.send(JSON.stringify({
      type,
      session_id: sessionIdRef.current,
      payload: { text },
    }));

    if (isFinal) {
      setTranscript(prev => [...prev, {
        speaker: 'user',
        text,
        ts: Date.now(),
        isFinal: true,
      }]);
      setPartialText('');
    }
  }, []);

  const sendStateUpdate = useCallback((op, slot, value) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'client.state.update',
      session_id: sessionIdRef.current,
      payload: { op, slot, value },
    }));
  }, []);

  const sendConfirmation = useCallback((choice) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'client.transcript.final',
      session_id: sessionIdRef.current,
      payload: { text: choice },
    }));
    setConfirmation(null);

    setTranscript(prev => [...prev, {
      speaker: 'user',
      text: choice,
      ts: Date.now(),
      isFinal: true,
    }]);
  }, []);

  const sendBargeIn = useCallback((lastSpokenSentence) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'client.barge_in',
      session_id: sessionIdRef.current,
      payload: { last_spoken_sentence: lastSpokenSentence || '' },
    }));
  }, []);

  const sendIdleTimeout = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      type: 'client.idle.timeout',
      session_id: sessionIdRef.current,
      payload: {},
    }));
  }, []);

  return {
    connected,
    transcript,
    partialText,
    state,
    confirmation,
    latestPrompt,
    promptChunks,
    guardrailBlocked,
    speechInterrupted,
    slotsFilledEvent,
    reviewProceedEvent,
    reviewModifySlotEvent,
    sendTranscript,
    sendStateUpdate,
    sendConfirmation,
    sendBargeIn,
    sendIdleTimeout,
  };
}
