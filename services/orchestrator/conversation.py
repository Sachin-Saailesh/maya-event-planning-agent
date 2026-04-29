"""
Conversation logic — slot-filling engine for Maya.
Drives the user through decoration fields in priority order,
handles confirmations, generates summary text, and speaks with the
warmth of a world-class wedding concierge.
"""
from __future__ import annotations

import logging
import os
import random
import sys
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "schema"))

from maya_schema.state import (
    get_next_empty_slot,
    get_nested,
    set_nested,
    slot_is_filled,
    validate_backdrop_types,
    SLOT_PRIORITY,
)
from maya_schema.patches import (
    create_add_patch,
    create_remove_patch,
    create_replace_patch,
    dotted_to_pointer,
)

# ── Prompt versioning ──────────────────────────────────────────────
# Increment when prompts are meaningfully changed for A/B tracking.
PROMPT_VERSION = "v8"

# ── Slot prompts (luxury concierge register) ───────────────────────

SLOT_PROMPTS: dict[str, list[str]] = {
    "primary_colors": [
        "Let's begin with the soul of your celebration — what colours are you dreaming of for the hall? Gold and maroon are timeless South Indian royalty, ivory and rose gold are endlessly romantic, or tell me your own unique vision.",
        "Colours set the whole mood for the evening. What palette speaks to your heart — warm and regal, soft and dreamy, or something bold and unexpected?",
        "The first brushstroke of your décor story — what primary colours would you like to weave through every corner of the hall?",
    ],
    "types_of_flowers": [
        "Flowers breathe life into every celebration. Are you drawn to the timeless elegance of jasmine, the festive vibrancy of marigolds, the romance of roses, or perhaps something more exotic like orchids?",
        "Now let's choose your blooms — what flowers should fill the hall with colour and fragrance? South Indian traditions adore jasmine and marigolds, but your vision is entirely your own.",
        "Fresh flowers are inseparable from South Indian weddings. Which varieties would you love — jasmine, roses, marigolds, lilies, orchids, or a mix of several?",
    ],
    "entrance_decor.foyer": [
        "Your guests' first impression begins at the foyer — how would you like it dressed? A grand floral arch, cascading silk drapes, towering banana plants, or an ornate traditional welcome?",
        "Let's design the entrance foyer. A floral canopy, hanging torans, ornate pillar arrangement — what style of welcome feels right for your celebration?",
        "The foyer is where the magic begins for your guests. What kind of decoration would you love them to walk into first?",
    ],
    "entrance_decor.garlands": [
        "Garlands at the entrance bring such warmth and tradition. Would you like fresh flower garlands — jasmine strings, marigold chains — or mango-leaf torans, or perhaps both?",
        "Should we adorn the entrance doors with garlands? Jasmine, marigold, rose petals — what feels right for your celebration?",
        "A beautifully garlanded entrance is a timeless South Indian gesture of welcome. What garland style would you like to greet your guests?",
    ],
    "entrance_decor.name_board": [
        "A personalised name board makes every guest feel truly honoured the moment they arrive. Shall we include a beautifully crafted welcome board at the entrance?",
        "Would you like a custom name board at the entrance — perhaps framed in fresh flowers or elegant gold lettering?",
        "Name boards add such a lovely personal touch. Would you like one at the entrance to welcome your guests with warmth?",
    ],
    "entrance_decor.top_decor_at_entrance": [
        "For the crown of your entrance — what would you like overhead? A cascade of fresh blooms, elegant draped fabric, hanging lanterns, or a fairy-light canopy?",
        "What shall we drape above the entrance arch? A lush floral canopy, silk swags, or clusters of hanging lights — what speaks to your imagination?",
        "Let's finish the entrance with something stunning overhead. A floral canopy, fabric swags, or hanging décor — what would you love?",
    ],
    "backdrop_decor.types": [
        "Now for the centrepiece of the stage — your backdrop. This frames every precious photograph of the day. Would you prefer a lush floral wall, an intricate patterned backdrop, or the romance of a flower-and-lights combination?",
        "The backdrop is the heart of every photograph taken that day. Flowers give a lush organic feel, a pattern brings artistry, and flower lights create pure enchantment — what speaks to you?",
        "Let's create your stage backdrop. A floral wall, an intricate pattern, or flower lights — which vision feels most like you?",
    ],
    "decor_lights": [
        "Lighting transforms a beautiful hall into something truly magical. Are you thinking warm fairy lights, elegant crystal uplights, romantic paper lanterns, or something else entirely?",
        "The right lighting makes everything glow. What decorative lights would set your perfect mood — warm white strings, tea lights, neon accents, or hanging lantern clusters?",
        "Let's set the atmosphere with light. Fairy lights, paper lanterns, crystal lights, or candle-style fixtures — what feeling do you want to create?",
    ],
    "chandeliers": [
        "Chandeliers are a stunning statement of grandeur from above. Would you like crystal, floral, brass, glass, or a modern chandelier style — or perhaps a mix?",
        "A chandelier adds elegance like nothing else. Shall we hang one — or a few — in the hall? Crystal, floral, or candle-style — which feels right?",
        "Imagine guests looking up at a stunning chandelier as they enter. Crystal, floral, or brass — which style would you love to see?",
    ],
    "props": [
        "Traditional props root the celebration in culture and beauty. An uruli filled with floating flowers, towering banana plants, gleaming brass lamps, or hand-painted clay pots — any that resonate with you?",
        "South Indian props carry such wonderful meaning. Would you like urulis, banana plants, brass lamps, or other traditional touches to ground the celebration in heritage?",
        "Let's add some cultural soul with props — a brass lamp here, banana plants there, an uruli filled with petals. What would you love to see placed around the hall?",
    ],
    "selfie_booth_decor": [
        "Every celebration deserves a beautiful memory corner! Would you like a selfie booth for your guests — perhaps framed in fresh flowers, fairy lights, or a personalised themed backdrop?",
        "A photo booth is always a guest favourite. Shall we create one? Floral frames, string lights, or a custom backdrop — what style would you love?",
        "Would you like a dedicated selfie booth? It's a wonderful way for guests to take home a beautiful memory of your special day.",
    ],
    "hall_decor": [
        "We're nearly there — just the finishing flourishes for the hall itself! Any additional touches you'd love? Table centrepieces, pillar wraps, aisle runners, or hanging floral installations?",
        "Last but never least — the hall's finishing details. Centrepieces, pillar décor, table runners, or ceiling installations — what extra magic shall we weave in?",
        "To complete the hall beautifully — any final décor elements? Centrepieces, draped pillars, or hanging floral clusters perhaps?",
    ],
}

GREETING = (
    "Vanakkam! I'm Maya, your personal South Indian wedding décor concierge. "
    "It is my absolute honour to help you design something truly beautiful and unforgettable today. "
    "Every detail we plan together will be a reflection of your taste and vision. "
    "Let us begin — what primary colours are you dreaming of for the hall?"
)

COMPLETION_MESSAGE = (
    "Your décor vision is looking absolutely stunning! "
    "Here is everything we've crafted together. "
    "Would you like to refine any detail — colours, flowers, the backdrop — "
    "or are you ready to see this come alive in your chosen hall?"
)

SESSION_ENDED_MESSAGE = (
    "It has been a true pleasure planning with you. "
    "Your decoration brief has been saved — click 'Export Brief' to download a shareable summary. "
    "May your celebration be everything you've dreamed of and more. Vanakkam!"
)

# ── Social / polite phrase handling ───────────────────────────────

POLITE_PHRASES = {
    "thank you", "thanks", "thank you so much", "thanks a lot", "great", "awesome",
    "perfect", "wonderful", "nice", "good", "okay", "ok", "sure", "alright",
    "sounds good", "that sounds great", "lovely", "brilliant", "excellent",
    "you're welcome", "appreciate it", "got it", "understood", "cool",
}

POLITE_RESPONSES = [
    "Of course! It's my pleasure.",
    "Absolutely! Happy to help.",
    "Not at all — let's keep creating something beautiful together.",
    "My pleasure entirely! Let's continue.",
    "Of course! Your celebration deserves every care.",
]

END_SESSION_PHRASES = {
    "end", "end session", "stop", "finish", "done", "wrap up", "that's all",
    "that is all", "close", "goodbye", "bye", "exit", "quit", "no changes",
    "no change", "no thank you", "no thanks", "nothing", "all good", "looks good",
}

REPEAT_PHRASES = {
    "repeat", "say that again", "can you repeat", "repeat that", "repeat please",
    "what did you say", "what was that", "what?", "huh?", "sorry?", "pardon?",
    "can you say that again", "could you repeat that", "please repeat",
    "i didn't hear you", "i couldn't hear", "say again", "one more time",
    "come again", "i missed that", "didn't catch that",
    "sorry can you repeat", "sorry what", "sorry say that again",
    "i'm sorry can you repeat", "i'm sorry what", "sorry i didn't catch that",
    "pardon me",
}

WHISPER_HALLUCINATION_BLOCKLIST = {
    "you", "you.", "you!", "uh", "um", "hmm", "hm",
    "thank you", "thank you.", "thanks", "thanks.",
    "okay", "ok", "yes", "no",
    "the", "a", "an", "is", "it", "in", "on", "at",
    "mayo", "maya",
}

# ── Prompt helpers ─────────────────────────────────────────────────

def get_slot_prompt(slot: str) -> str:
    """Get Maya's prompt for a given slot. Logs version + variant index."""
    prompts = SLOT_PROMPTS.get(slot)
    if prompts and isinstance(prompts, list):
        idx = random.randrange(len(prompts))
        logger.debug("[PROMPT] version=%s slot=%s variant=%d", PROMPT_VERSION, slot, idx)
        return prompts[idx]
    if prompts and isinstance(prompts, str):
        logger.debug("[PROMPT] version=%s slot=%s variant=0", PROMPT_VERSION, slot)
        return prompts
    return f"Tell me about your preferences for {slot.replace('_', ' ')}."


def get_greeting() -> str:
    return GREETING


def is_polite_phrase(text: str) -> bool:
    normalized = text.lower().strip().rstrip("!.").strip()
    return normalized in POLITE_PHRASES


def get_polite_response() -> str:
    return random.choice(POLITE_RESPONSES)


def is_end_session_intent(text: str) -> bool:
    normalized = text.lower().strip().rstrip("!.").strip()
    return normalized in END_SESSION_PHRASES


def is_repeat_request(text: str) -> bool:
    normalized = text.lower().strip().rstrip("!?.").strip()
    if normalized in REPEAT_PHRASES:
        return True
    for phrase in REPEAT_PHRASES:
        if phrase in normalized:
            return True
    return False


def is_whisper_hallucination(text: str) -> bool:
    normalized = text.strip().lower().rstrip("!?.,").strip()
    if normalized in WHISPER_HALLUCINATION_BLOCKLIST:
        return True
    if any(p in normalized for p in [".com", "www.", "subscribe", "thanks for watching", "learn more at"]):
        return True
    return False


# ── Personalised acknowledgment helpers ───────────────────────────

def _get_personalized_ack(slot: str, values: list[str], state: dict[str, Any]) -> str:
    """
    Return a warm, 1-sentence celebratory acknowledgment tailored to the
    slot and the specific values the customer just chose.
    Considers what's already been chosen (e.g. cross-references colours with flowers).
    """
    if not values:
        return ""

    val_lower = [v.lower() for v in values]
    colors_chosen = [c.lower() for c in state.get("primary_colors", [])]

    if len(values) == 1:
        joined = values[0]
    elif len(values) == 2:
        joined = f"{values[0]} and {values[1]}"
    else:
        joined = ", ".join(values[:-1]) + f", and {values[-1]}"

    if slot == "primary_colors":
        if {"gold", "maroon"}.issubset(set(val_lower)):
            return f"{joined.title()} — the very essence of South Indian royalty. What a magnificent, timeless choice!"
        if {"gold"} & set(val_lower) and {"maroon", "red", "burgundy"} & set(val_lower):
            return f"A rich, regal palette — {joined} together radiate warmth and grandeur!"
        if {"ivory", "white", "cream"} & set(val_lower):
            return f"What an ethereal, elegant palette — {joined} will give the hall a luminous, dreamlike beauty!"
        if {"rose gold", "blush", "pink"} & set(val_lower):
            return f"Absolutely romantic — {joined} will make the entire hall feel like a fairytale!"
        if {"purple", "lavender"} & set(val_lower):
            return f"Regal and enchanting — {joined} will give the celebration a truly majestic feel!"
        return f"A beautiful palette — {joined} will be woven through every element to create a cohesive, stunning look!"

    if slot == "types_of_flowers":
        if "jasmine" in val_lower and ("gold" in colors_chosen or "maroon" in colors_chosen):
            return "Jasmine will look absolutely divine against your chosen palette — that fragrance filling the hall will be intoxicating!"
        if "jasmine" in val_lower:
            return "Jasmine — the very soul of South Indian celebrations. Its divine fragrance will fill every corner of the hall!"
        if {"rose", "roses"} & set(val_lower):
            return f"{joined.capitalize()} add a classic romantic touch that never fails to move people. Stunning choice!"
        if {"marigold", "marigolds"} & set(val_lower):
            return f"Marigolds are the heartbeat of South Indian weddings — such a vibrant, joyful choice!"
        if {"orchid", "orchids"} & set(val_lower):
            return f"Orchids bring a sense of refined luxury that's truly breathtaking. Wonderful!"
        if {"lotus"} & set(val_lower):
            return "Lotus flowers carry such profound beauty and meaning — a deeply spiritual and elegant choice!"
        return f"{joined.capitalize()} will bring the hall to life with colour, fragrance, and natural beauty!"

    if slot == "entrance_decor.foyer":
        return f"Wonderful — {joined} at the foyer will set a warm, magnificent first impression your guests will never forget!"

    if slot == "entrance_decor.garlands":
        return f"Beautiful — {joined} garlands framing the entrance will carry that deep sense of South Indian tradition and welcome!"

    if slot == "entrance_decor.name_board":
        return "Lovely! A personalised name board will make every guest feel truly honoured from the very first moment they arrive."

    if slot == "entrance_decor.top_decor_at_entrance":
        return f"Stunning — {joined} overhead will give the entrance such dramatic, unforgettable impact!"

    if slot == "backdrop_decor.types":
        if "flower_lights" in val_lower:
            return "A flower-and-lights backdrop — every photograph taken in front of it will look absolutely breathtaking. Pure magic!"
        if "flowers" in val_lower:
            return "A lush floral wall backdrop will be the most photographed element of the entire day. Magnificent!"
        if "pattern" in val_lower:
            return "An intricate patterned backdrop gives such a refined, artisanal quality to the stage. Beautiful choice!"
        return f"Your {joined} backdrop will frame every precious moment of the celebration perfectly!"

    if slot == "decor_lights":
        if "fairy lights" in val_lower or "string lights" in val_lower:
            return f"{joined.capitalize()} will turn your hall into something truly magical once the evening begins!"
        if "paper lanterns" in val_lower:
            return "Paper lanterns cast the most romantic, warm glow — guests will be enchanted by the atmosphere!"
        return f"{joined.capitalize()} — the hall is going to radiate such warmth and elegance!"

    if slot == "chandeliers":
        if "crystal" in " ".join(val_lower):
            return "Crystal chandeliers cascading light across the hall — the very definition of grandeur and opulence!"
        if "floral" in " ".join(val_lower):
            return "A floral chandelier is so uniquely beautiful — it will be a true conversation piece overhead!"
        return f"A {joined} is going to be a show-stopping focal point above the celebrations!"

    if slot == "props":
        if any("uruli" in v for v in val_lower):
            return "An uruli filled with floating flowers — a true symbol of South Indian elegance and abundance. Exquisite!"
        if any("lamp" in v for v in val_lower):
            return f"Brass lamps carry such beautiful symbolism — {joined} will fill the hall with a golden, sacred warmth!"
        return f"{joined.capitalize()} will add such rich cultural depth and meaning to the celebration!"

    if slot == "selfie_booth_decor":
        return "Perfect — your guests are going to absolutely love having a beautiful memory corner. Those photographs will be treasured forever!"

    if slot == "hall_decor":
        return f"{joined.capitalize()} — the finishing flourishes that will tie every element of your hall together beautifully!"

    return format_confirmation(values)


def _get_progress_note(next_slot_index: int) -> str:
    """
    Return a short milestone note at key points in the slot-filling journey.
    Only fires at indices 5, 6, 8, 10, 11 — silent at all other points.
    """
    _MILESTONES: dict[int, str] = {
        5:  "Wonderful — the entrance is completely planned! Now let's design the stage.",
        6:  "We're halfway through and it's looking absolutely spectacular! On to the all-important backdrop.",
        8:  "The grand elements are beautifully set — just the final details to weave in now.",
        10: "Almost there — just the last flourishes to make it perfect!",
        11: "We're at the very final touch. Let's make it extraordinary.",
    }
    return _MILESTONES.get(next_slot_index, "")


def _build_next_prompt(next_slot: str | None) -> str:
    """Compose the next prompt with an optional milestone note prepended."""
    if next_slot is None:
        return COMPLETION_MESSAGE
    try:
        idx = SLOT_PRIORITY.index(next_slot)
    except ValueError:
        idx = -1
    note = _get_progress_note(idx)
    slot_q = get_slot_prompt(next_slot)
    return f"{note} {slot_q}".strip() if note else slot_q


# ── Confirmation helpers ───────────────────────────────────────────

def format_confirmation(values: list[str]) -> str:
    if len(values) == 1:
        return f"Got it: {values[0]}."
    elif len(values) == 2:
        return f"Got it: {values[0]} and {values[1]}."
    else:
        return f"Got it: {', '.join(values[:-1])}, and {values[-1]}."


def build_confirmation_request(
    slot: str, existing: list[str], new_values: list[str]
) -> dict[str, Any]:
    existing_str = ", ".join(existing)
    new_str = ", ".join(new_values)
    return {
        "slot": slot,
        "existing_values": existing,
        "new_values": new_values,
        "message": (
            f"You already have {existing_str} for {slot.replace('_', ' ')}. "
            f"You mentioned {new_str}. Would you like to replace the existing, "
            f"add these to the list, or remove some?"
        ),
        "options": ["replace", "add", "remove"],
    }


def resolve_confirmation(
    intent: str, slot: str, existing: list[str], new_values: list[str], state: dict[str, Any]
) -> tuple[list[dict[str, Any]], str]:
    pointer = dotted_to_pointer(slot)

    if intent == "replace":
        ops = create_replace_patch(pointer, new_values)
        return ops, format_confirmation(new_values)

    elif intent == "add":
        ops = create_add_patch(pointer, new_values)
        combined = existing + new_values
        return ops, format_confirmation(combined)

    elif intent == "remove":
        current = get_nested(state, slot) or []
        ops = create_remove_patch(pointer, new_values, current)
        remaining = [v for v in current if v not in new_values]
        if remaining:
            return ops, f"Removed. Keeping: {', '.join(remaining)}."
        return ops, "All items removed."

    else:
        ops = create_add_patch(pointer, new_values)
        combined = existing + new_values
        return ops, format_confirmation(combined)


# ── Core slot-filling engine ───────────────────────────────────────

# Slots where a bare "yes/sure/ok" confirm intent can be stored as a value
AFFIRMATIVE_SLOTS = {
    "entrance_decor.name_board",
    "entrance_decor.garlands",
    "chandeliers",
    "selfie_booth_decor",
}


def process_user_input(
    _text: str,
    slot: str,
    parsed: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Process parsed user input for a slot.
    Returns: {
        "patch_ops": list,
        "confirmation_text": str,
        "needs_confirmation": bool,
        "confirmation_request": dict | None,
        "next_slot": str | None,
        "next_prompt": str | None,
    }
    """
    values = parsed["values"]
    intent = parsed["intent"]
    target_slot = parsed.get("slot", slot)

    # ── Greeting ───────────────────────────────────────────────────
    if intent == "greeting":
        if slot == "primary_colors":
            prompt = "Vanakkam! It's wonderful to have you here. Let's begin — what primary colours are you imagining for the hall? Gold, maroon, ivory, rose gold — your palette is completely yours to choose."
        else:
            prompt = f"Hello! Let's continue crafting your beautiful celebration. {get_slot_prompt(slot)}"
        return {
            "patch_ops": [],
            "confirmation_text": "",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": slot,
            "next_prompt": prompt,
        }

    # ── Deny / skip ────────────────────────────────────────────────
    if intent == "deny" and not values:
        next_slot = _advance_slot(state, slot)
        return {
            "patch_ops": [],
            "confirmation_text": "Of course — no problem at all.",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": next_slot,
            "next_prompt": _build_next_prompt(next_slot),
        }

    # ── Acknowledgment / confirm with no values ────────────────────
    if intent in ("acknowledgment", "confirm") and not values:
        if slot in AFFIRMATIVE_SLOTS:
            values = ["yes"]
            # Fall through to the normal set path below
        else:
            return {
                "patch_ops": [],
                "confirmation_text": "",
                "needs_confirmation": False,
                "confirmation_request": None,
                "next_slot": slot,
                "next_prompt": f"Of course! {get_slot_prompt(slot)}",
            }

    # ── No values extracted ────────────────────────────────────────
    if not values:
        # Warm, empathetic re-prompt rather than generic "didn't catch that"
        empathetic_reprompts = [
            "I want to make sure I get this exactly right for you.",
            "I'd love to capture this perfectly for your celebration.",
            "Take your time — every detail matters.",
        ]
        re_note = random.choice(empathetic_reprompts)
        return {
            "patch_ops": [],
            "confirmation_text": "",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": slot,
            "next_prompt": f"{re_note} {get_slot_prompt(slot)}",
        }

    # ── Backdrop type validation ───────────────────────────────────
    if target_slot == "backdrop_decor.types":
        try:
            values = validate_backdrop_types(values)
        except ValueError:
            return {
                "patch_ops": [],
                "confirmation_text": "",
                "needs_confirmation": False,
                "confirmation_request": None,
                "next_slot": slot,
                "next_prompt": "Those backdrop types aren't available. You can choose from: flowers, pattern, or flower lights — which would you love?",
            }

    # ── Slot already has values — needs confirmation ───────────────
    existing = get_nested(state, target_slot)
    if existing and isinstance(existing, list) and len(existing) > 0:
        if intent in ("add", "replace", "remove"):
            pointer = dotted_to_pointer(target_slot)
            ops, conf_text = resolve_confirmation(intent, target_slot, existing, values, state)

            if target_slot != slot and not slot_is_filled(state, slot):
                next_slot = slot
            else:
                next_slot = _advance_slot(state, slot)

            return {
                "patch_ops": ops,
                "confirmation_text": conf_text,
                "needs_confirmation": False,
                "confirmation_request": None,
                "next_slot": next_slot,
                "next_prompt": _build_next_prompt(next_slot),
            }
        else:
            conf_req = build_confirmation_request(target_slot, existing, values)
            return {
                "patch_ops": [],
                "confirmation_text": "",
                "needs_confirmation": True,
                "confirmation_request": conf_req,
                "next_slot": slot,
                "next_prompt": None,
            }

    # ── Fresh field — set ──────────────────────────────────────────
    pointer = dotted_to_pointer(target_slot)
    if target_slot == "backdrop_decor.types":
        ops = create_replace_patch("/backdrop_decor/enabled", True)
        ops += create_add_patch(pointer, values)
    else:
        ops = create_add_patch(pointer, values)

    # Personalised acknowledgment — warm, specific to choices made
    ack = _get_personalized_ack(target_slot, values, state)
    conf_text = ack if ack else format_confirmation(values)

    if target_slot != slot and not slot_is_filled(state, slot):
        next_slot = slot
    else:
        next_slot = _advance_slot(state, slot)

    return {
        "patch_ops": ops,
        "confirmation_text": conf_text,
        "needs_confirmation": False,
        "confirmation_request": None,
        "next_slot": next_slot,
        "next_prompt": _build_next_prompt(next_slot),
    }


def _advance_slot(state: dict[str, Any], current_slot: str) -> str | None:
    try:
        idx = SLOT_PRIORITY.index(current_slot)
    except ValueError:
        return get_next_empty_slot(state)

    for s in SLOT_PRIORITY[idx + 1:]:
        if not slot_is_filled(state, s):
            return s
    return None


# ── Review-stage intent parsing ────────────────────────────────────

REVIEW_PROCEED_PHRASES = [
    "proceed to image", "proceed to generation", "proceed to hall",
    "let's proceed", "let's go", "looks good proceed", "go ahead",
    "ready to proceed", "ready", "generate", "let's generate",
    "image generation", "i'm ready", "im ready", "next step",
    "proceed", "let's move", "continue", "go forward",
]

REVIEW_MODIFY_GENERIC_PHRASES = [
    "want to modify", "i want to modify", "want to change", "i want to change",
    "modify these", "change these", "modify props", "change props",
    "modify selections", "change selections", "edit selections",
    "go back and", "want to edit", "i want to edit", "modify",
]

REVIEW_SLOT_ALIASES: dict[str, set[str]] = {
    "primary_colors":                      {"color", "colours", "colors", "palette", "theme color", "primary colors", "colour scheme"},
    "types_of_flowers":                    {"flowers", "flower", "floral", "florals"},
    "backdrop_decor.types":                {"backdrop", "stage background", "background", "stage backdrop"},
    "decor_lights":                        {"lights", "lighting", "light"},
    "chandeliers":                         {"chandelier", "chandeliers"},
    "entrance_decor.foyer":                {"foyer", "entrance foyer"},
    "entrance_decor.garlands":             {"garlands", "garland"},
    "entrance_decor.name_board":           {"name board", "nameboard", "welcome board"},
    "entrance_decor.top_decor_at_entrance": {"top decor", "entrance canopy", "entrance top"},
    "props":                               {"props", "traditional props"},
    "selfie_booth_decor":                  {"selfie booth", "photo booth", "selfie", "photobooth"},
    "hall_decor":                          {"hall decor", "hall decoration", "centrepieces", "centerpieces"},
}

MODIFY_VERBS = {"modify", "change", "edit", "update", "fix", "adjust", "redo", "different"}


def parse_review_intent(text: str) -> dict[str, Any]:
    """
    Parse a user utterance when all slots are filled (review / completion stage).
    Returns: { "intent": "proceed" | "modify_slot" | "modify_generic" | "end" | "other",
               "slot": str | None }
    """
    lower = text.lower().strip().rstrip("!.?")

    for phrase in REVIEW_PROCEED_PHRASES:
        if phrase in lower:
            return {"intent": "proceed", "slot": None}

    has_verb = any(v in lower for v in MODIFY_VERBS)
    for slot, aliases in REVIEW_SLOT_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                if has_verb or any(w in lower for w in ("want", "would like", "like to", "need to")):
                    return {"intent": "modify_slot", "slot": slot}

    for phrase in REVIEW_MODIFY_GENERIC_PHRASES:
        if phrase in lower:
            return {"intent": "modify_generic", "slot": None}

    if is_end_session_intent(text):
        return {"intent": "end", "slot": None}

    return {"intent": "other", "slot": None}


def get_review_modify_prompt() -> str:
    return (
        "Of course! Which detail would you like to refine? "
        "Colours, flowers, backdrop, entrance décor, lighting, "
        "chandeliers, selfie booth, props, or hall décor — just say the word."
    )


# ── Summary text generator ─────────────────────────────────────────

def generate_summary_text(state: dict[str, Any]) -> str:
    """Generate a human-readable decor brief from the state."""
    lines = []
    lines.append("═" * 50)
    lines.append("  MAYA — DECORATION HALL BRIEF")
    lines.append("  South Indian Wedding Event")
    lines.append("═" * 50)
    lines.append("")

    def _fmt_list(items: list, label: str):
        if items:
            lines.append(f"▸ {label}")
            for item in items:
                lines.append(f"    • {item}")
            lines.append("")

    _fmt_list(state.get("primary_colors", []), "Primary Colours")
    _fmt_list(state.get("types_of_flowers", []), "Flowers")

    entrance = state.get("entrance_decor", {})
    if any(entrance.get(k) for k in ("foyer", "garlands", "name_board", "top_decor_at_entrance")):
        lines.append("▸ Entrance Decoration")
        _fmt_list(entrance.get("foyer", []), "  Foyer")
        _fmt_list(entrance.get("garlands", []), "  Garlands")
        _fmt_list(entrance.get("name_board", []), "  Name Board")
        _fmt_list(entrance.get("top_decor_at_entrance", []), "  Top Decor at Entrance")

    backdrop = state.get("backdrop_decor", {})
    if backdrop.get("enabled"):
        lines.append("▸ Backdrop")
        lines.append(f"    Types: {', '.join(backdrop.get('types', []))}")
        lines.append("")

    _fmt_list(state.get("decor_lights", []), "Decorative Lighting")
    _fmt_list(state.get("chandeliers", []), "Chandeliers")
    _fmt_list(state.get("props", []), "Props")
    _fmt_list(state.get("selfie_booth_decor", []), "Selfie Booth")
    _fmt_list(state.get("hall_decor", []), "Hall Decoration")

    lines.append("═" * 50)
    lines.append("  Generated by Maya AI Wedding Planner")
    return "\n".join(lines)
