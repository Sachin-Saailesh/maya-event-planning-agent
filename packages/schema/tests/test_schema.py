"""
Unit tests for state schema, JSON patch operations, and confirmation logic.
"""
import pytest
from maya_schema.state import (
    create_empty_state,
    get_nested,
    set_nested,
    get_next_empty_slot,
    slot_is_filled,
    validate_backdrop_types,
    BACKDROP_ALLOWED_TYPES,
)
from maya_schema.patches import (
    apply_patch,
    create_add_patch,
    create_remove_patch,
    create_replace_patch,
    dotted_to_pointer,
)
from maya_schema.events import EventType, create_event


# ── State creation ─────────────────────────────────────────────────

class TestCreateEmptyState:
    def test_all_fields_present(self):
        s = create_empty_state()
        assert s["scope"] == "decoration_hall"
        assert s["primary_colors"] == []
        assert s["types_of_flowers"] == []
        assert s["props"] == []
        assert s["chandeliers"] == []
        assert s["decor_lights"] == []
        assert s["hall_decor"] == []
        assert s["selfie_booth_decor"] == []
        assert s["entrance_decor"]["foyer"] == []
        assert s["entrance_decor"]["garlands"] == []
        assert s["entrance_decor"]["name_board"] == []
        assert s["entrance_decor"]["top_decor_at_entrance"] == []
        assert s["backdrop_decor"]["enabled"] is False
        assert s["backdrop_decor"]["types"] == []

    def test_independent_copies(self):
        s1 = create_empty_state()
        s2 = create_empty_state()
        s1["primary_colors"].append("gold")
        assert s2["primary_colors"] == []


# ── Nested access ──────────────────────────────────────────────────

class TestNestedAccess:
    def test_get_nested(self):
        s = create_empty_state()
        s["entrance_decor"]["foyer"] = ["flowers"]
        assert get_nested(s, "entrance_decor.foyer") == ["flowers"]

    def test_set_nested(self):
        s = create_empty_state()
        set_nested(s, "backdrop_decor.enabled", True)
        assert s["backdrop_decor"]["enabled"] is True

    def test_get_nested_top_level(self):
        s = create_empty_state()
        s["primary_colors"] = ["red"]
        assert get_nested(s, "primary_colors") == ["red"]


# ── Slot filling ───────────────────────────────────────────────────

class TestSlotFilling:
    def test_first_empty_slot(self):
        s = create_empty_state()
        assert get_next_empty_slot(s) == "primary_colors"

    def test_after_filling_first(self):
        s = create_empty_state()
        s["primary_colors"] = ["gold"]
        assert get_next_empty_slot(s) == "types_of_flowers"

    def test_all_filled(self):
        s = create_empty_state()
        s["primary_colors"] = ["gold"]
        s["types_of_flowers"] = ["jasmine"]
        s["entrance_decor"]["foyer"] = ["arch"]
        s["entrance_decor"]["garlands"] = ["mango leaves"]
        s["entrance_decor"]["name_board"] = ["floral"]
        s["entrance_decor"]["top_decor_at_entrance"] = ["drape"]
        s["backdrop_decor"]["types"] = ["flowers"]
        s["decor_lights"] = ["fairy lights"]
        s["chandeliers"] = ["crystal"]
        s["props"] = ["table"]
        s["selfie_booth_decor"] = ["frame"]
        s["hall_decor"] = ["ribbon"]
        assert get_next_empty_slot(s) is None

    def test_slot_is_filled(self):
        s = create_empty_state()
        assert slot_is_filled(s, "primary_colors") is False
        s["primary_colors"] = ["white"]
        assert slot_is_filled(s, "primary_colors") is True


# ── Backdrop validation ────────────────────────────────────────────

class TestBackdropValidation:
    def test_valid_types(self):
        assert validate_backdrop_types(["flowers", "pattern"]) == ["flowers", "pattern"]

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid backdrop types"):
            validate_backdrop_types(["flowers", "neon"])


# ── JSON Patch operations ─────────────────────────────────────────

class TestAddPatch:
    def test_add_to_empty_array(self):
        s = create_empty_state()
        ops = create_add_patch("/primary_colors", ["gold", "maroon"])
        result = apply_patch(s, ops)
        assert result["primary_colors"] == ["gold", "maroon"]

    def test_add_to_existing_array(self):
        s = create_empty_state()
        s["primary_colors"] = ["gold"]
        ops = create_add_patch("/primary_colors", ["maroon"])
        result = apply_patch(s, ops)
        assert result["primary_colors"] == ["gold", "maroon"]

    def test_add_nested(self):
        s = create_empty_state()
        ops = create_add_patch("/entrance_decor/foyer", ["floral arch", "rangoli"])
        result = apply_patch(s, ops)
        assert result["entrance_decor"]["foyer"] == ["floral arch", "rangoli"]


class TestRemovePatch:
    def test_remove_single_item(self):
        s = create_empty_state()
        s["primary_colors"] = ["gold", "maroon", "white"]
        ops = create_remove_patch("/primary_colors", ["maroon"], s["primary_colors"])
        result = apply_patch(s, ops)
        assert result["primary_colors"] == ["gold", "white"]

    def test_remove_multiple_items(self):
        s = create_empty_state()
        s["primary_colors"] = ["gold", "maroon", "white"]
        ops = create_remove_patch("/primary_colors", ["gold", "white"], s["primary_colors"])
        result = apply_patch(s, ops)
        assert result["primary_colors"] == ["maroon"]


class TestReplacePatch:
    def test_replace_array(self):
        s = create_empty_state()
        s["primary_colors"] = ["gold"]
        ops = create_replace_patch("/primary_colors", ["silver", "blue"])
        result = apply_patch(s, ops)
        assert result["primary_colors"] == ["silver", "blue"]

    def test_replace_boolean(self):
        s = create_empty_state()
        ops = create_replace_patch("/backdrop_decor/enabled", True)
        result = apply_patch(s, ops)
        assert result["backdrop_decor"]["enabled"] is True


class TestBackdropMultiSelect:
    """Backdrop types must support add/remove without overwriting others."""

    def test_add_one_type(self):
        s = create_empty_state()
        s["backdrop_decor"]["types"] = ["flowers"]
        ops = create_add_patch("/backdrop_decor/types", ["pattern"])
        result = apply_patch(s, ops)
        assert set(result["backdrop_decor"]["types"]) == {"flowers", "pattern"}

    def test_remove_one_type_keeps_others(self):
        s = create_empty_state()
        s["backdrop_decor"]["types"] = ["flowers", "pattern", "flower_lights"]
        ops = create_remove_patch(
            "/backdrop_decor/types",
            ["pattern"],
            s["backdrop_decor"]["types"],
        )
        result = apply_patch(s, ops)
        assert set(result["backdrop_decor"]["types"]) == {"flowers", "flower_lights"}

    def test_add_then_remove(self):
        s = create_empty_state()
        ops1 = create_add_patch("/backdrop_decor/types", ["flowers", "pattern"])
        s = apply_patch(s, ops1)
        assert set(s["backdrop_decor"]["types"]) == {"flowers", "pattern"}
        ops2 = create_remove_patch("/backdrop_decor/types", ["flowers"], s["backdrop_decor"]["types"])
        s = apply_patch(s, ops2)
        assert s["backdrop_decor"]["types"] == ["pattern"]


# ── Path conversion ────────────────────────────────────────────────

class TestPathConversion:
    def test_dotted_to_pointer(self):
        assert dotted_to_pointer("entrance_decor.foyer") == "/entrance_decor/foyer"
        assert dotted_to_pointer("primary_colors") == "/primary_colors"
        assert dotted_to_pointer("backdrop_decor.types") == "/backdrop_decor/types"


# ── Events ─────────────────────────────────────────────────────────

class TestEvents:
    def test_create_event(self):
        evt = create_event(EventType.SERVER_PROMPT, "sess-1", {"text": "Hello!"})
        assert evt["type"] == "server.prompt"
        assert evt["session_id"] == "sess-1"
        assert evt["payload"]["text"] == "Hello!"
        assert "timestamp" in evt

    def test_event_types(self):
        assert EventType.CLIENT_AUDIO_STARTED == "client.audio.started"
        assert EventType.CLIENT_TRANSCRIPT_PARTIAL == "client.transcript.partial"
        assert EventType.SERVER_STATE_PATCH == "server.state.patch"
        assert EventType.SERVER_CONFIRMATION_REQUEST == "server.confirmation.request"
