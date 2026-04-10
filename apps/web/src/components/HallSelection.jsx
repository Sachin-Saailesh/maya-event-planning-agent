import { useState } from 'react';
import { HALL_CONFIG } from '../slotConfig.js';

/**
 * HallSelection — choose which hall to visualize the decoration in.
 * Featured card (left, 2 rows) + two side cards layout.
 */
export default function HallSelection({ onSelect, onBack }) {
  const [selected, setSelected] = useState(null);

  const [featured, ...rest] = HALL_CONFIG;

  const handleConfirm = () => {
    if (!selected) return;
    onSelect(selected);
  };

  return (
    <>
      <div className="ambient-bg">
        <div className="ambient-bg__glow ambient-bg__glow--gold" />
        <div className="ambient-bg__glow ambient-bg__glow--purple" />
      </div>

      <div className="hall-screen">
        <div className="hall-screen__inner">
          {/* Prompt */}
          <div className="hall-screen__prompt">
            <div className="hall-screen__prompt-eyebrow">Step 3 of 3 — Hall</div>
            <h1 className="hall-screen__title">
              "Which of these <em>prestigious halls</em> would you like to see
              your decorations in?"
            </h1>
          </div>

          {/* Hall grid */}
          <div className="hall-grid">
            {/* Featured hall */}
            <HallCard
              hall={featured}
              selected={selected?.id === featured.id}
              featured
              onSelect={setSelected}
            />

            {/* Side cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              {rest.map(hall => (
                <HallCard
                  key={hall.id}
                  hall={hall}
                  selected={selected?.id === hall.id}
                  onSelect={setSelected}
                />
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="hall-actions">
            <button className="btn-ghost" onClick={onBack}>← Back to Review</button>
            <button
              className="btn-gold"
              onClick={handleConfirm}
              disabled={!selected}
              style={{ opacity: selected ? 1 : 0.4 }}
            >
              Visualize in {selected ? selected.name : 'selected hall'} →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function HallCard({ hall, selected, featured, onSelect }) {
  return (
    <div
      className={`hall-card${featured ? ' hall-card--featured' : ' hall-card--small'}${selected ? ' hall-card--selected' : ''}`}
      onClick={() => onSelect(hall)}
    >
      {/* Gradient placeholder background */}
      <div className={`hall-card__bg ${hall.cssClass}`} />
      <div className="hall-card__overlay" />

      {selected && (
        <div className="hall-card__selected-badge">Selected</div>
      )}

      <div className="hall-card__content">
        <span className="hall-card__tag">{hall.tag}</span>
        <h2 className="hall-card__name">
          <span style={{ marginRight: 8 }}>{hall.emoji}</span>
          {hall.name}
        </h2>
        <div className="hall-card__meta">
          <span>👥 {hall.capacity}</span>
          <span>✨ {hall.mood}</span>
        </div>
        {featured && (
          <p style={{
            marginTop: 'var(--space-2)',
            fontSize: '0.78rem',
            color: 'rgba(229,226,225,0.55)',
            lineHeight: 1.5,
          }}>
            {hall.description}
          </p>
        )}
      </div>
    </div>
  );
}
