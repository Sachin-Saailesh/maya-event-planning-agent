"""
Tool execution framework for Maya voice agent.
Registry-based tool system for decoration planning capabilities.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable, Awaitable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "schema"))

logger = logging.getLogger(__name__)

# ── Tool Registry ──────────────────────────────────────────────────

_TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(name: str, description: str):
    """Decorator to register a tool function."""
    def decorator(fn):
        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "function": fn,
        }
        return fn
    return decorator


def get_available_tools() -> list[dict[str, str]]:
    """Return list of available tools with names and descriptions."""
    return [
        {"name": t["name"], "description": t["description"]}
        for t in _TOOL_REGISTRY.values()
    ]


async def execute_tool(name: str, args: dict[str, Any], session_state: dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool by name."""
    tool = _TOOL_REGISTRY.get(name)
    if not tool:
        return {"success": False, "error": f"Unknown tool: {name}"}

    try:
        result = tool["function"](args, session_state)
        if hasattr(result, "__await__"):
            result = await result
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Tool execution failed [{name}]: {e}")
        return {"success": False, "error": str(e)}


# ── Tool Intent Detection ─────────────────────────────────────────

TOOL_TRIGGERS = {
    "generate_decor_brief": ["generate brief", "create brief", "export brief", "make brief", "summary brief", "decoration brief"],
    "suggest_decor_themes": ["suggest theme", "theme suggestion", "recommend theme", "decoration theme", "what theme", "style suggestion"],
    "shortlist_vendors": ["find vendor", "vendor list", "vendor suggestion", "recommend vendor", "shortlist vendor", "decorator list"],
    "schedule_site_visit": ["schedule visit", "book visit", "site visit", "venue visit", "hall visit", "plan visit"],
}


def detect_tool_intent(text: str) -> str | None:
    """Detect if user text triggers a tool call. Returns tool name or None."""
    text_lower = text.lower()
    for tool_name, triggers in TOOL_TRIGGERS.items():
        for trigger in triggers:
            if trigger in text_lower:
                return tool_name
    return None


# ── Built-in Tools ─────────────────────────────────────────────────

@register_tool("generate_decor_brief", "Generate a formatted decoration brief from the current planning state")
def generate_decor_brief(args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Generate a formatted decoration brief."""
    from conversation import generate_summary_text
    brief = generate_summary_text(state)
    return {
        "brief": brief,
        "message": "I've generated your decoration brief! Here's a summary of everything we've planned.",
    }


@register_tool("suggest_decor_themes", "Suggest decoration themes based on current preferences")
def suggest_decor_themes(args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Suggest decoration themes based on selected colors and flowers."""
    colors = state.get("primary_colors", [])
    flowers = state.get("types_of_flowers", [])

    themes = []

    # Theme suggestions based on color palette
    color_set = set(c.lower() for c in colors)
    if color_set & {"gold", "maroon", "red"}:
        themes.append({
            "name": "Traditional Temple",
            "description": "Rich gold and maroon palette with brass accents, temple bells, and traditional kolam designs",
            "keywords": ["brass lamps", "kolam", "temple bells", "silk drapes"],
        })
    if color_set & {"white", "ivory", "cream", "blush", "pink"}:
        themes.append({
            "name": "Elegant Minimalist",
            "description": "Soft whites and pastels with clean lines, white florals, and crystal accents",
            "keywords": ["white lilies", "crystal chandeliers", "sheer drapes"],
        })
    if color_set & {"green", "sage", "emerald", "teal"}:
        themes.append({
            "name": "Tropical Garden",
            "description": "Lush greens with tropical foliage, banana plants, and natural elements",
            "keywords": ["banana leaves", "ferns", "hanging gardens", "wooden props"],
        })
    if color_set & {"purple", "lavender", "rose gold"}:
        themes.append({
            "name": "Royal Luxe",
            "description": "Regal purples with rose gold accents, velvet drapes, and orchid arrangements",
            "keywords": ["velvet", "orchids", "chandeliers", "candelabras"],
        })

    if not themes:
        themes.append({
            "name": "Classic South Indian",
            "description": "Jasmine and marigold garlands, banana stems, mango leaf thoranam, and brass uruli",
            "keywords": ["jasmine", "marigold", "thoranam", "uruli", "brass lamps"],
        })

    return {
        "themes": themes,
        "message": f"Based on your choices, I'd suggest these {len(themes)} theme(s). Would you like to explore any of them?",
    }


@register_tool("shortlist_vendors", "Suggest decoration vendors based on style and location")
def shortlist_vendors(args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Suggest vendors based on decoration style."""
    # In production, this would query a vendor database
    vendors = [
        {
            "name": "Kalyana Mandapam Decorators",
            "speciality": "Traditional South Indian weddings",
            "rating": 4.8,
            "location": "Chennai",
        },
        {
            "name": "Bloom & Petal Studios",
            "speciality": "Floral arrangements and mandap decor",
            "rating": 4.7,
            "location": "Bangalore",
        },
        {
            "name": "Royal Event Decors",
            "speciality": "Luxury wedding setups",
            "rating": 4.9,
            "location": "Hyderabad",
        },
    ]
    return {
        "vendors": vendors,
        "message": "Here are some recommended decoration vendors. Shall I help you schedule a consultation?",
    }


@register_tool("schedule_site_visit", "Schedule a venue decoration site visit")
def schedule_site_visit(args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Schedule a site visit."""
    return {
        "status": "request_noted",
        "message": (
            "I've noted your request for a site visit. "
            "Our team will reach out to confirm the date and time. "
            "In the meantime, let's continue planning your decoration!"
        ),
    }
