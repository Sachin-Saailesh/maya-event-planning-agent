"""
Content guardrails for Maya voice agent.
Filters unsafe content and enforces the wedding planning domain.
"""
from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Domain keywords ────────────────────────────────────────────────
WEDDING_DOMAIN_KEYWORDS = {
    "wedding", "decoration", "decor", "flower", "flowers", "garland",
    "color", "colour", "light", "lights", "chandelier", "backdrop",
    "entrance", "foyer", "hall", "venue", "stage", "mandap", "mandapam",
    "rangoli", "kolam", "thoranam", "prop", "props", "selfie", "booth",
    "drape", "drapes", "canopy", "arch", "pillar", "table", "aisle",
    "bride", "groom", "reception", "ceremony", "sangeet", "mehendi",
    "haldi", "south indian", "tamil", "telugu", "kannada", "malayalam",
    "theme", "style", "vendor", "brief", "plan", "budget", "gold",
    "maroon", "ivory", "rose", "jasmine", "marigold", "orchid", "lily",
    "lotus", "mango", "banana", "plant", "silk", "satin",
    # confirmation/navigation words
    "yes", "no", "ok", "okay", "sure", "skip", "next", "add", "replace",
    "remove", "change", "keep", "want", "like", "prefer", "need",
    "hello", "hi", "vanakkam", "namaste", "thanks", "thank",
}

# ── Blocked patterns ──────────────────────────────────────────────
BLOCKED_PATTERNS = [
    re.compile(r"\b(kill|murder|attack|bomb|weapon|gun|knife|harm|hurt|abuse|violence|hate)\b", re.I),
    re.compile(r"\b(drugs?|cocaine|heroin|meth|marijuana|cannabis)\b", re.I),
    re.compile(r"\b(hack|exploit|malware|phishing|scam|fraud)\b", re.I),
    re.compile(r"\b(porn|xxx|explicit|nsfw|nude)\b", re.I),
]

# ── PII patterns ──────────────────────────────────────────────────
PII_PATTERNS = [
    (re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"), "[SSN REDACTED]"),          # SSN
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[CARD REDACTED]"), # Credit card
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"), # Email
]


class GuardrailResult:
    """Result of a guardrail check."""

    def __init__(self, safe: bool, reason: str = "", filtered_text: str = ""):
        self.safe = safe
        self.reason = reason
        self.filtered_text = filtered_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "reason": self.reason,
            "filtered_text": self.filtered_text,
        }


def check_input(text: str) -> GuardrailResult:
    """
    Check incoming user transcript for safety and domain relevance.
    Returns GuardrailResult with safe=True if text is acceptable.
    """
    if not text or not text.strip():
        return GuardrailResult(safe=True, filtered_text=text)

    text_lower = text.lower().strip()

    # 1. Check for blocked content
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(text_lower):
            logger.warning(f"Guardrail blocked input: {text[:50]}...")
            return GuardrailResult(
                safe=False,
                reason="blocked_content",
                filtered_text="",
            )

    # 2. Redact PII
    filtered = text
    for pattern, replacement in PII_PATTERNS:
        filtered = pattern.sub(replacement, filtered)

    # 3. Domain relevance check (lenient — only block clearly off-topic long inputs)
    words = set(re.findall(r"[a-z]+", text_lower))
    if len(words) > 8:
        domain_overlap = words & WEDDING_DOMAIN_KEYWORDS
        if len(domain_overlap) == 0:
            logger.info(f"Guardrail: off-topic input detected: {text[:50]}...")
            return GuardrailResult(
                safe=False,
                reason="off_topic",
                filtered_text="",
            )

    return GuardrailResult(safe=True, filtered_text=filtered)


def check_output(text: str) -> GuardrailResult:
    """
    Check outgoing Maya response for safety.
    """
    if not text or not text.strip():
        return GuardrailResult(safe=True, filtered_text=text)

    # Check for blocked content in responses
    text_lower = text.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(text_lower):
            logger.warning(f"Guardrail blocked output: {text[:50]}...")
            return GuardrailResult(
                safe=False,
                reason="unsafe_response",
                filtered_text="I can help you plan your wedding decoration. What would you like to know?",
            )

    return GuardrailResult(safe=True, filtered_text=text)


def get_guardrail_message(reason: str) -> str:
    """Get a user-friendly message for a guardrail block."""
    messages = {
        "blocked_content": "I'm here to help with wedding decoration planning. Let's focus on making your event beautiful!",
        "off_topic": "I specialise in South Indian wedding decorations. Could you tell me about your decoration preferences instead?",
        "unsafe_response": "Let me help you with your wedding decoration planning.",
    }
    return messages.get(reason, "Let's continue with your decoration planning!")
