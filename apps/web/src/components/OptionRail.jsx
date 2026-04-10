import { useEffect, useState, useCallback } from 'react';
import { SLOT_CONFIG } from '../slotConfig.js';

/**
 * OptionRail — contextual option cards for the current slot.
 *
 * Cards are interactive: clicking (or pressing Enter/Space) sends the
 * option label as user input via `onSelect(label)`.
 *
 * Selected state is local and resets whenever the slot changes.
 */
export default function OptionRail({ currentSlot, onSelect }) {
  const [visible, setVisible] = useState(false);
  const [displayedSlot, setDisplayedSlot] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Crossfade: hide first, swap slot, then show
  useEffect(() => {
    if (!currentSlot) {
      setVisible(false);
      return;
    }
    if (currentSlot !== displayedSlot) {
      setVisible(false);
      const t = setTimeout(() => {
        setDisplayedSlot(currentSlot);
        setSelectedIds(new Set()); // reset selection on slot change
        setVisible(true);
      }, 180);
      return () => clearTimeout(t);
    }
    setVisible(true);
  }, [currentSlot]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = useCallback((opt) => {
    setSelectedIds(prev => new Set([...prev, opt.id]));
    onSelect?.(opt.label);
  }, [onSelect]);

  const config = displayedSlot ? SLOT_CONFIG[displayedSlot] : null;
  if (!config) return null;

  return (
    <div
      className="option-rail"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
        transition: 'opacity 0.3s ease, transform 0.3s ease',
        pointerEvents: visible ? 'auto' : 'none',
      }}
    >
      <div className="option-rail__label">Choose from</div>
      <div className="option-rail__cards">
        {config.options.map((opt, i) => {
          const isSelected = selectedIds.has(opt.id);
          return (
            <div
              key={opt.id}
              className={`option-card${isSelected ? ' option-card--active' : ''}`}
              style={{ animationDelay: `${i * 0.06}s` }}
              title={opt.label}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              onClick={() => handleSelect(opt)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(opt);
                }
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: opt.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.1rem',
                  marginBottom: 4,
                  flexShrink: 0,
                }}
              >
                {opt.emoji}
              </div>
              <div className="option-card__label">{opt.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
