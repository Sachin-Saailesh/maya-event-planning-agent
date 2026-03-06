# Maya — Wedding Decoration Voice Planner

AI voice agent that helps plan South Indian wedding hall decorations through natural conversation.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Browser                              │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  Transcript │  │  State Panel │  │  Web Speech TTS   │   │
│  │  (live)     │  │  (chips)     │  │  (Maya's voice)   │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘   │
│         │ WebSocket      │ WebSocket          │              │
│         └───────┬────────┘                    │              │
│  ┌──────────────▼──────────────────┐          │              │
│  │  LiveKit WebRTC (mic audio) ────┼──────────┘              │
│  └──────────────┬──────────────────┘                         │
└─────────────────┼────────────────────────────────────────────┘
                  │
     ┌────────────▼────────────────┐
     │    LiveKit Server (SFU)     │  ← Docker container
     └────────────┬────────────────┘
                  │
     ┌────────────▼────────────────┐
     │    Agent Worker (Python)    │
     │  ┌────────┐  ┌───────────┐ │
     │  │  VAD   │→ │ Whisper   │ │
     │  │(energy)│  │ STT (API) │ │
     │  └────────┘  └─────┬─────┘ │
     └────────────────────┼────────┘
                          │ WebSocket
     ┌────────────────────▼────────┐
     │   Orchestrator (FastAPI)    │
     │  ┌────────┐ ┌────────────┐ │
     │  │  NLU   │ │ Slot-Fill  │ │
     │  │(rules) │ │ Conversa-  │ │
     │  └───┬────┘ │ tion Logic │ │
     │      │      └─────┬──────┘ │
     │  ┌───▼────────────▼──────┐ │
     │  │  Session Manager      │ │
     │  │  (JSON Patch/RFC6902) │ │
     │  └───────────┬───────────┘ │
     └──────────────┼──────────────┘
                    │
     ┌──────────────▼──────────────┐
     │    PostgreSQL (optional)    │
     │  sessions │ transcripts    │
     └────────────────────────────┘
```

## Monorepo Layout

```
maya-event-planning-agent/
├── apps/web/              # React + Vite frontend
├── services/
│   ├── orchestrator/      # FastAPI backend
│   └── agent_worker/      # LiveKit + Whisper worker
├── packages/schema/       # Shared state, events, patches
├── infra/                 # Docker, LiveKit config
├── Makefile
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.11+, Node 18+, Docker (for LiveKit/Postgres)

### 1. Setup

```bash
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

# Python deps
pip install -e packages/schema
pip install -r services/orchestrator/requirements.txt

# Frontend deps
cd apps/web && npm install && cd ../..
```

### 2. Start Infrastructure (optional — for voice mode)

```bash
cd infra && docker compose up -d
```

### 3. Run Services

**Terminal 1 — Orchestrator:**

```bash
cd services/orchestrator
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**

```bash
cd apps/web
npm run dev
```

**Terminal 3 — Agent Worker (only for voice mode):**

```bash
cd services/agent_worker
python worker.py <session-id>
```

### 4. Open Browser

Navigate to `http://localhost:5173`

## Testing

### Run Tests

```bash
# Schema tests
python -m pytest packages/schema/tests/ -v

# Orchestrator tests (conversation + WS integration)
python -m pytest services/orchestrator/tests/ -v
```

### Test Without LiveKit (Text Mode)

1. Start orchestrator + frontend (steps above)
2. Open `http://localhost:5173`
3. Click "Start Planning with Maya"
4. Type responses in the text input — Maya responds via TTS and the state panel updates

### Test Full Voice Loop

1. Start Docker infrastructure (`cd infra && docker compose up -d`)
2. Start all three services
3. Open browser, grant mic permissions
4. Speak decoration preferences — partial transcripts appear live
5. State chips update, Maya speaks responses

## Event Protocol

All messages use this envelope:

```json
{
  "type": "server.prompt",
  "session_id": "abc-123",
  "timestamp": 1709654321.123,
  "payload": { "text": "What primary colours would you like?" }
}
```

### Event Types

| Type                          | Direction       | Payload                                                      |
| ----------------------------- | --------------- | ------------------------------------------------------------ |
| `client.audio.started`        | Client → Server | `{}`                                                         |
| `client.transcript.partial`   | Client → Server | `{ "text": "gol..." }`                                       |
| `client.transcript.final`     | Client → Server | `{ "text": "gold and maroon" }`                              |
| `client.state.update`         | Client → Server | `{ "op": "add", "slot": "primary_colors", "value": "blue" }` |
| `server.prompt`               | Server → Client | `{ "text": "Got it: gold and maroon. What flowers?" }`       |
| `server.state.patch`          | Server → Client | `{ "ops": [...], "state": {...} }`                           |
| `server.confirmation.request` | Server → Client | `{ "slot": "...", "options": ["replace","add","remove"] }`   |
| `server.summary.ready`        | Server → Client | `{ "summary": "..." }`                                       |

### State Patch Example (RFC6902)

```json
{
  "type": "server.state.patch",
  "payload": {
    "ops": [
      { "op": "add", "path": "/primary_colors/-", "value": "gold" },
      { "op": "add", "path": "/primary_colors/-", "value": "maroon" }
    ],
    "state": { "primary_colors": ["gold", "maroon"], "...": "..." }
  }
}
```

## State Schema

```json
{
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
    "top_decor_at_entrance": []
  },
  "selfie_booth_decor": [],
  "backdrop_decor": {
    "enabled": false,
    "types": []
  }
}
```

**Backdrop types** (multi-select): `"flowers"`, `"pattern"`, `"flower_lights"`

## Troubleshooting

| Issue                          | Fix                                                                |
| ------------------------------ | ------------------------------------------------------------------ |
| **Mic permission denied**      | Open `chrome://settings/content/microphone`, allow localhost       |
| **WebSocket fails to connect** | Ensure orchestrator is running on port 8000. Check CORS.           |
| **No state updates**           | Check browser console for WS errors. Verify event format.          |
| **LiveKit connection fails**   | Ensure `cd infra && docker compose up -d` ran. Check port 7880.    |
| **Whisper timeout**            | Check `OPENAI_API_KEY` in `.env`. Verify internet connectivity.    |
| **TTS not working**            | TTS requires a user gesture first. Click the page before starting. |
| **Port 8000 in use**           | Kill existing process: `lsof -ti:8000 \| xargs kill`               |
| **No voices for TTS**          | Some browsers need time to load voices. Refresh the page.          |
| **Docker Postgres fails**      | Check if port 5432 is free: `lsof -ti:5432`                        |

## Design Decisions

- **JSON Patch (RFC6902)** for all state mutations — robust UI updates, auditable
- **Rule-based NLU** by default — zero cost. LLM parser interface ready for swap
- **Browser Web Speech API** for TTS — free, no API key needed
- **In-memory sessions** with optional Postgres — works without DB for dev
- **Text input fallback** — test full flow without LiveKit/mic setup
