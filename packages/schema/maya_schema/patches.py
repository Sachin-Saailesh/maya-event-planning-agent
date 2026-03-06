"""
JSON Patch (RFC6902) utilities for Maya state management.
All state mutations go through patches for robust UI updates.
"""
from __future__ import annotations

import copy
from typing import Any

import jsonpatch


def apply_patch(state: dict[str, Any], patch_ops: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply a list of RFC6902 patch operations to state. Returns new state dict."""
    jp = jsonpatch.JsonPatch(patch_ops)
    return jp.apply(copy.deepcopy(state))


def create_add_patch(json_pointer: str, values: list[str]) -> list[dict[str, Any]]:
    """
    Create patch ops to append items to an array at json_pointer.
    Example: create_add_patch("/primary_colors", ["gold", "maroon"])
    produces: [{"op": "add", "path": "/primary_colors/-", "value": "gold"}, ...]
    """
    return [{"op": "add", "path": f"{json_pointer}/-", "value": v} for v in values]


def create_remove_patch(json_pointer: str, values: list[str], current_array: list[str]) -> list[dict[str, Any]]:
    """
    Create patch ops to remove specific items from an array.
    Removes by index in reverse order to avoid shifting.
    """
    indices = []
    for v in values:
        for i, existing in enumerate(current_array):
            if existing == v and i not in indices:
                indices.append(i)
                break
    indices.sort(reverse=True)
    return [{"op": "remove", "path": f"{json_pointer}/{i}"} for i in indices]


def create_replace_patch(json_pointer: str, value: Any) -> list[dict[str, Any]]:
    """Create a patch op to replace a value at json_pointer."""
    return [{"op": "replace", "path": json_pointer, "value": value}]


def dotted_to_pointer(dotted_path: str) -> str:
    """Convert 'entrance_decor.foyer' to '/entrance_decor/foyer'."""
    return "/" + dotted_path.replace(".", "/")
