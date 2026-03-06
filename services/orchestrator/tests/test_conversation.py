"""
Unit tests for conversation logic, NLU parsing, and session management.
"""
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages", "schema"))

import pytest
from maya_schema.state import create_empty_state, get_nested, SLOT_PRIORITY

from conversation import (
    process_user_input,
    resolve_confirmation,
    get_slot_prompt,
    format_confirmation,
    generate_summary_text,
    COMPLETION_MESSAGE,
)
from nlu import RuleBasedParser
from session_manager import SessionManager


# ── NLU Parser Tests ───────────────────────────────────────────────

class TestRuleBasedParser:
    def setup_method(self):
        self.parser = RuleBasedParser()
        self.state = create_empty_state()

    def test_color_extraction(self):
        result = self.parser.parse("I'd like gold and maroon", "primary_colors", self.state)
        assert "gold" in result["values"]
        assert "maroon" in result["values"]

    def test_flower_extraction(self):
        result = self.parser.parse("jasmine and roses please", "types_of_flowers", self.state)
        assert "jasmine" in result["values"]
        assert "roses" in result["values"]

    def test_backdrop_extraction(self):
        result = self.parser.parse("flowers and pattern", "backdrop_decor.types", self.state)
        assert "flowers" in result["values"]
        assert "pattern" in result["values"]

    def test_intent_add(self):
        result = self.parser.parse("also add blue", "primary_colors", self.state)
        assert result["intent"] == "add"

    def test_intent_remove(self):
        result = self.parser.parse("remove maroon", "primary_colors", self.state)
        assert result["intent"] == "remove"

    def test_intent_replace(self):
        result = self.parser.parse("replace with silver", "primary_colors", self.state)
        assert result["intent"] == "replace"

    def test_intent_confirm(self):
        result = self.parser.parse("yes", "primary_colors", self.state)
        assert result["intent"] == "confirm"

    def test_intent_deny(self):
        result = self.parser.parse("no", "primary_colors", self.state)
        assert result["intent"] == "deny"

    def test_freeform_extraction(self):
        result = self.parser.parse("floral arch, rangoli, lanterns", "entrance_decor.foyer", self.state)
        assert len(result["values"]) >= 2

    def test_light_extraction(self):
        result = self.parser.parse("fairy lights and candle lights", "decor_lights", self.state)
        assert "fairy lights" in result["values"]
        assert "candle lights" in result["values"]


# ── Conversation Logic Tests ───────────────────────────────────────

class TestSlotFillingPriority:
    def test_first_slot_is_primary_colors(self):
        state = create_empty_state()
        from maya_schema.state import get_next_empty_slot
        assert get_next_empty_slot(state) == "primary_colors"

    def test_priority_order(self):
        state = create_empty_state()
        parser = RuleBasedParser()
        from maya_schema.state import get_next_empty_slot
        from maya_schema.patches import apply_patch

        expected_order = SLOT_PRIORITY.copy()
        for i, slot in enumerate(expected_order):
            current = get_next_empty_slot(state)
            assert current == slot, f"Expected {slot} but got {current} at position {i}"
            # Use valid value for backdrop types, dummy for others
            if slot == "backdrop_decor.types":
                parsed = {"values": ["flowers"], "intent": "set", "raw_text": "flowers"}
            else:
                parsed = {"values": ["test_item"], "intent": "set", "raw_text": "test"}
            result = process_user_input("test", slot, parsed, state)
            if result["patch_ops"]:
                state = apply_patch(state, result["patch_ops"])


class TestConfirmationFlow:
    def test_replace_confirmation(self):
        state = create_empty_state()
        state["primary_colors"] = ["gold"]
        ops, text = resolve_confirmation("replace", "primary_colors", ["gold"], ["silver"], state)
        assert len(ops) == 1
        assert ops[0]["op"] == "replace"

    def test_add_confirmation(self):
        state = create_empty_state()
        state["primary_colors"] = ["gold"]
        ops, text = resolve_confirmation("add", "primary_colors", ["gold"], ["silver"], state)
        assert len(ops) == 1
        assert ops[0]["op"] == "add"

    def test_remove_confirmation(self):
        state = create_empty_state()
        state["primary_colors"] = ["gold", "maroon"]
        ops, text = resolve_confirmation("remove", "primary_colors", ["gold", "maroon"], ["maroon"], state)
        assert len(ops) == 1
        assert ops[0]["op"] == "remove"

    def test_existing_values_trigger_confirmation(self):
        state = create_empty_state()
        state["primary_colors"] = ["gold"]
        parsed = {"values": ["silver"], "intent": "set", "raw_text": "silver"}
        result = process_user_input("silver", "primary_colors", parsed, state)
        assert result["needs_confirmation"] is True
        assert result["confirmation_request"] is not None

    def test_explicit_add_skips_confirmation(self):
        state = create_empty_state()
        state["primary_colors"] = ["gold"]
        parsed = {"values": ["silver"], "intent": "add", "raw_text": "add silver"}
        result = process_user_input("add silver", "primary_colors", parsed, state)
        assert result["needs_confirmation"] is False
        assert len(result["patch_ops"]) > 0


class TestProcessUserInput:
    def test_deny_skips_slot(self):
        state = create_empty_state()
        parsed = {"values": [], "intent": "deny", "raw_text": "no"}
        result = process_user_input("no", "primary_colors", parsed, state)
        assert result["next_slot"] == "types_of_flowers"

    def test_no_values_reprompts(self):
        state = create_empty_state()
        parsed = {"values": [], "intent": "set", "raw_text": "um"}
        result = process_user_input("um", "primary_colors", parsed, state)
        assert result["next_slot"] == "primary_colors"
        assert "didn't quite catch" in result["next_prompt"]

    def test_successful_set(self):
        state = create_empty_state()
        parsed = {"values": ["gold", "maroon"], "intent": "set", "raw_text": "gold and maroon"}
        result = process_user_input("gold and maroon", "primary_colors", parsed, state)
        assert result["needs_confirmation"] is False
        assert len(result["patch_ops"]) > 0
        assert "gold" in result["confirmation_text"]


# ── Session Manager Tests ──────────────────────────────────────────

class TestSessionManager:
    def test_create_and_get(self):
        mgr = SessionManager()
        session = mgr.create_session("test-1")
        assert mgr.get_session("test-1") is not None

    def test_missing_session(self):
        mgr = SessionManager()
        assert mgr.get_session("nonexistent") is None

    def test_transcript_accumulation(self):
        mgr = SessionManager()
        mgr.create_session("test-1")
        mgr.add_transcript("test-1", "user", "hello", True)
        mgr.add_transcript("test-1", "maya", "hi!", True)
        session = mgr.get_session("test-1")
        assert len(session["transcript"]) == 2

    def test_state_patching(self):
        mgr = SessionManager()
        mgr.create_session("test-1")
        from maya_schema.patches import create_add_patch
        ops = create_add_patch("/primary_colors", ["gold"])
        new_state = mgr.apply_state_patch("test-1", ops)
        assert new_state["primary_colors"] == ["gold"]


# ── Summary Generation Tests ──────────────────────────────────────

class TestSummaryGeneration:
    def test_generate_summary(self):
        state = create_empty_state()
        state["primary_colors"] = ["gold", "maroon"]
        state["types_of_flowers"] = ["jasmine", "roses"]
        summary = generate_summary_text(state)
        assert "gold" in summary
        assert "maroon" in summary
        assert "jasmine" in summary
        assert "DECORATION HALL BRIEF" in summary

    def test_format_confirmation_single(self):
        assert format_confirmation(["gold"]) == "Got it: gold."

    def test_format_confirmation_multiple(self):
        result = format_confirmation(["gold", "maroon", "white"])
        assert "gold" in result
        assert "maroon" in result
        assert "white" in result
