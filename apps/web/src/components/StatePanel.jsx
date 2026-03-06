import { useState, useCallback } from 'react';

/**
 * State panel with editable chips for all decoration fields.
 */

const FIELD_LABELS = {
  primary_colors: 'Primary Colours',
  types_of_flowers: 'Flowers',
  props: 'Props',
  chandeliers: 'Chandeliers',
  decor_lights: 'Decorative Lighting',
  hall_decor: 'Hall Decoration',
  selfie_booth_decor: 'Selfie Booth',
};

const ENTRANCE_LABELS = {
  foyer: 'Foyer',
  garlands: 'Garlands',
  name_board: 'Name Board',
  top_decor_at_entrance: 'Top Decor at Entrance',
};

export default function StatePanel({ state, onStateUpdate }) {
  if (!state) return (
    <div className="state-panel">
      <div className="state-panel__header">Decor State</div>
      <div className="state-panel__content">
        <p className="state-section__empty">No session active</p>
      </div>
    </div>
  );

  return (
    <div className="state-panel">
      <div className="state-panel__header">
        <span>Decor State</span>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Live</span>
      </div>
      <div className="state-panel__content">
        {/* Top-level array fields */}
        {Object.entries(FIELD_LABELS).map(([key, label]) => (
          <ChipSection
            key={key}
            label={label}
            items={state[key] || []}
            slot={key}
            onAdd={(val) => onStateUpdate('add', key, val)}
            onRemove={(val) => onStateUpdate('remove', key, val)}
          />
        ))}

        {/* Entrance decor */}
        <div className="state-section">
          <div className="state-section__title" style={{ color: 'var(--accent)', marginBottom: '0.75rem' }}>
            Entrance Decoration
          </div>
          {Object.entries(ENTRANCE_LABELS).map(([key, label]) => (
            <ChipSection
              key={`entrance_${key}`}
              label={label}
              items={state.entrance_decor?.[key] || []}
              slot={`entrance_decor.${key}`}
              onAdd={(val) => onStateUpdate('add', `entrance_decor.${key}`, val)}
              onRemove={(val) => onStateUpdate('remove', `entrance_decor.${key}`, val)}
              nested
            />
          ))}
        </div>

        {/* Backdrop */}
        <div className="state-section">
          <div className="state-section__title" style={{ color: 'var(--accent)' }}>
            Backdrop
          </div>
          <div style={{ marginBottom: '0.5rem' }}>
            <span className={`chip ${state.backdrop_decor?.enabled ? 'chip--active' : ''}`}>
              {state.backdrop_decor?.enabled ? '✓ Enabled' : '✗ Disabled'}
            </span>
          </div>
          <ChipSection
            label="Types"
            items={state.backdrop_decor?.types || []}
            slot="backdrop_decor.types"
            onAdd={(val) => onStateUpdate('add', 'backdrop_decor.types', val)}
            onRemove={(val) => onStateUpdate('remove', 'backdrop_decor.types', val)}
            nested
          />
        </div>
      </div>
    </div>
  );
}


function ChipSection({ label, items, slot, onAdd, onRemove, nested = false }) {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = useCallback(() => {
    const val = inputValue.trim();
    if (val) {
      onAdd(val);
      setInputValue('');
    }
  }, [inputValue, onAdd]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      handleAdd();
    }
  }, [handleAdd]);

  return (
    <div className="state-section" style={nested ? { marginLeft: '0.75rem', marginBottom: '0.75rem' } : {}}>
      <div className="state-section__title">{label}</div>
      <div className="state-section__chips">
        {items.map((item, i) => (
          <span key={`${item}-${i}`} className="chip chip--active">
            {item}
            <button
              className="chip__remove"
              onClick={() => onRemove(item)}
              title={`Remove ${item}`}
            >
              ✕
            </button>
          </span>
        ))}
        <span className="chip-add">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="+ add"
          />
        </span>
      </div>
    </div>
  );
}
