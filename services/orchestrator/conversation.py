"""
Conversation logic — slot-filling engine for Maya.
Drives the user through decoration fields in priority order,
handles confirmations, and generates summary text.
"""
from __future__ import annotations

import os
import sys
import random
from typing import Any

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

# ── Slot prompts ───────────────────────────────────────────────────

SLOT_PROMPTS: dict[str, list[str]] = {
    "primary_colors": [
        "What primary colours would you like for the hall?",
        "What colour scheme do you have in mind for the hall?",
        "Could you tell me the main colours you want for the decoration?"
    ],
    "types_of_flowers": [
        "Lovely choice! What flowers would you like?",
        "Beautiful! Next, what kind of flowers should we use?",
        "Great colour palette. What type of flowers are you thinking of?"
    ],
    "entrance_decor.foyer": [
        "Let's plan the entrance. What kind of foyer decoration would you like?",
        "Moving on to the entryway, how would you like the foyer decorated?",
        "For the entrance foyer, what style are you looking for?"
    ],
    "entrance_decor.garlands": [
        "What garlands would you like at the entrance?",
        "Should we add some garlands at the entrance?",
        "Any specific garlands for the entryway?"
    ],
    "entrance_decor.name_board": [
        "Would you like a customised welcome name board?",
        "How about a welcome name board?",
        "Do you want a customized name board at the entrance?"
    ],
    "entrance_decor.top_decor_at_entrance": [
        "Any top decoration for the entrance canopy?",
        "Would you like any decor hanging from the top of the entrance?",
        "For the top of the entryway, do you prefer a floral canopy or drape swags?"
    ],
    "backdrop_decor.types": [
        "Now for the backdrop. You can choose from flowers, pattern, or flower lights.",
        "Moving to the stage backdrop, what style catches your eye?",
        "Let's design the backdrop. Would you prefer flowers, a pattern, or lights?"
    ],
    "decor_lights": [
        "What decorative lighting would you like?",
        "Lighting sets the mood! Any preference for the decorative lights?",
        "Any preferences for decorative lights? We can do fairy lights or warm paper lanterns."
    ],
    "chandeliers": [
        "Would you like any hanging chandeliers?",
        "Should we add chandeliers to the ceiling?",
        "How about hanging some chandeliers?"
    ],
    "props": [
        "Any traditional props you'd like in the hall? Like an uruli or banana plants?",
        "Would you like to add some traditional props?",
        "Do you want any special props around the hall?"
    ],
    "selfie_booth_decor": [
        "Would you like a selfie booth?",
        "How about a fun selfie booth for the guests?",
        "Do you want to include a photobooth backdrop?"
    ],
    "hall_decor": [
        "Finally, any additional hall decoration? Like table centrepieces or pillar wraps?",
        "Is there any extra hall decor you'd like?",
        "Last but not least, any decorative touches for the rest of the hall?"
    ],
}

GREETING = (
    "Hi, I am Maya. "
    "I'll help plan the perfect decoration for your hall. "
    "Let's start — what primary colours would you like?"
)

COMPLETION_MESSAGE = (
    "These are the props you chose. Would you like to modify any of that, "
    "or shall we proceed to the image generation?"
)

SESSION_ENDED_MESSAGE = (
    "Perfect! It was a pleasure helping you plan. "
    "Your decoration brief has been saved — click 'Export Brief' to download a shareable summary. "
    "Have a wonderful event!"
)

# Polite / social phrases that should get a warm acknowledgment, not be parsed as slot input
POLITE_PHRASES = {
    "thank you", "thanks", "thank you so much", "thanks a lot", "great", "awesome",
    "perfect", "wonderful", "nice", "good", "okay", "ok", "sure", "alright",
    "sounds good", "that sounds great", "lovely", "brilliant", "excellent",
    "you're welcome", "appreciate it", "got it", "understood", "cool",
}

POLITE_RESPONSES = [
    "Of course! Happy to help.",
    "No problem at all!",
    "Absolutely! Let's keep going.",
    "My pleasure!",
    "Sure thing!",
]

# Phrases that signal the user wants to end the session
END_SESSION_PHRASES = {
    "end", "end session", "stop", "finish", "done", "wrap up", "that's all",
    "that is all", "close", "goodbye", "bye", "exit", "quit", "no changes",
    "no change", "no thank you", "no thanks", "nothing", "all good", "looks good",
}

# Phrases that signal the user wants Maya to repeat the last question
REPEAT_PHRASES = {
    # Direct requests
    "repeat", "say that again", "can you repeat", "repeat that", "repeat please",
    "what did you say", "what was that", "what?", "huh?", "sorry?", "pardon?",
    # Polite variants
    "can you say that again", "could you repeat that", "please repeat",
    "i didn't hear you", "i couldn't hear", "say again", "one more time",
    "come again", "i missed that", "didn't catch that",
    # With apologies (common voice pattern)
    "sorry can you repeat", "sorry what", "sorry say that again",
    "i'm sorry can you repeat", "i'm sorry what", "sorry i didn't catch that",
    "pardon me",
}

# Common Whisper hallucinations on near-silence audio.
# These are filtered at the orchestrator level as a second line of defence
# (first line is the VAD min_speech_ms guard in the worker).
WHISPER_HALLUCINATION_BLOCKLIST = {
    "you", "you.", "you!", "uh", "um", "hmm", "hm",
    "thank you", "thank you.", "thanks", "thanks.",
    "okay", "ok", "yes", "no",  # single-word noise triggers
    "the", "a", "an", "is", "it", "in", "on", "at",
    "mayo", "maya",  # common mic pickup of TTS leakage
}


def get_slot_prompt(slot: str) -> str:
    """Get Maya's prompt for a given slot."""
    prompts = SLOT_PROMPTS.get(slot)
    if prompts and isinstance(prompts, list):
        return random.choice(prompts)
    elif prompts and isinstance(prompts, str):
        return prompts
    return f"Tell me about your preferences for {slot.replace('_', ' ')}."


def get_greeting() -> str:
    return GREETING


def is_polite_phrase(text: str) -> bool:
    """Return True if the text is a social/polite filler that should not be parsed as a slot."""
    normalized = text.lower().strip().rstrip("!.").strip()
    return normalized in POLITE_PHRASES


def get_polite_response() -> str:
    """Return a warm, brief acknowledgment for social phrases."""
    return random.choice(POLITE_RESPONSES)


def is_end_session_intent(text: str) -> bool:
    """Return True if the user is signalling they want to end the session."""
    normalized = text.lower().strip().rstrip("!.").strip()
    return normalized in END_SESSION_PHRASES


def is_repeat_request(text: str) -> bool:
    """
    Return True if the user is asking Maya to repeat the last question.
    Checks both exact matches and substring containment for natural phrasing.
    """
    normalized = text.lower().strip().rstrip("!?.").strip()
    # Exact match first (fast path)
    if normalized in REPEAT_PHRASES:
        return True
    # Substring match for longer utterances like "I'm sorry, can you repeat that?"
    for phrase in REPEAT_PHRASES:
        if phrase in normalized:
            return True
    return False


def is_whisper_hallucination(text: str) -> bool:
    """
    Return True if the transcript looks like a Whisper hallucination.
    These are single-word or very short strings that Whisper produces
    when transcribing near-silence or background noise audio.
    Also filter out common whisper spam like youtube links or .com domains.
    """
    normalized = text.strip().lower().rstrip("!?.,").strip()
    
    if normalized in WHISPER_HALLUCINATION_BLOCKLIST:
        return True
    
    if any(phrase in normalized for phrase in [".com", "www.", "subscribe", "thanks for watching", "learn more at"]):
        return True
        
    return False


def format_confirmation(values: list[str]) -> str:
    """Format a brief confirmation message."""
    if len(values) == 1:
        return f"Got it: {values[0]}."
    elif len(values) == 2:
        return f"Got it: {values[0]} and {values[1]}."
    else:
        return f"Got it: {', '.join(values[:-1])}, and {values[-1]}."


def build_confirmation_request(
    slot: str, existing: list[str], new_values: list[str]
) -> dict[str, Any]:
    """Build a confirmation request when a field already has values."""
    existing_str = ", ".join(existing)
    new_str = ", ".join(new_values)
    return {
        "slot": slot,
        "existing_values": existing,
        "new_values": new_values,
        "message": (
            f"You already have {existing_str} for {slot.replace('_', ' ')}. "
            f"You mentioned {new_str}. Would you like to replace the existing values, "
            f"add these to the list, or remove some?"
        ),
        "options": ["replace", "add", "remove"],
    }


def resolve_confirmation(
    intent: str, slot: str, existing: list[str], new_values: list[str], state: dict[str, Any]
) -> tuple[list[dict[str, Any]], str]:
    """
    Resolve a replace/add/remove confirmation.
    Returns: (patch_ops, confirmation_text)
    """
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
        # Default to add
        ops = create_add_patch(pointer, new_values)
        combined = existing + new_values
        return ops, format_confirmation(combined)


def process_user_input(
    text: str,
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

    # Handle greeting
    if intent == "greeting":
        if slot == "primary_colors":
            prompt = "Hello! Let's get started. What primary colours would you like for the hall? (e.g., gold, maroon, ivory)"
        else:
            prompt = f"Hi there! Back to our planning: {get_slot_prompt(slot)}"
            
        return {
            "patch_ops": [],
            "confirmation_text": "",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": slot,
            "next_prompt": prompt,
        }

    # Slots where a bare confirmation means "yes, I want that"
    # (boolean-style questions where the answer is effectively yes/no)
    AFFIRMATIVE_SLOTS = {
        "entrance_decor.name_board",
        "entrance_decor.garlands",
        "chandeliers",
        "selfie_booth_decor",
    }

    # Handle deny/skip
    if intent == "deny" and not values:
        next_slot = _advance_slot(state, slot)
        return {
            "patch_ops": [],
            "confirmation_text": "No problem, skipping that.",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": next_slot,
            "next_prompt": get_slot_prompt(next_slot) if next_slot else COMPLETION_MESSAGE,
        }

    # Handle acknowledgment / confirmation with no values
    if intent in ("acknowledgment", "confirm") and not values:
        # For boolean-style slots, a bare "yes/sure/okay" means they want it
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
                "next_prompt": f"Got it! {get_slot_prompt(slot)}",
            }

    # No values extracted — re-prompt with context
    if not values:
        return {
            "patch_ops": [],
            "confirmation_text": "",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": slot,
            "next_prompt": f"I didn't quite catch that. {get_slot_prompt(slot)}",
        }

    # Validate backdrop types
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
                "next_prompt": "Those backdrop types aren't available. Please choose from: flowers, pattern, or flower lights.",
            }

    # Check if slot already has values
    existing = get_nested(state, target_slot)
    if existing and isinstance(existing, list) and len(existing) > 0:
        # Field has values — needs confirmation
        if intent in ("add", "replace", "remove"):
            # User already specified intent
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
                "next_prompt": get_slot_prompt(next_slot) if next_slot else COMPLETION_MESSAGE,
            }
        else:
            # Ask for confirmation
            conf_req = build_confirmation_request(target_slot, existing, values)
            return {
                "patch_ops": [],
                "confirmation_text": "",
                "needs_confirmation": True,
                "confirmation_request": conf_req,
                "next_slot": slot,
                "next_prompt": None,
            }

    # Fresh field — just set
    pointer = dotted_to_pointer(target_slot)
    if target_slot == "backdrop_decor.types":
        # Also enable backdrop
        ops = create_replace_patch("/backdrop_decor/enabled", True)
        ops += create_add_patch(pointer, values)
    else:
        ops = create_add_patch(pointer, values)

    conf_text = format_confirmation(values)
    
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
        "next_prompt": get_slot_prompt(next_slot) if next_slot else COMPLETION_MESSAGE,
    }


def _advance_slot(state: dict[str, Any], current_slot: str) -> str | None:
    """Get the next empty slot after processing current one."""
    # We need to check which slots are still empty
    # But we also need to skip the current slot since we're processing it
    from maya_schema.state import SLOT_PRIORITY as sp
    try:
        idx = sp.index(current_slot)
    except ValueError:
        return get_next_empty_slot(state)

    for s in sp[idx + 1:]:
        if not slot_is_filled(state, s):
            return s
    return None


# ── Review-stage intent parsing ────────────────────────────────

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

# Slot aliases for voice-driven slot targeting
REVIEW_SLOT_ALIASES: dict[str, set[str]] = {
    "primary_colors":                     {"color", "colours", "colors", "palette", "theme color", "primary colors", "colour scheme"},
    "types_of_flowers":                   {"flowers", "flower", "floral", "florals"},
    "backdrop_decor.types":               {"backdrop", "stage background", "background", "stage backdrop"},
    "decor_lights":                       {"lights", "lighting", "light"},
    "chandeliers":                        {"chandelier", "chandeliers"},
    "entrance_decor.foyer":               {"foyer", "entrance foyer"},
    "entrance_decor.garlands":            {"garlands", "garland"},
    "entrance_decor.name_board":          {"name board", "nameboard", "welcome board"},
    "entrance_decor.top_decor_at_entrance":{"top decor", "entrance canopy", "entrance top"},
    "props":                              {"props", "traditional props"},
    "selfie_booth_decor":                 {"selfie booth", "photo booth", "selfie", "photobooth"},
    "hall_decor":                         {"hall decor", "hall decoration", "centrepieces", "centerpieces"},
}

MODIFY_VERBS = {"modify", "change", "edit", "update", "fix", "adjust", "redo", "different"}


def parse_review_intent(text: str) -> dict[str, Any]:
    """
    Parse a user utterance when all slots are filled (review / completion stage).
    Called instead of generic NLU when current_slot is None.

    Returns: { "intent": "proceed" | "modify_slot" | "modify_generic" | "end" | "other",
               "slot": str | None }
    """
    lower = text.lower().strip().rstrip("!.?")

    # Proceed intents — check first so "let's proceed" doesn't match modify
    for phrase in REVIEW_PROCEED_PHRASES:
        if phrase in lower:
            return {"intent": "proceed", "slot": None}

    # Slot-specific modify (needs a modify verb + a slot alias)
    has_verb = any(v in lower for v in MODIFY_VERBS)
    for slot, aliases in REVIEW_SLOT_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                if has_verb or any(w in lower for w in ("want", "would like", "like to", "need to")):
                    return {"intent": "modify_slot", "slot": slot}

    # Generic modify
    for phrase in REVIEW_MODIFY_GENERIC_PHRASES:
        if phrase in lower:
            return {"intent": "modify_generic", "slot": None}

    # End/done
    if is_end_session_intent(text):
        return {"intent": "end", "slot": None}

    return {"intent": "other", "slot": None}


def get_review_modify_prompt() -> str:
    return (
        "Sure! Which part would you like to change? "
        "Colors, flowers, backdrop, entrance decor, lighting, "
        "chandeliers, selfie booth, props, or hall decor?"
    )


def generate_summary_text(state: dict[str, Any]) -> str:
    """Generate a human-readable decor brief from the state."""
    lines = []
    lines.append("═" * 50)
    lines.append("  DECORATION HALL BRIEF")
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
    return "\n".join(lines)
