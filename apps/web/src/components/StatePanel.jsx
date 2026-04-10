import { useState, useCallback } from 'react';
import { SLOT_CONFIG, getNestedValue } from '../slotConfig.js';

/**
 * StatePanel — live decor state with editable chips.
 * New design: gold/charcoal, ghost borders, highlights active slot.
 */

const TOP_LEVEL_SLOTS = [
  "primary_colors",
  "types_of_flowers",
  "decor_lights",
  "chandeliers",
  "props",
  "selfie_booth_decor",
  "hall_decor",
];

const ENTRANCE_KEYS = [
  "entrance_decor.foyer",
  "entrance_decor.garlands",
  "entrance_decor.name_board",
  "entrance_decor.top_decor_at_entrance",
];

function slotLabel(slotKey) {
  return SLOT_CONFIG[slotKey]?.label ?? slotKey.split(".").pop().replace(/_/g, " ");
}

export default function StatePanel({ state, currentSlot, onStateUpdate }) {
  const isActive = (slotKey) => slotKey === currentSlot;

  const getItems = (slotKey) => {
    if (!state) return [];
    const val = getNestedValue(state, slotKey);
    return Array.isArray(val) ? val : val ? [String(val)] : [];
  };

  return (
    <div className="state-panel">
      <div className="state-panel__header">
        <span className="state-panel__title">Decor State</span>
        <span className="state-panel__badge">Live</span>
      </div>

      {!state ? (
        <div className="state-panel__content">
          <p className="state-section__empty">Waiting for session…</p>
        </div>
      ) : (
        <div className="state-panel__content">
          {/* Top-level array slots */}
          {TOP_LEVEL_SLOTS.map(slotKey => (
            <ChipSection
              key={slotKey}
              label={slotLabel(slotKey)}
              items={getItems(slotKey)}
              active={isActive(slotKey)}
              onAdd={v => onStateUpdate('add', slotKey, v)}
              onRemove={v => onStateUpdate('remove', slotKey, v)}
            />
          ))}

          {/* Entrance decor group */}
          <div className="state-section">
            <div
              className="state-section__title"
              style={{ color: 'var(--primary)', marginBottom: 'var(--space-3)' }}
            >
              Entrance
            </div>
            {ENTRANCE_KEYS.map(slotKey => (
              <ChipSection
                key={slotKey}
                label={slotLabel(slotKey)}
                items={getItems(slotKey)}
                active={isActive(slotKey)}
                nested
                onAdd={v => onStateUpdate('add', slotKey, v)}
                onRemove={v => onStateUpdate('remove', slotKey, v)}
              />
            ))}
          </div>

          {/* Backdrop */}
          <div className="state-section">
            <div
              className={`state-section__title ${isActive('backdrop_decor.types') ? 'state-section--active' : ''}`}
              style={{ color: isActive('backdrop_decor.types') ? 'var(--primary)' : undefined }}
            >
              Backdrop
              {state.backdrop_decor?.enabled && (
                <span style={{ marginLeft: 8, color: 'var(--success)', fontSize: '0.6rem' }}>✓</span>
              )}
            </div>
            <ChipSection
              label=""
              items={getItems('backdrop_decor.types')}
              active={isActive('backdrop_decor.types')}
              nested
              onAdd={v => onStateUpdate('add', 'backdrop_decor.types', v)}
              onRemove={v => onStateUpdate('remove', 'backdrop_decor.types', v)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function ChipSection({ label, items, active, nested, onAdd, onRemove }) {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = useCallback(() => {
    const v = inputValue.trim();
    if (v) { onAdd(v); setInputValue(''); }
  }, [inputValue, onAdd]);

  const handleKey = useCallback((e) => {
    if (e.key === 'Enter') handleAdd();
  }, [handleAdd]);

  return (
    <div
      className={`state-section${active ? ' state-section--active' : ''}${nested ? ' state-section--nested' : ''}`}
    >
      {label && <div className="state-section__title">{label}</div>}
      <div className="state-section__chips">
        {items.map((item, i) => (
          <span key={`${item}-${i}`} className={`chip${active ? ' chip--gold' : ''}`}>
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
        {items.length === 0 && !active && (
          <span className="state-section__empty">—</span>
        )}
        <span className="chip-add">
          <input
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKey}
            placeholder="+ add"
          />
        </span>
      </div>
    </div>
  );
}
