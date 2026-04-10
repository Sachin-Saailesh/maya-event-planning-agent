/**
 * Slot configuration — drives option visuals, labels, and contextual
 * hints shown in the OptionRail during each Maya question.
 *
 * No external image URLs. Each option gets a gradient color + emoji.
 */

export const SLOT_CONFIG = {
  primary_colors: {
    label: "Primary Colours",
    options: [
      { id: "gold",    label: "Temple Gold",   emoji: "✨", color: "linear-gradient(135deg,#3d2d00,#d4af37)" },
      { id: "maroon",  label: "Royal Maroon",  emoji: "🔴", color: "linear-gradient(135deg,#3d0000,#8b0000)" },
      { id: "ivory",   label: "Ivory & Cream", emoji: "🤍", color: "linear-gradient(135deg,#2a2820,#a09070)" },
      { id: "rose",    label: "Rose Gold",     emoji: "🌸", color: "linear-gradient(135deg,#3d2020,#e9c7c0)" },
      { id: "purple",  label: "Royal Purple",  emoji: "💜", color: "linear-gradient(135deg,#2c0050,#622599)" },
      { id: "emerald", label: "Emerald",        emoji: "💚", color: "linear-gradient(135deg,#001a0a,#228b22)" },
    ],
  },

  types_of_flowers: {
    label: "Flowers",
    options: [
      { id: "marigold",  label: "Marigold",  emoji: "🌻", color: "linear-gradient(135deg,#3d2000,#f5a623)" },
      { id: "jasmine",   label: "Jasmine",   emoji: "⚪",  color: "linear-gradient(135deg,#2a2820,#fffadc)" },
      { id: "rose",      label: "Roses",     emoji: "🌹", color: "linear-gradient(135deg,#3d0010,#dc143c)" },
      { id: "lily",      label: "Lily",      emoji: "🪷",  color: "linear-gradient(135deg,#3d0030,#ff69b4)" },
      { id: "lotus",     label: "Lotus",     emoji: "🪷",  color: "linear-gradient(135deg,#1a0030,#dda0dd)" },
      { id: "mogra",     label: "Mogra",     emoji: "🌼",  color: "linear-gradient(135deg,#1a1a1a,#fffadc)" },
    ],
  },

  "entrance_decor.foyer": {
    label: "Foyer Style",
    options: [
      { id: "floral_arch",    label: "Floral Arch",    emoji: "🌿", color: "linear-gradient(135deg,#001a0a,#3cb371)" },
      { id: "traditional",    label: "Trad. Pillars",  emoji: "🏛",  color: "linear-gradient(135deg,#2a1800,#d4af37)" },
      { id: "floral_carpet",  label: "Floral Carpet",  emoji: "🌺", color: "linear-gradient(135deg,#3d0010,#ff6347)" },
      { id: "lamp_entry",     label: "Lamp Entry",     emoji: "🪔",  color: "linear-gradient(135deg,#2a1800,#ffd700)" },
    ],
  },

  "entrance_decor.garlands": {
    label: "Entrance Garlands",
    options: [
      { id: "marigold_garland", label: "Marigold",     emoji: "🌻", color: "linear-gradient(135deg,#3d2000,#f5a623)" },
      { id: "jasmine_garland",  label: "Jasmine",      emoji: "⚪",  color: "linear-gradient(135deg,#2a2820,#fffadc)" },
      { id: "mango_leaves",     label: "Mango Leaves", emoji: "🍃", color: "linear-gradient(135deg,#001a00,#3cb371)" },
      { id: "mixed_floral",     label: "Mixed Floral", emoji: "💐", color: "linear-gradient(135deg,#2c0050,#dda0dd)" },
    ],
  },

  "entrance_decor.name_board": {
    label: "Welcome Name Board",
    options: [
      { id: "yes",    label: "Yes — One Board",  emoji: "✏️", color: "linear-gradient(135deg,#2a1800,#d4af37)" },
      { id: "custom", label: "Custom Design",    emoji: "🎨", color: "linear-gradient(135deg,#2c0050,#ddb7ff)" },
      { id: "no",     label: "Skip It",          emoji: "—",  color: "linear-gradient(135deg,#1a1a1a,#444)" },
    ],
  },

  "entrance_decor.top_decor_at_entrance": {
    label: "Top Entrance Decor",
    options: [
      { id: "floral_canopy",  label: "Floral Canopy",  emoji: "🌺", color: "linear-gradient(135deg,#3d0010,#ff6347)" },
      { id: "drape_swags",    label: "Silk Swags",     emoji: "🎀", color: "linear-gradient(135deg,#2c0050,#dda0dd)" },
      { id: "chandelier",     label: "Chandelier",     emoji: "💎", color: "linear-gradient(135deg,#001a2a,#b0c4de)" },
      { id: "banana_leaves",  label: "Banana Leaves",  emoji: "🍌", color: "linear-gradient(135deg,#001a00,#90ee90)" },
    ],
  },

  "backdrop_decor.types": {
    label: "Stage Backdrop",
    options: [
      { id: "flowers",      label: "Full Floral",    emoji: "🌸", color: "linear-gradient(135deg,#3d0030,#ff69b4)" },
      { id: "pattern",      label: "Pattern",        emoji: "🔶", color: "linear-gradient(135deg,#2a1800,#d4af37)" },
      { id: "flower_lights",label: "Flower Lights",  emoji: "✨", color: "linear-gradient(135deg,#1a0020,#f2ca50)" },
    ],
  },

  decor_lights: {
    label: "Decorative Lighting",
    options: [
      { id: "fairy_lights",  label: "Fairy Lights",   emoji: "✨", color: "linear-gradient(135deg,#1a1800,#fffacd)" },
      { id: "warm_amber",    label: "Warm Amber",     emoji: "🕯",  color: "linear-gradient(135deg,#2a1000,#f5a623)" },
      { id: "paper_lanterns",label: "Paper Lanterns", emoji: "🏮", color: "linear-gradient(135deg,#3d0a00,#ff4500)" },
      { id: "crystal_drops", label: "Crystal Drops",  emoji: "💎", color: "linear-gradient(135deg,#001a2a,#b0e0e6)" },
    ],
  },

  chandeliers: {
    label: "Chandeliers",
    options: [
      { id: "crystal",  label: "Crystal",  emoji: "💎", color: "linear-gradient(135deg,#001a2a,#b0c4de)" },
      { id: "floral",   label: "Floral",   emoji: "🌸", color: "linear-gradient(135deg,#3d0020,#ff69b4)" },
      { id: "brass",    label: "Brass",    emoji: "🌟", color: "linear-gradient(135deg,#2a1800,#d4af37)" },
      { id: "none",     label: "None",     emoji: "—",  color: "linear-gradient(135deg,#1a1a1a,#444)" },
    ],
  },

  props: {
    label: "Traditional Props",
    options: [
      { id: "uruli",        label: "Uruli Bowl",    emoji: "🫙",  color: "linear-gradient(135deg,#2a1400,#cd853f)" },
      { id: "banana_plant", label: "Banana Plants", emoji: "🍌", color: "linear-gradient(135deg,#001a00,#90ee90)" },
      { id: "oil_lamps",    label: "Oil Lamps",     emoji: "🪔",  color: "linear-gradient(135deg,#2a1800,#ffd700)" },
      { id: "kolam",        label: "Kolam Art",     emoji: "🔵", color: "linear-gradient(135deg,#1a0030,#ddb7ff)" },
    ],
  },

  selfie_booth_decor: {
    label: "Selfie Booth",
    options: [
      { id: "floral_frame",    label: "Floral Frame",   emoji: "🌸", color: "linear-gradient(135deg,#3d0020,#ff69b4)" },
      { id: "lit_signage",     label: "Lit Signage",    emoji: "✨", color: "linear-gradient(135deg,#1a1800,#f2ca50)" },
      { id: "minimal_booth",   label: "Minimal",        emoji: "📸", color: "linear-gradient(135deg,#1a1a1a,#666)" },
      { id: "traditional_frame",label: "Trad. Frame",   emoji: "🏛",  color: "linear-gradient(135deg,#2a1800,#d4af37)" },
    ],
  },

  hall_decor: {
    label: "Hall Decoration",
    options: [
      { id: "table_centrepieces", label: "Centrepieces",   emoji: "💐", color: "linear-gradient(135deg,#2c0050,#dda0dd)" },
      { id: "pillar_wraps",       label: "Pillar Wraps",   emoji: "🌿", color: "linear-gradient(135deg,#001a00,#3cb371)" },
      { id: "ceiling_drapes",     label: "Ceiling Drapes", emoji: "🎀", color: "linear-gradient(135deg,#2a1400,#e9c7c0)" },
      { id: "aisle_decor",        label: "Aisle Decor",    emoji: "✨", color: "linear-gradient(135deg,#1a1800,#f2ca50)" },
    ],
  },
};

/** Ordered list of slot keys (matches server SLOT_PRIORITY). */
export const SLOT_PRIORITY = [
  "primary_colors",
  "types_of_flowers",
  "entrance_decor.foyer",
  "entrance_decor.garlands",
  "entrance_decor.name_board",
  "entrance_decor.top_decor_at_entrance",
  "backdrop_decor.types",
  "decor_lights",
  "chandeliers",
  "props",
  "selfie_booth_decor",
  "hall_decor",
];

/** Compute the next unfilled slot from state (mirrors server logic). */
export function getNextEmptySlot(state) {
  if (!state) return SLOT_PRIORITY[0];
  for (const slot of SLOT_PRIORITY) {
    const val = getNestedValue(state, slot);
    const isEmpty = !val || (Array.isArray(val) && val.length === 0);
    if (isEmpty) return slot;
  }
  return null; // all filled
}

export function getNestedValue(obj, dottedPath) {
  const keys = dottedPath.split(".");
  let cur = obj;
  for (const k of keys) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = cur[k];
  }
  return cur;
}

/** Returns progress 0..1 based on how many slots are filled. */
export function getSlotProgress(state) {
  if (!state) return 0;
  let filled = 0;
  for (const slot of SLOT_PRIORITY) {
    const val = getNestedValue(state, slot);
    if (val && !(Array.isArray(val) && val.length === 0)) filled++;
  }
  return filled / SLOT_PRIORITY.length;
}

/** Hall options for the hall selection screen. */
export const HALL_CONFIG = [
  {
    id: "grand_lotus",
    name: "The Grand Lotus Ballroom",
    tag: "Lush Heritage",
    capacity: "800+ guests",
    mood: "Majestic & Opulent",
    emoji: "🏛",
    cssClass: "hall-visual-grand",
    description: "Grand crystal chandeliers, ornate gold-leaf pillars, reflective marble floors.",
  },
  {
    id: "amaravathi",
    name: "Amaravathi Palace",
    tag: "Royal Classic",
    capacity: "450 guests",
    mood: "Regal & Traditional",
    emoji: "🏯",
    cssClass: "hall-visual-amaravathi",
    description: "Stone arches, dark teak ceilings, royal purple and gold silk drapes.",
  },
  {
    id: "sky_pavilion",
    name: "The Sky Pavilion",
    tag: "Modern Ethereal",
    capacity: "300 guests",
    mood: "Airy & Contemporary",
    emoji: "🌅",
    cssClass: "hall-visual-sky",
    description: "Floor-to-ceiling glass, minimalist spaces, panoramic views at dusk.",
  },
  {
    id: "temple_gardens",
    name: "Temple Gardens Estate",
    tag: "Sacred Heritage",
    capacity: "600 guests",
    mood: "Serene & Sacred",
    emoji: "🌿",
    cssClass: "hall-visual-temple",
    description: "Open-air courtyard, carved stone pathways, ancient banyan trees.",
  },
];
