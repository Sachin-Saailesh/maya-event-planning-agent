import { useState, useCallback, useEffect, useRef } from 'react';
import {
  createSession as _create,
  getSession,
  saveSession as _save,
  getAllSessions,
  getSessionsForUser,
  getGuestSessions,
  getCurrentSessionId,
  setCurrentSessionId,
  deleteSession,
} from '../services/sessionStorage.js';
import { generateSessionName, shouldUpdateAutoName } from '../services/sessionNaming.js';

const SAVE_DEBOUNCE_MS = 1500;

/**
 * Hook that wraps session persistence.
 *
 * Exposes:
 *   currentSession     — active session object (or null)
 *   recentSessions     — sorted list of saved sessions for the current user/guest
 *   createNewSession   — fn(serverId, ownerId) → session
 *   restoreSession     — fn(id) → session | null
 *   updateSession      — fn(partial) — debounced save
 *   renameSession      — fn(name) — sets customName, immediate save
 *   removeSession      — fn(id)
 */
export function useSavedSessions(user) {
  const [currentSession, setCurrentSession] = useState(null);
  const [recentSessions, setRecentSessions] = useState([]);
  const saveTimerRef = useRef(null);

  // Load recent sessions list
  const refreshList = useCallback(() => {
    const all = user?.id ? getSessionsForUser(user.id) : getGuestSessions();
    setRecentSessions(all);
  }, [user]);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  // Restore last session on mount if it exists
  useEffect(() => {
    const lastId = getCurrentSessionId();
    if (lastId) {
      const s = getSession(lastId);
      if (s) setCurrentSession(s);
    }
  }, []);

  const createNewSession = useCallback((serverId, ownerId = null) => {
    const s = _create(serverId, ownerId);
    setCurrentSession(s);
    refreshList();
    return s;
  }, [refreshList]);

  const restoreSession = useCallback((id) => {
    const s = getSession(id);
    if (!s) return null;
    setCurrentSessionId(id);
    setCurrentSession(s);
    return s;
  }, []);

  const updateSession = useCallback((partial) => {
    setCurrentSession(prev => {
      if (!prev) return prev;

      // Auto-naming: only if no customName set
      let autoName = prev.autoName;
      if (!prev.customName && partial.state) {
        const candidate = generateSessionName(partial.state);
        if (shouldUpdateAutoName(autoName, candidate)) {
          autoName = candidate;
        }
      }

      const updated = { ...prev, ...partial, autoName };

      // Debounced persist
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        _save(updated.id, updated);
      }, SAVE_DEBOUNCE_MS);

      return updated;
    });
  }, []);

  const renameSession = useCallback((name) => {
    setCurrentSession(prev => {
      if (!prev) return prev;
      const updated = { ...prev, customName: name.trim() || null };
      _save(updated.id, updated);
      refreshList();
      return updated;
    });
  }, [refreshList]);

  const removeSession = useCallback((id) => {
    deleteSession(id);
    setCurrentSession(prev => (prev?.id === id ? null : prev));
    refreshList();
  }, [refreshList]);

  // Flush any pending save on unmount
  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
        if (currentSession) _save(currentSession.id, currentSession);
      }
    };
  }, [currentSession]);

  return {
    currentSession,
    recentSessions,
    createNewSession,
    restoreSession,
    updateSession,
    renameSession,
    removeSession,
    refreshList,
  };
}
