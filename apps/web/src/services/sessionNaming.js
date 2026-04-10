/**
 * Session auto-naming utility.
 *
 * Generates a short, elegant title from the decor state.
 * Called whenever enough data is present to produce a meaningful name.
 * Never overwrites a custom (user-set) name.
 *
 * Example outputs:
 *   "Gold & Rose Floral Entrance"
 *   "Royal Maroon Stage Backdrop"
 *   "Ivory Jasmine & Crystal Hall"
 *   "Traditional Marigold Entrance"
 */

const ADJECTIVES = {
  gold:      'Golden',
  golden:    'Golden',
  maroon:    'Royal Maroon',
  red:       'Crimson',
  white:     'Pure White',
  cream:     'Ivory Cream',
  ivory:     'Ivory',
  pink:      'Blush Pink',
  rose:      'Rose',
  'rose gold':'Rose Gold',
  blush:     'Blush',
  peach:     'Peach',
  orange:    'Saffron',
  green:     'Emerald',
  teal:      'Teal',
  blue:      'Sapphire',
  navy:      'Navy',
  purple:    'Royal Purple',
  lavender:  'Lavender',
  silver:    'Silver',
  bronze:    'Bronze',
  copper:    'Copper',
  champagne: 'Champagne',
  burgundy:  'Burgundy',
  emerald:   'Emerald',
  ruby:      'Ruby',
};

function titleCase(str) {
  return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function colorAdjective(color) {
  return ADJECTIVES[color?.toLowerCase()] || titleCase(color || '');
}

/**
 * Generate an auto name from state.
 * Returns null if not enough data yet (< 2 slots filled).
 */
export function generateSessionName(state) {
  if (!state) return null;

  const colors = state.primary_colors || [];
  const flowers = state.types_of_flowers || [];
  const backdrop = state.backdrop_decor || {};
  const backdropTypes = backdrop.enabled ? (backdrop.types || []) : [];
  const chandeliers = state.chandeliers || [];
  const lights = state.decor_lights || [];
  const entrance = state.entrance_decor || {};
  const foyer = entrance.foyer || [];

  const filledCount = [colors, flowers, backdropTypes, chandeliers].filter(a => a.length > 0).length;
  if (filledCount < 1 && foyer.length === 0) return null;

  const parts = [];

  // Lead with up to 2 color adjectives
  if (colors.length > 0) {
    const c1 = colorAdjective(colors[0]);
    const c2 = colors[1] ? colorAdjective(colors[1]) : null;
    parts.push(c2 ? `${c1} & ${c2}` : c1);
  }

  // Key noun — most distinctive feature
  if (backdropTypes.includes('flowers') || backdropTypes.includes('flower_lights')) {
    const flowerName = flowers[0] ? titleCase(flowers[0]) : 'Floral';
    parts.push(flowerName);
    parts.push('Backdrop');
  } else if (flowers.length > 0) {
    parts.push(titleCase(flowers[0]));
    if (chandeliers.length > 0) {
      parts.push('& Crystal');
    }
    parts.push(foyer.length > 0 ? 'Entrance' : 'Hall');
  } else if (chandeliers.length > 0) {
    parts.push('Crystal');
    parts.push('Hall');
  } else if (lights.length > 0) {
    parts.push('Lit');
    parts.push('Hall');
  } else if (foyer.length > 0) {
    parts.push('Entrance');
  } else {
    parts.push('Wedding Hall');
  }

  const name = parts.join(' ');
  return name.length > 50 ? name.slice(0, 47) + '…' : name;
}

/**
 * Decide whether the auto-name should be updated.
 * Returns true if we have more info than when the last name was generated.
 */
export function shouldUpdateAutoName(currentAutoName, newName) {
  if (!newName) return false;
  if (!currentAutoName || currentAutoName === 'New Wedding Decor Session') return true;
  // Only update if the new name is more descriptive (longer / different)
  return newName !== currentAutoName && newName.length > currentAutoName.length;
}
