"""
NLU parser — rule-based extraction with swappable LLM interface.
Default: keyword matching. LLM parser disabled by default (ENABLE_LLM_NLU=false).

Key improvements:
- Context-first interpretation: short answers resolve against the active slot
- Slot-local synonym maps: "lights" -> "flower_lights" for backdrop, etc.
- Compound short answers: "yeah, just one" correctly extracts "one"
- Domain guard: rejects implausible ASR output relative to wedding decor domain
- Better intent: mixed affirmative+content yields "set" not "confirm"
"""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "schema"))

from maya_schema.state import BACKDROP_ALLOWED_TYPES, SLOT_PRIORITY

# ── Known vocabularies ─────────────────────────────────────────

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

# ── Slot-local synonym maps ────────────────────────────────────
# Maps user shorthand → canonical schema value, keyed by slot.
# Applied BEFORE generic extraction to handle contextual meaning.

SLOT_SYNONYMS: dict[str, dict[str, str]] = {
    "backdrop_decor.types": {
        "lights":        "flower_lights",
        "light":         "flower_lights",
        "lit":           "flower_lights",
        "floral":        "flowers",
        "floral wall":   "flowers",
        "flower wall":   "flowers",
        "flower":        "flowers",
        "geometric":     "pattern",
        "design":        "pattern",
        "textile":       "pattern",
    },
    "entrance_decor.name_board": {
        "one":       "yes",
        "just one":  "yes",
        "a board":   "yes",
        "one board": "yes",
        "yeah":      "yes",
        "sure":      "yes",
        "yep":       "yes",
        "ok":        "yes",
        "okay":      "yes",
    },
    "chandeliers": {
        "crystal":   "crystal chandelier",
        "floral":    "floral chandelier",
        "brass":     "brass chandelier",
        "glass":     "glass chandelier",
        "candle":    "candle chandelier",
        "modern":    "modern chandelier",
        "trad":      "traditional chandelier",
        "traditional":"traditional chandelier",
    },
    "primary_colors": {
        "golden": "gold",
        "saffron": "orange",
        "cream": "ivory",
        "off white": "ivory",
        "blush": "rose",
    },
}

# Slots where a bare "yes/sure/ok" confirm intent can be stored as a value
# (boolean-style slots where the question is effectively yes/no).
AFFIRMATIVE_SLOTS = {
    "entrance_decor.name_board",
    "entrance_decor.garlands",
    "chandeliers",
    "selfie_booth_decor",
}

# Domain guard: words that strongly suggest the text is NOT wedding-decor input.
# Used to reject implausible ASR hallucinations.
DOMAIN_REJECT_PATTERNS = [
    r"www\.", r"\.com", r"\.net", r"\.org",
    r"subscribe", r"thanks for watching", r"learn more at",
    r"click here", r"sponsored", r"advertisement",
    r"lambda\b", r"\bfunction\b.*\breturn\b",   # code snippets
    r"stock market", r"bitcoin", r"crypto",
    r"breaking news", r"weather forecast",
]


# ── Parser interface ───────────────────────────────────────────

class NLUParser(ABC):
    """Interface for NLU parsers."""

    @abstractmethod
    async def parse(self, text: str, current_slot: str, state: dict[str, Any], context: str = "") -> dict[str, Any]:
        """
        Parse user text and return extraction result.
        Returns: {
            "values": list[str],
            "intent": str,   # "add"|"remove"|"replace"|"set"|"confirm"|"deny"|"greeting"|"unknown"
            "raw_text": str,
        }
        context: optional RAG / sliding-window transcript context (LLM backend only).
        """
        ...


# ── Rule-based parser ──────────────────────────────────────────

class RuleBasedParser(NLUParser):
    """Keyword + synonym matching NLU, context-first."""

    async def parse(self, text: str, current_slot: str, state: dict[str, Any], _context: str = "") -> dict[str, Any]:
        text_lower = text.lower().strip()

        # Domain guard — reject implausible ASR garbage
        if _is_domain_irrelevant(text_lower):
            return {"values": [], "intent": "unknown", "raw_text": text}

        # 1. Try slot-local synonyms first (context-first interpretation)
        slot_values = self._apply_slot_synonyms(text_lower, current_slot)

        # 2. Detect intent
        intent = self._detect_intent(text_lower, has_slot_values=bool(slot_values))

        # 3. If synonyms gave values, use them; otherwise generic extraction
        if slot_values:
            values = slot_values
        else:
            values = self._extract_values(text_lower, current_slot)

        # 4. For pure-affirmative responses to AFFIRMATIVE_SLOTS, synthesise "yes"
        if intent == "confirm" and not values and current_slot in AFFIRMATIVE_SLOTS:
            values = ["yes"]

        return {
            "values": values,
            "intent": intent,
            "raw_text": text,
        }

    def _apply_slot_synonyms(self, text: str, slot: str) -> list[str]:
        """Check if any slot-local synonym matches the user text."""
        synonyms = SLOT_SYNONYMS.get(slot, {})
        if not synonyms:
            return []
        # Sorted longest-first to prefer more specific matches
        found = []
        remaining = text
        for phrase in sorted(synonyms.keys(), key=len, reverse=True):
            if re.search(r'\b' + re.escape(phrase) + r'\b', remaining):
                canonical = synonyms[phrase]
                if canonical not in found:
                    found.append(canonical)
                remaining = re.sub(r'\b' + re.escape(phrase) + r'\b', '', remaining, count=1)
        return found

    def _detect_intent(self, text: str, has_slot_values: bool = False) -> str:
        """
        Detect intent.

        Key change from original:
        - If the text contains BOTH affirmative words AND content words
          (i.e. has_slot_values or extracted values exist), lean toward "set"
          rather than "confirm" — the user is answering, not just saying yes.
        """
        words = set(re.findall(r'\b\w+\b', text.lower()))

        if any(phrase in text for phrase in ["how are you", "whats up", "what's up", "doing well"]):
            return "greeting"

        if words & REPLACE_WORDS:
            return "replace"
        if words & REMOVE_WORDS:
            return "remove"
        if words & ADD_WORDS:
            return "add"

        has_affirmative = bool(words & YES_WORDS)
        has_negative    = bool(words & NO_WORDS)

        if has_affirmative:
            # Mixed: affirmative + content → treat as "set" so values flow through
            if has_slot_values:
                return "set"
            # Pure affirmative (only yes-words and filler) → confirm
            non_affirmative = words - YES_WORDS - {"just", "one", "a", "the", "it", "that", "this", "so"}
            if not non_affirmative:
                return "confirm"
            return "set"

        if has_negative:
            return "deny"
        if words & GREETING_WORDS and len(words) <= 4:
            return "greeting"
        return "set"

    def _extract_values(self, text: str, slot: str) -> list[str]:
        """Extract values relevant to the current slot."""
        if slot == "primary_colors":
            return self._match_from_list(text, KNOWN_COLORS)
        elif slot == "types_of_flowers":
            return self._match_from_list(text, KNOWN_FLOWERS)
        elif slot == "backdrop_decor.types":
            # Include extra aliases alongside schema values
            extras = ["lights", "flower lights", "floral", "flower wall"]
            candidates = list(BACKDROP_ALLOWED_TYPES) + extras
            found = self._match_from_list(text, candidates)
            # Normalise to schema values via synonym map + built-in logic
            return [_normalise_backdrop(v) for v in found]
        elif slot == "decor_lights":
            found = self._match_from_list(text, KNOWN_LIGHT_TYPES)
            return found if found else self._extract_freeform(text)
        elif slot == "chandeliers":
            found = self._match_from_list(text, KNOWN_CHANDELIER_TYPES)
            return found if found else self._extract_freeform(text)
        else:
            return self._extract_freeform(text)

    def _match_from_list(self, text: str, known: list[str]) -> list[str]:
        """Match known terms in text, longest match first.

        Normalises underscores to spaces so 'flower_lights' matches 'flower lights'.
        Returns the original (possibly underscore) form for schema compliance.
        """
        found = []
        normalized_map = {term.replace("_", " "): term for term in known}
        sorted_normalized = sorted(normalized_map.keys(), key=len, reverse=True)
        remaining = text
        for norm_term in sorted_normalized:
            if norm_term in remaining:
                found.append(normalized_map[norm_term])
                remaining = remaining.replace(norm_term, "", 1)
        return found

    def _extract_freeform(self, text: str) -> list[str]:
        """Extract comma/and-separated freeform values, stripping intent words."""
        cleaned = text
        words_to_remove = (
            list(REPLACE_WORDS) + list(ADD_WORDS) + list(REMOVE_WORDS)
            + list(YES_WORDS) + list(NO_WORDS)
        )
        for word in words_to_remove:
            cleaned = re.sub(r'\b' + re.escape(word) + r'\b', '', cleaned, flags=re.IGNORECASE)

        # Remove filler phrases
        for phrase in [
            "i want", "i'd like", "i would like", "we want", "we need",
            "please", "can you", "could you", "let's go with", "go with",
            "how about", "what about", "maybe", "perhaps", "something like",
            "go for", "go ahead with",
        ]:
            cleaned = re.sub(r'\b' + re.escape(phrase) + r'\b', '', cleaned, flags=re.IGNORECASE)

        parts = re.split(r"[,]|\band\b|\bwith\b", cleaned)
        values = [
            p.strip().strip('.!?').strip()
            for p in parts
            if p.strip() and len(p.strip().strip('.!?').strip()) > 1
        ]
        return values


# ── LLM parser (stub, disabled by default) ────────────────────

class LLMParser(NLUParser):
    """LLM-based parser. Set NLU_BACKEND=llm to enable."""

    def __init__(self):
        self.enabled = os.getenv("NLU_BACKEND", "rule_based") == "llm"
        if self.enabled:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def parse(self, text: str, current_slot: str, state: dict[str, Any], context: str = "") -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM parser is disabled. Set NLU_BACKEND=llm to enable.")

        context_block = (
            f"\n\nConversation context (for reference — do not override the user's explicit answer):\n{context}"
            if context else ""
        )

        prompt = f"""You are an NLU engine for a South Indian wedding decoration planner.
Extract the decoration preferences from the user's text.
Current slot being asked about: "{current_slot}"
Available slots: {", ".join(SLOT_PRIORITY)}

User's response: "{text}"

Return a JSON object exactly like this:
{{
  "slot": "the slot the user is actually answering (default to {current_slot} if ambiguous)",
  "values": ["list", "of", "extracted", "keywords"],
  "intent": "add" | "remove" | "replace" | "set" | "confirm" | "deny" | "greeting" | "acknowledgment" | "unknown"
}}

Rules:
1. ONLY extract relevant decoration keywords (e.g., "floral arch", "maroon").
2. EXCLUDE conversational filler ("I want", "a", "can you", "please").
3. CRITICAL: If the user says something irrelevant or clearly off-topic (e.g. a URL, code, unrelated topic), return "values": [] and "intent": "unknown". DO NOT discard quantities or boolean answers like "just one" or "yeah sure".
4. For AFFIRMATIVE slots ({', '.join(AFFIRMATIVE_SLOTS)}): treat "yes", "sure", "okay", "just one", "one" as values=["yes"] with intent="confirm".
5. Determine the intent:
   - "confirm" for pure "yes/sure", "deny" for "no/skip"
   - "add" for adding to a list, "replace" or "remove" if they specify it.
   - "set" for giving a direct answer (even if it starts with "yeah").
   - "greeting" if they just say Hi/Hello.
   - "acknowledgment" if they just say "perfect", "great", "awesome" without new details.
6. Use slot context: if current slot is "backdrop_decor.types", map "lights" -> "flower_lights".
7. If the user explicitly mentions colors, slot MUST be "primary_colors".
   If the user explicitly mentions flowers, slot MUST be "types_of_flowers".{context_block}"""

        try:
            import json
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            return {
                "slot":    parsed.get("slot", current_slot),
                "values":  parsed.get("values", []),
                "intent":  parsed.get("intent", "unknown"),
                "raw_text": text,
            }
        except Exception:
            return {"slot": current_slot, "values": [], "intent": "unknown", "raw_text": text}


# ── Helpers ────────────────────────────────────────────────────

def _is_domain_irrelevant(text: str) -> bool:
    """Return True if the text is clearly outside the wedding-decor domain."""
    for pattern in DOMAIN_REJECT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _normalise_backdrop(value: str) -> str:
    """Normalise a backdrop value to one of the three schema values."""
    v = value.lower().replace("_", " ")
    if "light" in v or v in ("lit",):
        return "flower_lights"
    if "flower" in v or "floral" in v:
        return "flowers"
    if "pattern" in v or "geometric" in v or "design" in v:
        return "pattern"
    return value  # pass through — validate_backdrop_types will catch invalids


# ── Factory ────────────────────────────────────────────────────

def get_parser() -> NLUParser:
    """Return the configured NLU parser."""
    backend = os.getenv("NLU_BACKEND", "rule_based")
    if backend == "llm":
        return LLMParser()
    return RuleBasedParser()
