import { useRef, useEffect } from 'react';

/**
 * Transcript panel — left column of the voice session.
 * Shows Maya and user messages with the Stitch design language.
 */
export default function Transcript({ transcript, partialText }) {
  const listRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcript, partialText]);

  return (
    <div className="transcript-panel">
      <div className="transcript-panel__header">
        <span className="transcript-panel__title">Conversation</span>
      </div>

      <div className="transcript-panel__list" ref={listRef}>
        {transcript.length === 0 && !partialText && (
          <div className="transcript-empty">
            Maya will begin shortly…
          </div>
        )}

        {transcript.map((entry, i) => {
          // Skip system entries that are too verbose (e.g. barge-in notes)
          const isSystem = entry.speaker === 'system';
          return (
            <div
              key={i}
              className={`transcript-entry transcript-entry--${isSystem ? 'system' : entry.speaker}`}
            >
              {!isSystem && (
                <span className="transcript-entry__label">
                  {entry.speaker === 'maya' ? 'Maya' : 'You'}
                </span>
              )}
              <div className="transcript-entry__bubble">{entry.text}</div>
            </div>
          );
        })}

        {partialText && (
          <div className="transcript-entry transcript-entry--user">
            <span className="transcript-entry__label">You</span>
            <div className="transcript-partial">
              <span className="loading-dots">
                <span /><span /><span />
              </span>
              <span style={{ marginLeft: 6 }}>{partialText}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
