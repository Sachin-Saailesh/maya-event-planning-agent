"""
Conversation logic — slot-filling engine for Maya.
Drives the user through decoration fields in priority order,
handles confirmations, and generates summary text.
"""
from __future__ import annotations

import os
import sys
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

SLOT_PROMPTS: dict[str, str] = {
    "primary_colors": (
        "Hi, I am Maya from Neenkal Kettavai, your decoration planning assistant. "
        "Let's start with the colour palette for the hall. "
        "What primary colours would you like? For example: gold, maroon, ivory, or warm white."
    ),
    "types_of_flowers": (
        "Lovely choice! Now, what flowers would you like? "
        "Popular options include jasmine, marigold, roses, orchids, and lilies."
    ),
    "entrance_decor.foyer": (
        "Let's plan the entrance. What kind of foyer decoration would you like? "
        "For example: floral arch, kolam rangoli, drapes, or lanterns."
    ),
    "entrance_decor.garlands": (
        "What garlands would you like at the entrance? "
        "Options include mango leaf thoranam, jasmine strings, marigold garlands, or rose garlands."
    ),
    "entrance_decor.name_board": (
        "Would you like a name board at the entrance? "
        "It can be floral, backlit, wooden, or with LED letters."
    ),
    "entrance_decor.top_decor_at_entrance": (
        "Any top decoration at the entrance? "
        "For example: drape swags, floral canopy, or hanging installations."
    ),
    "backdrop_decor.types": (
        "Now for the backdrop. You can choose from: flowers, pattern, or flower lights. "
        "You can pick multiple — just tell me which ones."
    ),
    "decor_lights": (
        "What decorative lighting would you like? "
        "Options include fairy lights, string lights, candle lights, paper lanterns, or spotlights."
    ),
    "chandeliers": (
        "Would you like chandeliers? "
        "We have crystal, floral, brass, glass, or beaded chandeliers available."
    ),
    "props": (
        "Any props you'd like in the hall? "
        "For example: vintage furniture, swing, uruli, temple bells, or banana plants."
    ),
    "selfie_booth_decor": (
        "Would you like a selfie booth? "
        "We can set it up with a floral frame, neon sign, props wall, or themed backdrop."
    ),
    "hall_decor": (
        "Finally, any additional hall decoration? "
        "For example: ceiling drapes, pillar wraps, table centrepieces, or aisle runners."
    ),
}

GREETING = (
    "Hi, I am Maya from Neenkal Kettavai, your decoration planning assistant. "
    "I'll help you plan the perfect decoration for your hall. "
    "Let's start — what primary colours would you like for the decoration?"
)

COMPLETION_MESSAGE = (
    "That covers everything! Your decoration brief is ready. "
    "You can review all the details in the state panel on the right, "
    "and click 'Export Brief' to get a shareable summary."
)


def get_slot_prompt(slot: str) -> str:
    """Get Maya's prompt for a given slot."""
    return SLOT_PROMPTS.get(slot, f"Tell me about your preferences for {slot.replace('_', ' ')}.")


def get_greeting() -> str:
    return GREETING


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

    # No values extracted
    if not values:
        return {
            "patch_ops": [],
            "confirmation_text": "",
            "needs_confirmation": False,
            "confirmation_request": None,
            "next_slot": slot,
            "next_prompt": (
                f"I didn't quite catch that. {get_slot_prompt(slot)}"
            ),
        }

    # Validate backdrop types
    if slot == "backdrop_decor.types":
        try:
            values = validate_backdrop_types(values)
        except ValueError:
            valid = ", ".join(sorted(SLOT_PROMPTS.keys()))
            return {
                "patch_ops": [],
                "confirmation_text": "",
                "needs_confirmation": False,
                "confirmation_request": None,
                "next_slot": slot,
                "next_prompt": "Those backdrop types aren't available. Please choose from: flowers, pattern, or flower lights.",
            }

    # Check if slot already has values
    existing = get_nested(state, slot)
    if existing and isinstance(existing, list) and len(existing) > 0:
        # Field has values — needs confirmation
        if intent in ("add", "replace", "remove"):
            # User already specified intent
            pointer = dotted_to_pointer(slot)
            ops, conf_text = resolve_confirmation(intent, slot, existing, values, state)
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
            conf_req = build_confirmation_request(slot, existing, values)
            return {
                "patch_ops": [],
                "confirmation_text": "",
                "needs_confirmation": True,
                "confirmation_request": conf_req,
                "next_slot": slot,
                "next_prompt": None,
            }

    # Fresh field — just set
    pointer = dotted_to_pointer(slot)
    if slot == "backdrop_decor.types":
        # Also enable backdrop
        ops = create_replace_patch("/backdrop_decor/enabled", True)
        ops += create_add_patch(pointer, values)
    else:
        ops = create_add_patch(pointer, values)

    conf_text = format_confirmation(values)
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
