import { useState, useEffect, useCallback } from 'react';

/**
 * useMicrophone — tracks browser microphone permission state.
 *
 * States:
 *   'unknown'     — not yet checked (initial)
 *   'requesting'  — getUserMedia in flight
 *   'granted'     — permission confirmed
 *   'denied'      — user/browser blocked it
 *   'unavailable' — no device found
 *   'error'       — unexpected error
 *
 * This is intentionally separate from LiveKit. It performs a lightweight
 * permission check so the UI can surface actionable guidance before the
 * LiveKit room tries to open the mic track.
 */
export function useMicrophone() {
  const [micState, setMicState] = useState('unknown');
  const [errorMessage, setErrorMessage] = useState('');

  // Query current permission state on mount (no prompt triggered).
  useEffect(() => {
    if (!navigator.mediaDevices) {
      setMicState('unavailable');
      setErrorMessage('Your browser does not support microphone access.');
      return;
    }

    if (navigator.permissions) {
      navigator.permissions
        .query({ name: 'microphone' })
        .then(status => {
          if (status.state === 'granted') setMicState('granted');
          else if (status.state === 'denied') setMicState('denied');
          // 'prompt' → stays 'unknown' until user interacts

          // Listen for changes (e.g. user toggles permission in browser settings)
          status.onchange = () => {
            if (status.state === 'granted') {
              setMicState('granted');
              setErrorMessage('');
            } else if (status.state === 'denied') {
              setMicState('denied');
              setErrorMessage('Microphone access is blocked. Please enable it in your browser settings.');
            }
          };
        })
        .catch(() => {
          // Permissions API not available in this browser — state stays 'unknown'
          // until requestMic() is called.
        });
    }
  }, []);

  /**
   * Explicitly request microphone permission.
   * Stops the test stream immediately — LiveKit will open its own track later.
   * Safe to call multiple times; no-ops if already 'granted'.
   */
  const requestMic = useCallback(async () => {
    if (micState === 'granted') return;
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicState('unavailable');
      setErrorMessage('Your browser does not support microphone access.');
      return;
    }

    setMicState('requesting');
    setErrorMessage('');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Release the test stream — LiveKit manages its own audio track.
      stream.getTracks().forEach(t => t.stop());
      setMicState('granted');
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setMicState('denied');
        setErrorMessage(
          'Microphone access is blocked. Please enable it in your browser settings, then refresh.'
        );
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setMicState('unavailable');
        setErrorMessage('No microphone found. Please connect a microphone and try again.');
      } else {
        setMicState('error');
        setErrorMessage(`Microphone error: ${err.message}`);
      }
    }
  }, [micState]);

  return { micState, errorMessage, requestMic };
}
