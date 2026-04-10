import { useRef, useCallback, useState } from 'react';

/**
 * TTS Hook — uses backend /tts endpoint (OpenAI TTS) + HTMLAudioElement.
 *
 * WHY: window.speechSynthesis is silenced at the OS hardware level
 * whenever any WebRTC microphone track is active on macOS.
 *
 * FIX: Generate audio on the backend (OpenAI tts-1 model), stream MP3 bytes,
 * and play via HTMLAudioElement — which is NOT affected by the WebRTC lock.
 *
 * LATENCY IMPROVEMENT: Pre-fetch all sentence TTS in parallel so there is
 * zero per-sentence gap between sentences. Audio plays back-to-back seamlessly.
 *
 * Barge-in support: tracks last-spoken sentence so interruption context
 * can be sent to the backend.
 */
export function useTTS() {
  // Queue holds pre-fetched Audio objects (NOT text strings)
  const queueRef = useRef([]);
  const speakingRef = useRef(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useRef(null);
  const generationIdRef = useRef(0);

  // Barge-in tracking
  const currentTextRef = useRef('');
  const spokenSentencesRef = useRef([]);

  /**
   * Internal: play the next Audio object from the queue.
   * The queue contains pre-fetched Audio objects, not text strings.
   */
  const processObjQueue = useCallback(() => {
    if (queueRef.current.length === 0) {
      speakingRef.current = false;
      setIsSpeaking(false);
      return;
    }

    const audio = queueRef.current.shift();

    // Cancelled while waiting
    if (!audio) {
      processObjQueue();
      return;
    }

    const currentGen = generationIdRef.current;
    speakingRef.current = true;
    setIsSpeaking(true);
    currentTextRef.current = audio._sentenceText || '';
    audioRef.current = audio;

    audio.onended = () => {
      if (generationIdRef.current !== currentGen) return;
      spokenSentencesRef.current.push(audio._sentenceText || '');
      if (audio._blobUrl) URL.revokeObjectURL(audio._blobUrl);
      audioRef.current = null;
      currentTextRef.current = '';
      processObjQueue();
    };

    audio.onerror = (e) => {
      console.error('[TTS] Audio playback error:', e);
      if (audio._blobUrl) URL.revokeObjectURL(audio._blobUrl);
      audioRef.current = null;
      speakingRef.current = false;
      setIsSpeaking(false);
      processObjQueue();
    };

    audio.play().catch((err) => {
      console.error('[TTS] play() error:', err);
      speakingRef.current = false;
      setIsSpeaking(false);
      processObjQueue();
    });
  }, []);

  /**
   * Speak a full prompt text.
   *
   * Splits into sentences and pre-fetches ALL TTS audio in parallel so there
   * is no per-sentence network round-trip between sentences.
   * Audio objects are queued in order and played back-to-back seamlessly.
   */
  const speak = useCallback(async (text) => {
    if (!text) return;

    const capturedGen = ++generationIdRef.current;

    // Split on sentence boundaries (., !, ?) keeping delimiters
    const sentences = text.match(/[^.!?]+[.!?]+(?:\s|$)/g) || [text];
    const trimmed = sentences.map(s => s.trim()).filter(Boolean);
    if (trimmed.length === 0) return;

    // Pre-fetch all TTS audio blobs in parallel
    const fetchPromises = trimmed.map(async (sentence) => {
      try {
        const url = `/tts?text=${encodeURIComponent(sentence)}`;
        const response = await fetch(url);
        if (!response.ok) {
          console.error('[TTS] Backend TTS error:', response.status);
          return null;
        }
        const blob = await response.blob();
        return { sentence, blob };
      } catch (err) {
        console.error('[TTS] Fetch error for sentence:', sentence, err);
        return null;
      }
    });

    const results = await Promise.all(fetchPromises);

    // If cancelled while fetching, discard
    if (capturedGen !== generationIdRef.current) return;

    // Build Audio objects and enqueue them
    for (const result of results) {
      if (result && result.blob) {
        const audioUrl = URL.createObjectURL(result.blob);
        const audio = new Audio(audioUrl);
        audio._sentenceText = result.sentence;
        audio._blobUrl = audioUrl;
        queueRef.current.push(audio);
      }
    }

    if (!speakingRef.current) {
      processObjQueue();
    }
  }, [processObjQueue]);

  /**
   * speakChunk — for backwards-compat with single-sentence chunks.
   * Delegates to speak() which handles parallel fetching.
   */
  const speakChunk = useCallback((chunk) => {
    if (!chunk) return;
    speak(chunk);
  }, [speak]);

  /** Stop all playback immediately (barge-in or end session). */
  const stop = useCallback(() => {
    generationIdRef.current++; // invalidates any pending fetches
    // Revoke blob URLs for all queued (not-yet-played) audio objects
    for (const audio of queueRef.current) {
      if (audio._blobUrl) URL.revokeObjectURL(audio._blobUrl);
    }
    queueRef.current = [];
    speakingRef.current = false;
    setIsSpeaking(false);
    currentTextRef.current = '';

    if (audioRef.current) {
      if (audioRef.current._blobUrl) URL.revokeObjectURL(audioRef.current._blobUrl);
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
  }, []);

  /**
   * Stop playback for barge-in and return the last spoken sentence
   * so the backend can track what was interrupted.
   */
  const cancelForBargeIn = useCallback(() => {
    const lastSentence = spokenSentencesRef.current[spokenSentencesRef.current.length - 1]
      || currentTextRef.current
      || '';
    stop();
    return lastSentence;
  }, [stop]);

  const clearSpokenSentences = useCallback(() => {
    spokenSentencesRef.current = [];
  }, []);

  return { speak, speakChunk, stop, cancelForBargeIn, clearSpokenSentences, isSpeaking };
}
