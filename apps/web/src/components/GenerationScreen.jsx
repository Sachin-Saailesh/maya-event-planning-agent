import { useEffect, useState } from 'react';
import { downloadImage } from '../services/imageGeneration.js';

/**
 * GenerationScreen — premium loading state while Nano Banana generates
 * the decorated hall image.
 *
 * Props:
 *   status: 'generating' | 'complete' | 'error'
 *   imageUrl: string | null
 *   errorMessage: string | null
 *   hallName: string
 *   onRetry: fn
 *   onEditDecor: fn
 *   onChangeHall: fn
 */

const STATUS_LINES = [
  'Creating your wedding hall visualization…',
  'Arranging flowers, lights, and decor…',
  'Composing the backdrop and stage…',
  'Placing chandeliers and entrance garlands…',
  'Generating your final styled preview…',
  'Adding the finishing touches…',
];

export default function GenerationScreen({
  status,
  imageUrl,
  errorMessage,
  hallName,
  onRetry,
  onEditDecor,
  onChangeHall,
}) {
  const [lineIndex, setLineIndex] = useState(0);

  // Cycle through status lines while generating
  useEffect(() => {
    if (status !== 'generating') return;
    const interval = setInterval(() => {
      setLineIndex(i => (i + 1) % STATUS_LINES.length);
    }, 3200);
    return () => clearInterval(interval);
  }, [status]);

  if (status === 'error') {
    return (
      <>
        <div className="ambient-bg">
          <div className="ambient-bg__glow ambient-bg__glow--gold" />
          <div className="ambient-bg__glow ambient-bg__glow--purple" />
        </div>
        <div className="generation-screen">
          <div className="generation-frame generation-frame--error">
            <div className="gen-error-icon">⚠</div>
            <div className="gen-error-title">Visualization failed</div>
            <div className="gen-error-desc">
              {errorMessage || 'Something went wrong generating the image.'}
            </div>
          </div>
          <div className="generation-actions">
            <button className="btn-gold" onClick={onRetry}>Retry Generation</button>
            <button className="btn-outline" onClick={onChangeHall}>Change Hall</button>
            <button className="btn-outline" onClick={onEditDecor}>Edit Decor</button>
          </div>
        </div>
      </>
    );
  }

  if (status === 'complete' && imageUrl) {
    const slug = hallName.toLowerCase().replace(/\s+/g, '-');
    return (
      <>
        <div className="ambient-bg">
          <div className="ambient-bg__glow ambient-bg__glow--gold" />
          <div className="ambient-bg__glow ambient-bg__glow--purple" />
        </div>
        <div className="generation-screen generation-screen--complete">
          <div className="generation-eyebrow">Your Visualization is Ready</div>
          <h1 className="generation-title">{hallName}</h1>
          <div className="generation-image-wrap">
            <img
              src={imageUrl}
              alt={`Decorated ${hallName}`}
              className="generation-image"
            />
          </div>
          <div className="generation-actions">
            <button className="btn-outline" onClick={onEditDecor}>Edit Decor</button>
            <button className="btn-outline" onClick={onChangeHall}>Change Hall</button>
          </div>
          {/* Image download row */}
          <div className="gen-download-row">
            <span className="gen-download-label">Download image</span>
            <button
              className="gen-download-btn"
              onClick={() => downloadImage(imageUrl, 'png', `maya-${slug}`)}
            >
              ↓ PNG
            </button>
            <button
              className="gen-download-btn"
              onClick={() => downloadImage(imageUrl, 'jpg', `maya-${slug}`)}
            >
              ↓ JPG
            </button>
          </div>
        </div>
      </>
    );
  }

  // Generating state
  return (
    <>
      <div className="ambient-bg">
        <div className="ambient-bg__glow ambient-bg__glow--gold" />
        <div className="ambient-bg__glow ambient-bg__glow--purple" />
      </div>
      <div className="generation-screen">
        <div className="generation-eyebrow">Crafting Your Vision</div>
        <h1 className="generation-title">{hallName}</h1>

        {/* Placeholder frame with shimmer */}
        <div className="generation-frame">
          <div className="gen-shimmer" />
          <div className="gen-placeholder-content">
            <div className="gen-placeholder-icon">✦</div>
          </div>
        </div>

        {/* Status line */}
        <div className="generation-status-line">
          {STATUS_LINES[lineIndex]}
        </div>

        <div className="gen-progress-track">
          <div className="gen-progress-bar" />
        </div>
      </div>
    </>
  );
}
