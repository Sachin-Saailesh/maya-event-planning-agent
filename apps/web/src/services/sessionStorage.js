/**
 * Session persistence service — localStorage-backed with schema versioning.
 *
 * Session schema v1:
 * {
 *   id: string,
 *   schemaVersion: 1,
 *   createdAt: number,
 *   updatedAt: number,
 *   ownerId: string | null,   // null = guest
 *   ownerType: 'guest' | 'user',
 *   stage: string,
 *   state: object,
 *   transcript: array,
 *   selectedHall: object | null,
 *   generatedImageUrl: string | null,
 *   autoName: string,
 *   customName: string | null,
 * }
 */

const SESSIONS_KEY = 'maya_sessions_v1';
const CURRENT_ID_KEY = 'maya_current_session_id';
const SCHEMA_VERSION = 1;

// ── Low-level storage helpers ──────────────────────────────────

function loadAll() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === 'object' && parsed !== null ? parsed : {};
  } catch (_) {
    return {};
  }
}

function saveAll(sessions) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  } catch (_) {}
}

// ── Public API ─────────────────────────────────────────────────

export function createSession(id, ownerId = null) {
  const sessions = loadAll();
  const now = Date.now();
  const session = {
    id,
    schemaVersion: SCHEMA_VERSION,
    createdAt: now,
    updatedAt: now,
    ownerId,
    ownerType: ownerId ? 'user' : 'guest',
    stage: 'session',
    state: null,
    transcript: [],
    selectedHall: null,
    generatedImageUrl: null,
    autoName: 'New Wedding Decor Session',
    customName: null,
  };
  sessions[id] = session;
  saveAll(sessions);
  setCurrentSessionId(id);
  return session;
}

export function getSession(id) {
  const sessions = loadAll();
  const s = sessions[id];
  if (!s || s.schemaVersion !== SCHEMA_VERSION) return null;
  return s;
}

export function saveSession(id, updates) {
  const sessions = loadAll();
  if (!sessions[id]) return;
  sessions[id] = { ...sessions[id], ...updates, updatedAt: Date.now() };
  saveAll(sessions);
}

export function getAllSessions() {
  const sessions = loadAll();
  return Object.values(sessions)
    .filter(s => s && s.schemaVersion === SCHEMA_VERSION)
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getSessionsForUser(ownerId) {
  return getAllSessions().filter(s => s.ownerId === ownerId);
}

export function getGuestSessions() {
  return getAllSessions().filter(s => s.ownerType === 'guest');
}

export function deleteSession(id) {
  const sessions = loadAll();
  delete sessions[id];
  saveAll(sessions);
}

export function setCurrentSessionId(id) {
  try {
    localStorage.setItem(CURRENT_ID_KEY, id || '');
  } catch (_) {}
}

export function getCurrentSessionId() {
  try {
    return localStorage.getItem(CURRENT_ID_KEY) || null;
  } catch (_) {
    return null;
  }
}

/**
 * Migrate a guest session to an authenticated user.
 * Updates ownerId/ownerType in-place; does not duplicate.
 */
export function migrateGuestSession(sessionId, userId) {
  const sessions = loadAll();
  const s = sessions[sessionId];
  if (!s) return;
  // Only migrate if currently a guest session
  if (s.ownerType === 'guest') {
    sessions[sessionId] = { ...s, ownerId: userId, ownerType: 'user', updatedAt: Date.now() };
    saveAll(sessions);
  }
}

/**
 * Migrate ALL guest sessions to a user (called on sign-in).
 */
export function migrateAllGuestSessions(userId) {
  const sessions = loadAll();
  let changed = false;
  for (const id of Object.keys(sessions)) {
    if (sessions[id]?.ownerType === 'guest') {
      sessions[id] = { ...sessions[id], ownerId: userId, ownerType: 'user', updatedAt: Date.now() };
      changed = true;
    }
  }
  if (changed) saveAll(sessions);
}
