import { getNestedValue } from '../slotConfig.js';
import { downloadImage } from '../services/imageGeneration.js';

/**
 * Visualization — final fullscreen result screen.
 *
 * Shows:
 *  - Full-screen hall gradient (placeholder until image generation is wired)
 *  - Left sidebar with hall name + decor summary
 *  - Bottom action strip: Regenerate, Change Hall, Edit Decor, Export
 */

const DECOR_ROWS = [
  { key: 'primary_colors',     label: 'Colours' },
  { key: 'types_of_flowers',   label: 'Flowers' },
  { key: 'decor_lights',       label: 'Lighting' },
  { key: 'chandeliers',        label: 'Chandeliers' },
  { key: 'backdrop_decor.types', label: 'Backdrop' },
];

function firstValue(state, slotKey) {
  const val = getNestedValue(state, slotKey);
  if (!val) return null;
  if (Array.isArray(val)) return val.length > 0 ? val[0] : null;
  return String(val);
}

function allValues(state, slotKey) {
  const val = getNestedValue(state, slotKey);
  if (!val) return [];
  return Array.isArray(val) ? val : [String(val)];
}

export default function Visualization({
  state,
  hall,
  generatedImageUrl,
  onGenerate,
  onChangeHall,
  onEditDecor,
  onExport,
}) {
  const hallName = hall?.name ?? 'Selected Hall';
  const hallEmoji = hall?.emoji ?? '🏛';
  const hallCss = hall?.cssClass ?? 'hall-visual-grand';

  return (
    <div className="viz-screen">
      {/* Full-screen background — generated image or gradient placeholder */}
      <div className="viz-bg">
        {generatedImageUrl ? (
          <img
            src={generatedImageUrl}
            alt={`Decorated ${hallName}`}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : (
          <div
            className={`viz-bg__image ${hallCss}`}
            style={{ width: '100%', height: '100%' }}
          />
        )}
        <div className="viz-bg__overlay" />

        {/* Subtle ambient lights */}
        <div style={{
          position: 'absolute', top: '20%', left: '25%',
          width: 400, height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(242,202,80,0.06) 0%, transparent 70%)',
          filter: 'blur(80px)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', bottom: '20%', right: '20%',
          width: 500, height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(98,37,153,0.08) 0%, transparent 70%)',
          filter: 'blur(100px)',
          pointerEvents: 'none',
        }} />
      </div>

      {/* Left sidebar */}
      <aside className="viz-sidebar">
        {/* Hall + decor summary */}
        <div className="viz-summary-card glass">
          <div className="viz-summary-card__hall">
            <div className="viz-summary-card__hall-icon">{hallEmoji}</div>
            <div>
              <div className="viz-summary-card__hall-name">{hallName}</div>
              <div className="viz-summary-card__hall-sub">Visualization Phase</div>
            </div>
          </div>

          <div style={{
            fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.2em',
            textTransform: 'uppercase', color: 'var(--on-surface-muted)',
            marginBottom: 'var(--space-4)',
          }}>
            Core Decor Palette
          </div>

          <div className="viz-summary-rows">
            {DECOR_ROWS.map(({ key, label }) => {
              const val = firstValue(state, key);
              if (!val) return null;
              return (
                <div key={key} className="viz-summary-row">
                  <span className="viz-summary-row__label">{label}</span>
                  <span className="viz-summary-row__value">{val}</span>
                </div>
              );
            })}
          </div>

          {/* Mood tags */}
          <div style={{
            marginTop: 'var(--space-5)', paddingTop: 'var(--space-5)',
            borderTop: '1px solid var(--outline-variant)',
          }}>
            <div style={{
              fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.2em',
              textTransform: 'uppercase', color: 'var(--on-surface-muted)',
              marginBottom: 'var(--space-3)',
            }}>
              Atmospheric Tone
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              <span style={{
                padding: '3px 10px', borderRadius: 'var(--radius-full)',
                background: 'var(--surface-highest)', fontSize: '0.62rem',
                fontWeight: 700, color: 'var(--tertiary)', letterSpacing: '0.1em',
              }}>CINEMATIC</span>
              <span style={{
                padding: '3px 10px', borderRadius: 'var(--radius-full)',
                background: 'var(--surface-highest)', fontSize: '0.62rem',
                fontWeight: 700, color: 'var(--secondary)', letterSpacing: '0.1em',
              }}>ROYAL</span>
            </div>
          </div>
        </div>

        {/* Maya presence badge */}
        <div
          className="glass"
          style={{
            padding: 'var(--space-3) var(--space-5)',
            borderRadius: 'var(--radius-full)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
          }}
        >
          <span style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'var(--primary-glow-soft)',
            border: '1px solid rgba(242,202,80,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1rem',
            animation: 'dotPulse 2.5s infinite',
          }}>✦</span>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--on-surface)' }}>
              Maya is observing
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--on-surface-muted)' }}>
              "This composition feels harmonious."
            </div>
          </div>
        </div>
      </aside>

      {/* Center label */}
      <div className="viz-label">
        <div className="viz-label__title">{hallName}</div>
        <div className="viz-label__badge">Your Decorated Vision</div>
      </div>

      {/* Bottom action bar */}
      <div className="viz-actions">
        <button className="viz-actions__btn" onClick={onGenerate}>
          {generatedImageUrl ? '↺ Regenerate' : '✦ Generate Image'}
        </button>
        <button className="viz-actions__btn" onClick={onChangeHall}>
          🏛 Change Hall
        </button>
        <button className="viz-actions__btn" onClick={onEditDecor}>
          ✎ Edit Decor
        </button>

        {/* Image download — visible only once image is generated */}
        {generatedImageUrl && (
          <>
            <div className="viz-actions__divider" />
            <button
              className="viz-actions__btn"
              onClick={() => downloadImage(generatedImageUrl, 'png', `maya-${hallName.toLowerCase().replace(/\s+/g, '-')}`)}
              title="Download as PNG"
            >
              ↓ PNG
            </button>
            <button
              className="viz-actions__btn"
              onClick={() => downloadImage(generatedImageUrl, 'jpg', `maya-${hallName.toLowerCase().replace(/\s+/g, '-')}`)}
              title="Download as JPG"
            >
              ↓ JPG
            </button>
          </>
        )}

        <div className="viz-actions__divider" />
        <button
          className="viz-actions__btn"
          onClick={onExport}
          style={{
            background: 'linear-gradient(135deg, var(--primary), var(--primary-dark))',
            color: 'var(--on-primary)',
            fontWeight: 700,
            letterSpacing: '0.08em',
          }}
        >
          ↓ Export Brief
        </button>
      </div>
    </div>
  );
}
