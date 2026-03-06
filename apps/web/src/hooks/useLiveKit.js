import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * LiveKit client hook for WebRTC audio.
 * Connects to a LiveKit room, publishes microphone audio with
 * enhanced audio constraints, and supports auto-reconnection.
 */
export function useLiveKit(sessionId) {
  const [connected, setConnected] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const roomRef = useRef(null);
  const tokenRef = useRef(null);
  const urlRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT = 5;

  const connect = useCallback(async (token, url) => {
    tokenRef.current = token;
    urlRef.current = url;
    try {
      const { Room, RoomEvent } = await import('livekit-client');
      const room = new Room({
        audioCaptureDefaults: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: true,
        },
        adaptiveStream: true,
        dynacast: true,
      });
      roomRef.current = room;

      room.on(RoomEvent.Connected, () => {
        setConnected(true);
        reconnectAttemptsRef.current = 0;
      });

      room.on(RoomEvent.Disconnected, () => {
        setConnected(false);
        // Auto-reconnect
        if (tokenRef.current && reconnectAttemptsRef.current < MAX_RECONNECT) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 16000);
          reconnectAttemptsRef.current += 1;
          console.log(`LiveKit disconnected. Reconnecting in ${delay}ms...`);
          setTimeout(() => {
            connect(tokenRef.current, urlRef.current);
          }, delay);
        }
      });

      room.on(RoomEvent.Reconnecting, () => {
        console.log('LiveKit reconnecting...');
      });

      room.on(RoomEvent.Reconnected, () => {
        console.log('LiveKit reconnected!');
        setConnected(true);
      });

      await room.connect(url, token);
    } catch (err) {
      console.error('LiveKit connection failed:', err);
      setConnected(false);
    }
  }, []);

  const toggleMic = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;

    try {
      if (micEnabled) {
        room.localParticipant.setMicrophoneEnabled(false);
        setMicEnabled(false);
      } else {
        await room.localParticipant.setMicrophoneEnabled(true, {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: true,
        });
        setMicEnabled(true);
      }
    } catch (err) {
      console.error('Mic toggle error:', err);
    }
  }, [micEnabled]);

  const disconnect = useCallback(() => {
    reconnectAttemptsRef.current = MAX_RECONNECT; // prevent auto-reconnect
    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }
    tokenRef.current = null;
    urlRef.current = null;
    setConnected(false);
    setMicEnabled(false);
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, []);

  return { connected, micEnabled, connect, toggleMic, disconnect };
}
