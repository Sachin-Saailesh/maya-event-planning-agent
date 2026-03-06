"""
Decoration hall state schema for Maya voice agent.
Scope: decoration_hall
"""
from __future__ import annotations

import copy
from typing import Any

BACKDROP_ALLOWED_TYPES = frozenset({"flowers", "pattern", "flower_lights"})

SLOT_PRIORITY: list[str] = [
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
]

_EMPTY_STATE: dict[str, Any] = {
    "scope": "decoration_hall",
    "primary_colors": [],
    "types_of_flowers": [],
    "props": [],
    "chandeliers": [],
    "decor_lights": [],
    "hall_decor": [],
    "entrance_decor": {
        "foyer": [],
        "garlands": [],
        "name_board": [],
        "top_decor_at_entrance": [],
    },
    "selfie_booth_decor": [],
    "backdrop_decor": {
        "enabled": False,
        "types": [],
    },
}


def create_empty_state() -> dict[str, Any]:
    """Return a fresh decoration hall state dict."""
    return copy.deepcopy(_EMPTY_STATE)


def get_nested(state: dict[str, Any], dotted_path: str) -> Any:
    """Resolve a dotted path like 'entrance_decor.foyer' to a value."""
    keys = dotted_path.split(".")
    current = state
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def set_nested(state: dict[str, Any], dotted_path: str, value: Any) -> None:
    """Set a value at a dotted path."""
    keys = dotted_path.split(".")
    current = state
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value


def validate_backdrop_types(types: list[str]) -> list[str]:
    """Return only valid backdrop types, raise on invalid."""
    invalid = [t for t in types if t not in BACKDROP_ALLOWED_TYPES]
    if invalid:
        raise ValueError(f"Invalid backdrop types: {invalid}. Allowed: {sorted(BACKDROP_ALLOWED_TYPES)}")
    return types


def slot_is_filled(state: dict[str, Any], slot: str) -> bool:
    """Check whether a slot has any values."""
    val = get_nested(state, slot)
    if val is None:
        return False
    if isinstance(val, list):
        return len(val) > 0
    if isinstance(val, bool):
        return val
    return bool(val)


def get_next_empty_slot(state: dict[str, Any]) -> str | None:
    """Return the next unfilled slot in priority order, or None if all filled."""
    for slot in SLOT_PRIORITY:
        if not slot_is_filled(state, slot):
            return slot
    return None
