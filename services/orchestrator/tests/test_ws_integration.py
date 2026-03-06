"""
Integration test — WebSocket session flow.
Tests the full event loop: connect → transcript → state patches → prompts.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages", "schema"))

import pytest
from starlette.testclient import TestClient

from main import app
from session_manager import SessionManager


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure session_mgr is set on app.state before tests."""
    app.state.session_mgr = SessionManager()
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class TestRESTEndpoints:
    def test_create_session(self, client):
        resp = client.post("/session")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["state"]["scope"] == "decoration_hall"

    def test_get_session(self, client):
        create_resp = client.post("/session")
        sid = create_resp.json()["session_id"]
        resp = client.get(f"/session/{sid}")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == sid

    def test_get_missing_session(self, client):
        resp = client.get("/session/nonexistent")
        assert resp.status_code == 404

    def test_export_session(self, client):
        create_resp = client.post("/session")
        sid = create_resp.json()["session_id"]
        resp = client.post(f"/session/{sid}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary_text" in data
        assert "DECORATION HALL BRIEF" in data["summary_text"]


class TestWebSocketFlow:
    def test_greeting_on_connect(self, client):
        create_resp = client.post("/session")
        sid = create_resp.json()["session_id"]

        with client.websocket_connect(f"/ws/session/{sid}") as ws:
            data = json.loads(ws.receive_text())
            assert data["type"] == "server.prompt"
            assert "Maya" in data["payload"]["text"] or "Vanakkam" in data["payload"]["text"]

    def test_transcript_to_state_patch(self, client):
        """Send a final transcript and verify we get state patch + prompt back."""
        create_resp = client.post("/session")
        sid = create_resp.json()["session_id"]

        with client.websocket_connect(f"/ws/session/{sid}") as ws:
            # Receive greeting (1 message)
            greeting = json.loads(ws.receive_text())
            assert greeting["type"] == "server.prompt"

            # Send transcript with known colors
            ws.send_text(json.dumps({
                "type": "client.transcript.final",
                "session_id": sid,
                "payload": {"text": "gold and maroon"}
            }))

            # Expect exactly 3 messages: broadcast transcript + state patch + next prompt
            msg_transcript = json.loads(ws.receive_text())
            assert msg_transcript["type"] == "client.transcript.final"

            msg1 = json.loads(ws.receive_text())
            msg2 = json.loads(ws.receive_text())
            types = {msg1["type"], msg2["type"]}
            assert "server.state.patch" in types
            assert "server.prompt" in types

            # Verify state patch has the colors
            patch_msg = msg1 if msg1["type"] == "server.state.patch" else msg2
            assert "gold" in patch_msg["payload"]["state"]["primary_colors"]
            assert "maroon" in patch_msg["payload"]["state"]["primary_colors"]

    def test_direct_state_edit(self, client):
        create_resp = client.post("/session")
        sid = create_resp.json()["session_id"]

        with client.websocket_connect(f"/ws/session/{sid}") as ws:
            # Receive greeting
            ws.receive_text()

            # Send direct state update (add chip)
            ws.send_text(json.dumps({
                "type": "client.state.update",
                "session_id": sid,
                "payload": {
                    "op": "add",
                    "slot": "primary_colors",
                    "value": "gold"
                }
            }))

            # Expect exactly 1 message: state patch
            raw = ws.receive_text()
            data = json.loads(raw)
            assert data["type"] == "server.state.patch"
            assert "gold" in data["payload"]["state"]["primary_colors"]

    def test_skip_slot(self, client):
        """User says 'no' to skip a slot."""
        create_resp = client.post("/session")
        sid = create_resp.json()["session_id"]

        with client.websocket_connect(f"/ws/session/{sid}") as ws:
            # Receive greeting
            ws.receive_text()

            # Skip primary colors
            ws.send_text(json.dumps({
                "type": "client.transcript.final",
                "session_id": sid,
                "payload": {"text": "no"}
            }))

            # Consume broadcast transcript
            msg_transcript = json.loads(ws.receive_text())
            assert msg_transcript["type"] == "client.transcript.final"

            # Expect 1 message: prompt for next slot (types_of_flowers)
            msg = json.loads(ws.receive_text())
            assert msg["type"] == "server.prompt"
            assert "flower" in msg["payload"]["text"].lower()
