import { useRef, useEffect } from 'react';

/**
 * Live transcript panel showing Maya and user messages.
 */
export default function Transcript({ transcript, partialText }) {
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [transcript, partialText]);

  return (
    <div className="transcript">
      <div className="transcript__header">Conversation</div>
      <div className="transcript__list" ref={listRef}>
        {transcript.map((entry, i) => (
          <div
            key={i}
            className={`transcript__entry transcript__entry--${entry.speaker}`}
          >
            <span className="transcript__speaker">
              {entry.speaker === 'maya' ? '✦ Maya' : '● You'}
            </span>
            <div className="transcript__bubble">{entry.text}</div>
          </div>
        ))}

        {partialText && (
          <div className="transcript__partial">
            <span className="loading-dots">
              <span></span><span></span><span></span>
            </span>
            {' '}{partialText}
          </div>
        )}

        {transcript.length === 0 && !partialText && (
          <div className="transcript__partial">
            Waiting for Maya to start the conversation...
          </div>
        )}
      </div>
    </div>
  );
}
