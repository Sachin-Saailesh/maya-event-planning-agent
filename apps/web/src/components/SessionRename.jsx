import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * SessionRename — inline editable session title shown in AppHeader.
 *
 * Single click to open edit mode; Enter or blur to confirm; Escape to cancel.
 * Shows custom name if set, otherwise auto-generated name.
 */
export default function SessionRename({ autoName, customName, onRename }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const inputRef = useRef(null);

  const displayName = customName || autoName || 'New Session';

  const startEdit = useCallback(() => {
    setDraft(displayName);
    setEditing(true);
  }, [displayName]);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const commit = useCallback(() => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== displayName) {
      onRename(trimmed);
    }
    setEditing(false);
  }, [draft, displayName, onRename]);

  const cancel = useCallback(() => {
    setEditing(false);
    setDraft('');
  }, []);

  const handleKey = useCallback((e) => {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') cancel();
  }, [commit, cancel]);

  if (editing) {
    return (
      <input
        ref={inputRef}
        className="session-name-input"
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={handleKey}
        maxLength={60}
        aria-label="Session name"
      />
    );
  }

  return (
    <button
      className="session-name-btn"
      onClick={startEdit}
      title="Click to rename session"
    >
      {displayName}
      <span className="session-name-edit-icon">✎</span>
    </button>
  );
}
