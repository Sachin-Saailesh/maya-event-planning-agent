import { getNestedValue } from '../slotConfig.js';

/**
 * ReviewScreen — post-slot-filling review step.
 *
 * Shows all collected decoration choices in a clean grid.
 * User can go back to edit, or proceed to hall selection.
 */

const REVIEW_SECTIONS = [
  { key: 'primary_colors',      label: 'Primary Colours' },
  { key: 'types_of_flowers',    label: 'Flowers' },
  { key: 'decor_lights',        label: 'Lighting' },
  { key: 'chandeliers',         label: 'Chandeliers' },
  { key: 'props',               label: 'Props' },
  { key: 'selfie_booth_decor',  label: 'Selfie Booth' },
  { key: 'hall_decor',          label: 'Hall Decor' },
];

const ENTRANCE_KEYS = [
  { key: 'entrance_decor.foyer',                   label: 'Foyer' },
  { key: 'entrance_decor.garlands',                label: 'Garlands' },
  { key: 'entrance_decor.name_board',              label: 'Name Board' },
  { key: 'entrance_decor.top_decor_at_entrance',   label: 'Top Decor' },
];

function getItems(state, slotKey) {
  if (!state) return [];
  const val = getNestedValue(state, slotKey);
  return Array.isArray(val) ? val : val ? [String(val)] : [];
}

function ReviewCard({ label, items, onEdit }) {
  const hasItems = items && items.length > 0;
  return (
    <div className="review-card">
      <div className="review-card__category">
        <span>{label}</span>
        {hasItems && <span className="review-card__check">✓</span>}
      </div>
      {hasItems ? (
        <div className="review-card__values">
          {items.map((item, i) => (
            <span key={i} className="chip chip--gold">{item}</span>
          ))}
        </div>
      ) : (
        <span className="review-card__empty">Not specified</span>
      )}
    </div>
  );
}

export default function ReviewScreen({ state, onEdit, onProceed }) {
  // Gather entrance items
  const entranceItems = ENTRANCE_KEYS.flatMap(({ key, label }) => {
    const items = getItems(state, key);
    return items.map(v => `${label}: ${v}`);
  });

  const backdropItems = state?.backdrop_decor?.enabled
    ? (state.backdrop_decor.types || [])
    : [];

  return (
    <>
      {/* Ambient background */}
      <div className="ambient-bg">
        <div className="ambient-bg__glow ambient-bg__glow--gold" />
        <div className="ambient-bg__glow ambient-bg__glow--purple" />
      </div>

      <div className="review-screen">
        <div className="review-screen__inner">
          {/* Header */}
          <div className="review-screen__hero">
            <div className="review-screen__eyebrow">Step 2 of 3 — Review</div>
            <h1 className="review-screen__title">
              Your vision is coming together beautifully.
            </h1>
            <p className="review-screen__sub">
              Would you like to make any changes, or shall we proceed to
              visualize this in a hall?
            </p>
          </div>

          {/* Selection grid */}
          <div className="review-grid">
            {REVIEW_SECTIONS.map(({ key, label }) => (
              <ReviewCard
                key={key}
                label={label}
                items={getItems(state, key)}
                onEdit={onEdit}
              />
            ))}

            {/* Entrance group (wide card) */}
            {entranceItems.length > 0 && (
              <div className="review-card review-card--wide">
                <div className="review-card__category">
                  <span>Entrance Decoration</span>
                  <span className="review-card__check">✓</span>
                </div>
                <div className="review-card__values">
                  {entranceItems.map((item, i) => (
                    <span key={i} className="chip chip--gold">{item}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Backdrop */}
            {backdropItems.length > 0 && (
              <ReviewCard
                label="Stage Backdrop"
                items={backdropItems}
                onEdit={onEdit}
              />
            )}
          </div>

          {/* Actions */}
          <div className="review-actions">
            <button className="btn-outline" onClick={onEdit}>
              ✎ Edit Selections
            </button>
            <button className="btn-gold" onClick={onProceed}>
              Proceed to Hall Selection →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
