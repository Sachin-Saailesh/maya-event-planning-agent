/**
 * Export Brief — shareable decoration summary (human-readable + JSON).
 */
export default function ExportBrief({ state, onBack }) {
  if (!state) return null;

  const sections = [
    { key: 'primary_colors', label: 'Primary Colours' },
    { key: 'types_of_flowers', label: 'Flowers' },
    { key: 'decor_lights', label: 'Decorative Lighting' },
    { key: 'chandeliers', label: 'Chandeliers' },
    { key: 'props', label: 'Props' },
    { key: 'selfie_booth_decor', label: 'Selfie Booth' },
    { key: 'hall_decor', label: 'Hall Decoration' },
  ];

  const entranceSections = [
    { key: 'foyer', label: 'Foyer' },
    { key: 'garlands', label: 'Garlands' },
    { key: 'name_board', label: 'Name Board' },
    { key: 'top_decor_at_entrance', label: 'Top Decor at Entrance' },
  ];

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(state, null, 2));
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="export">
      <div className="export__header">
        <button className="export__back" onClick={onBack}>← Back to session</button>
      </div>

      <div className="export__card">
        <h1 className="export__title">Decoration Brief</h1>
        <p className="export__subtitle">South Indian Wedding — Hall Decoration Plan</p>

        {sections.map(({ key, label }) => {
          const items = state[key] || [];
          if (items.length === 0) return null;
          return (
            <div key={key} className="export__section">
              <h3 className="export__section-title">{label}</h3>
              <div className="export__items">
                {items.map((item, i) => (
                  <span key={i} className="export__item">{item}</span>
                ))}
              </div>
            </div>
          );
        })}

        {/* Entrance */}
        {state.entrance_decor && (
          <>
            <div className="export__section">
              <h3 className="export__section-title">Entrance Decoration</h3>
            </div>
            {entranceSections.map(({ key, label }) => {
              const items = state.entrance_decor?.[key] || [];
              if (items.length === 0) return null;
              return (
                <div key={key} className="export__section" style={{ paddingLeft: '1rem' }}>
                  <h3 className="export__section-title" style={{ fontSize: '0.7rem' }}>{label}</h3>
                  <div className="export__items">
                    {items.map((item, i) => (
                      <span key={i} className="export__item">{item}</span>
                    ))}
                  </div>
                </div>
              );
            })}
          </>
        )}

        {/* Backdrop */}
        {state.backdrop_decor?.enabled && (
          <div className="export__section">
            <h3 className="export__section-title">Backdrop</h3>
            <div className="export__items">
              {(state.backdrop_decor.types || []).map((t, i) => (
                <span key={i} className="export__item">{t}</span>
              ))}
            </div>
          </div>
        )}

        {/* Raw JSON */}
        <div className="export__json">
          <pre>{JSON.stringify(state, null, 2)}</pre>
        </div>

        <div className="export__actions">
          <button className="btn-secondary" onClick={handleCopy}>📋 Copy JSON</button>
          <button className="btn-secondary" onClick={handlePrint}>🖨 Print Brief</button>
        </div>
      </div>
    </div>
  );
}
