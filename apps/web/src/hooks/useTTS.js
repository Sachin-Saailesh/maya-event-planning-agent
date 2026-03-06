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
 * Barge-in support: tracks last-spoken word position so interruption context
 * can be sent to the backend.
 */
export function useTTS() {
  const queueRef = useRef([]);
  const speakingRef = useRef(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useRef(null);

  // Barge-in tracking
  const currentTextRef = useRef('');
  const spokenSentencesRef = useRef([]);

  const processQueue = useCallback(async () => {
    if (queueRef.current.length === 0) {
      speakingRef.current = false;
      setIsSpeaking(false);
      return;
    }

    const text = queueRef.current.shift();
    console.log('[TTS] Speaking:', text.substring(0, 60));
    speakingRef.current = true;
    setIsSpeaking(true);
    currentTextRef.current = text;

    try {
      const url = `/tts?text=${encodeURIComponent(text)}`;
      const response = await fetch(url);

      if (!response.ok) {
        console.error('[TTS] Backend TTS error:', response.status, await response.text());
        speakingRef.current = false;
        setIsSpeaking(false);
        processQueue();
        return;
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        spokenSentencesRef.current.push(text);
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
        currentTextRef.current = '';
        processQueue();
      };

      audio.onerror = (e) => {
        console.error('[TTS] Audio playback error:', e);
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
        speakingRef.current = false;
        setIsSpeaking(false);
        processQueue();
      };

      await audio.play();
    } catch (err) {
      console.error('[TTS] Fetch/play error:', err);
      speakingRef.current = false;
      setIsSpeaking(false);
      processQueue();
    }
  }, []);

  const speak = useCallback((text) => {
    if (!text) return;
    queueRef.current.push(text);
    if (!speakingRef.current) {
      processQueue();
    }
  }, [processQueue]);

  const speakChunk = useCallback((chunk) => {
    if (!chunk) return;
    queueRef.current.push(chunk);
    if (!speakingRef.current) {
      processQueue();
    }
  }, [processQueue]);

  /** Stop playback immediately (barge-in or end session). */
  const stop = useCallback(() => {
    queueRef.current = [];
    speakingRef.current = false;
    setIsSpeaking(false);
    currentTextRef.current = '';

    if (audioRef.current) {
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
