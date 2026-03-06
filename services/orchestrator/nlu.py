"""
NLU parser — rule-based extraction with swappable LLM interface.
Default: keyword matching. LLM parser disabled by default (ENABLE_LLM_NLU=false).
"""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "schema"))

from maya_schema.state import BACKDROP_ALLOWED_TYPES

# ── Known vocabularies ────────────────────────────────────────────

KNOWN_COLORS = [
    "gold", "golden", "maroon", "red", "white", "cream", "ivory", "pink",
    "rose", "rose gold", "blush", "peach", "orange", "yellow", "green",
    "teal", "blue", "navy", "purple", "lavender", "silver", "bronze",
    "copper", "warm white", "cool white", "champagne", "burgundy",
    "magenta", "coral", "sage", "emerald", "ruby", "sapphire",
]

KNOWN_FLOWERS = [
    "jasmine", "rose", "roses", "marigold", "marigolds", "lily", "lilies",
    "orchid", "orchids", "lotus", "chrysanthemum", "tuberose", "carnation",
    "carnations", "sunflower", "sunflowers", "dahlia", "dahlias",
    "hydrangea", "hydrangeas", "peony", "peonies", "gerbera", "gerberas",
    "bougainvillea", "champa", "mogra", "kanakambaram",
]

KNOWN_LIGHT_TYPES = [
    "fairy lights", "string lights", "led lights", "candle lights",
    "paper lanterns", "tea lights", "spotlights", "uplights",
    "neon lights", "tube lights", "warm lights", "warm white lights",
    "cool white lights", "rice lights", "twinkle lights",
    "crystal lights", "chandelier lights",
]

KNOWN_CHANDELIER_TYPES = [
    "crystal chandelier", "floral chandelier", "candle chandelier",
    "modern chandelier", "traditional chandelier", "brass chandelier",
    "glass chandelier", "beaded chandelier", "lantern chandelier",
]

YES_WORDS = {"yes", "yeah", "yep", "sure", "okay", "ok", "yea", "definitely", "absolutely", "of course"}
NO_WORDS = {"no", "nah", "nope", "not really", "none", "nothing", "skip"}
REPLACE_WORDS = {"replace", "change", "swap", "switch", "instead"}
ADD_WORDS = {"add", "also", "additionally", "plus", "include", "more", "as well", "too", "along with"}
REMOVE_WORDS = {"remove", "delete", "drop", "take out", "get rid of", "minus", "without"}
GREETING_WORDS = {"hello", "hi", "hey", "vanakkam", "namaste", "greetings"}


# ── Parser interface ───────────────────────────────────────────────

class NLUParser(ABC):
    """Interface for NLU parsers. Implement parse() to extract slot values from text."""

    @abstractmethod
    def parse(self, text: str, current_slot: str, state: dict[str, Any]) -> dict[str, Any]:
        """
        Parse user text and return extraction result.
        Returns: {
            "values": list[str],       # extracted values
            "intent": str,             # "add" | "remove" | "replace" | "set" | "confirm" | "deny" | "greeting" | "unknown"
            "raw_text": str,
        }
        """
        ...


# ── Rule-based parser ─────────────────────────────────────────────

class RuleBasedParser(NLUParser):
    """Keyword matching + pattern extraction NLU."""

    def parse(self, text: str, current_slot: str, state: dict[str, Any]) -> dict[str, Any]:
        text_lower = text.lower().strip()
        intent = self._detect_intent(text_lower)
        values = self._extract_values(text_lower, current_slot)

        return {
            "values": values,
            "intent": intent,
            "raw_text": text,
        }

    def _detect_intent(self, text: str) -> str:
        """Detect user intent from text."""
        words = set(text.split())

        if any(phrase in text for phrase in ["how are you", "whats up", "what's up", "doing well"]):
            return "greeting"

        if words & REPLACE_WORDS:
            return "replace"
        if words & REMOVE_WORDS:
            return "remove"
        if words & ADD_WORDS:
            return "add"
        if words & YES_WORDS:
            return "confirm"
        if words & NO_WORDS:
            return "deny"
        if words & GREETING_WORDS and len(words) <= 4:
            return "greeting"
        return "set"

    def _extract_values(self, text: str, slot: str) -> list[str]:
        """Extract values relevant to the current slot."""
        if slot in ("primary_colors",):
            return self._match_from_list(text, KNOWN_COLORS)
        elif slot in ("types_of_flowers",):
            return self._match_from_list(text, KNOWN_FLOWERS)
        elif slot in ("backdrop_decor.types",):
            return self._match_from_list(text, list(BACKDROP_ALLOWED_TYPES))
        elif slot in ("decor_lights",):
            found = self._match_from_list(text, KNOWN_LIGHT_TYPES)
            if not found:
                found = self._extract_freeform(text)
            return found
        elif slot in ("chandeliers",):
            found = self._match_from_list(text, KNOWN_CHANDELIER_TYPES)
            if not found:
                found = self._extract_freeform(text)
            return found
        else:
            return self._extract_freeform(text)

    def _match_from_list(self, text: str, known: list[str]) -> list[str]:
        """Match known terms in text, longest match first."""
        found = []
        sorted_known = sorted(known, key=len, reverse=True)
        remaining = text
        for term in sorted_known:
            if term in remaining:
                found.append(term)
                remaining = remaining.replace(term, "", 1)
        return found

    def _extract_freeform(self, text: str) -> list[str]:
        """Extract comma/and-separated freeform values."""
        cleaned = text
        for word in list(REPLACE_WORDS) + list(ADD_WORDS) + list(REMOVE_WORDS) + list(YES_WORDS) + list(NO_WORDS):
            cleaned = cleaned.replace(word, "")

        # Remove filler phrases
        for phrase in ["i want", "i'd like", "i would like", "we want", "we need",
                       "please", "can you", "could you", "let's go with", "go with",
                       "how about", "what about", "maybe", "perhaps", "something like"]:
            cleaned = cleaned.replace(phrase, "")

        parts = re.split(r"[,]|\band\b|\bwith\b", cleaned)
        values = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
        return values


# ── LLM parser (stub, disabled by default) ─────────────────────────

class LLMParser(NLUParser):
    """LLM-based parser. Disabled by default. Set NLU_BACKEND=llm to enable."""

    def __init__(self):
        self.enabled = os.getenv("NLU_BACKEND", "rule_based") == "llm"

    def parse(self, text: str, current_slot: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM parser is disabled. Set NLU_BACKEND=llm to enable.")
        # Placeholder: would call OpenAI chat completions here
        # with a structured prompt to extract slot values
        return {
            "values": [],
            "intent": "unknown",
            "raw_text": text,
        }


# ── Factory ────────────────────────────────────────────────────────

def get_parser() -> NLUParser:
    """Return the configured NLU parser."""
    backend = os.getenv("NLU_BACKEND", "rule_based")
    if backend == "llm":
        return LLMParser()
    return RuleBasedParser()
