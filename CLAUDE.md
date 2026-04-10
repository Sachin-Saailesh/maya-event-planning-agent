# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all deps
make install

# Run all services concurrently (3 separate terminals in practice)
make dev-orchestrator   # FastAPI on :8000
make dev-worker         # LiveKit agent worker
make dev-web            # Vite dev server on :5173

# Docker (LiveKit SFU + optional Postgres)
make docker-up
make docker-down

# Tests
make test                                              # all
python -m pytest packages/schema/tests/ -v            # schema only
python -m pytest services/orchestrator/tests/ -v      # orchestrator only
python -m pytest services/orchestrator/tests/test_conversation.py -v  # single file

# Lint
make lint
cd services/orchestrator && python3 -m ruff check .
cd apps/web && npm run lint
```

The frontend proxies `/session`, `/tts`, `/generate`, and `/ws` to `http://127.0.0.1:8000` (see `apps/web/vite.config.js`), so the orchestrator must be running for any frontend functionality.

## Architecture

### System Overview

Audio flows from **Browser mic → LiveKit SFU → Agent Worker** (VAD + Whisper STT) **→ Orchestrator** (NLU + slot-filling) **→ Browser** (WebSocket for prompts + state patches, `/tts` endpoint for TTS audio).

Two separate WebSocket connections exist:
1. **Browser ↔ Orchestrator** (`/ws/session/{id}`) — events for transcripts, prompts, state patches, barge-in
2. **Agent Worker ↔ Orchestrator** — same WS, relays STT final transcripts

Text mode works without LiveKit: the browser text input sends `client.transcript.final` directly to the orchestrator.

### Frontend (`apps/web/src/`)

**Stage machine in `App.jsx`:** `startup → startup_picker → landing → session → review → hall_selection → generating → visualization → export`

- `startup` — auth resolving (loading spinner)
- `startup_picker` — shown when prior sessions exist; user picks continue or new
- `generating` — Nano Banana image generation in progress (`GenerationScreen`)
- Stage transitions to `hall_selection` triggered by voice (`server.review.proceed` WS event) or button
- Stage transitions back to `session` triggered by voice (`server.review.modify_slot` WS event) or button

Key hooks:
- `useWebSocket` — all WS events; returns `state`, `transcript`, `latestPrompt`, `speechInterrupted`, `slotsFilledEvent`, `reviewProceedEvent`, `reviewModifySlotEvent`
- `useAuth` — auth state (guest / authenticated), sign-in, sign-out
- `useSavedSessions` — localStorage session persistence with auto-naming and rename
- `useMicrophone` — browser permission state
- `useTTS` — fetches audio from `/tts?text=...` and plays via `HTMLAudioElement` (Web Speech API is silenced by WebRTC on macOS; this is intentional)
- `useLiveKit` — manages LiveKit room connection for mic audio

Key services (`apps/web/src/services/`):
- `auth.js` — email + Google sign-in, persisted user token. Configure `VITE_AUTH_BASE_URL` in `.env`
- `sessionStorage.js` — localStorage session CRUD, guest-to-user migration
- `sessionNaming.js` — generates elegant session names from decor state
- `imageGeneration.js` — calls `/generate` backend proxy for Nano Banana; polls async jobs

`slotConfig.js` is the single source of truth for slot ordering, option labels/colors, and hall config on the frontend.

### Orchestrator (`services/orchestrator/`)

Request lifecycle for a voice turn:
1. `ws_handler.py` receives `client.transcript.final`
2. Passes through: hallucination filter → guardrails → polite-phrase / repeat-request checks
3. `nlu.py` `RuleBasedParser.parse()` — context-first: checks `SLOT_SYNONYMS[current_slot]` before generic extraction
4. `conversation.py` `process_user_input()` — applies values to state, advances slot
5. `session_manager.py` `apply_state_patch()` — RFC6902 JSON Patch applied to in-memory state
6. Broadcasts `server.state.patch` + `server.prompt` to all connected clients
7. If `next_slot` is `None` (all slots filled), also broadcasts `server.slots.filled`

**Review-stage dialog (`ws_handler.py`):** When `current_slot` is `None`, utterances go through `parse_review_intent()` in `conversation.py` instead of generic NLU:
- `"proceed"` intent → broadcasts `server.review.proceed` → frontend moves to hall_selection
- `"modify_slot"` intent → clears that slot via RFC6902 replace patch, resets `current_slot`, broadcasts `server.review.modify_slot` → frontend returns to session
- `"modify_generic"` intent → Maya asks which category to change
- `"other"` → re-surfaces the completion/review prompt (no longer repeats blindly)

**Image generation:** `POST /generate` in `main.py` builds a prompt from state + hall and proxies to Nano Banana. Requires `NANO_BANANA_API_KEY` and `NANO_BANANA_BASE_URL` env vars. `GET /generate/{job_id}` polls async jobs.

**NLU fallback:** `NLU_BACKEND=llm` env var swaps `RuleBasedParser` for `LLMParser` (GPT-4o-mini). Rule-based is the default.

**State persistence:** In-memory by default. Postgres via `DATABASE_URL` env var, Redis cache via `REDIS_URL` — both degrade gracefully if not configured.

### Shared Schema (`packages/schema/`)

`maya_schema/state.py` — canonical state shape, `SLOT_PRIORITY`, `validate_backdrop_types()`, `get_next_empty_slot()`.

`maya_schema/patches.py` — RFC6902 patch helpers (`create_add_patch`, `create_replace_patch`, etc.).

`maya_schema/events.py` — event type constants and envelope factory.

The frontend mirrors `SLOT_PRIORITY` in `slotConfig.js`. If you add/reorder slots, update **both** files.

### Agent Worker (`services/agent_worker/`)

Runs as a LiveKit agent. `VoiceActivityDetector` (energy-based) segments audio; `stt.py` calls the Whisper API. Barge-in is detected when the orchestrator broadcasts `client.speech.started` — the worker publishes this after VAD detects speech while Maya's TTS is playing.

## Key Constraints

- **TTS uses `/tts` HTTP endpoint** (not Web Speech API) because WebRTC mic locks the Web Speech API on macOS. `useTTS` pre-fetches all sentence audio blobs in parallel before playback starts.
- **Backdrop types** are an enum: `"flowers"`, `"pattern"`, `"flower_lights"`. The NLU normalises synonyms ("lights" → "flower_lights") in `SLOT_SYNONYMS` in `nlu.py` and again in `validate_backdrop_types()` in `state.py`.
- **`AFFIRMATIVE_SLOTS`** in both `nlu.py` and `conversation.py` must match — these are the slots where a bare "yes/sure" confirm is treated as `values=["yes"]`.
- The Vite proxy config is the only place routing is configured; no nginx in dev.
- **Auth is optional** — `VITE_AUTH_BASE_URL` left blank disables sign-in UI gracefully; guest mode always works.
- **Nano Banana keys are server-side only** — never expose in frontend; all calls go through the `/generate` orchestrator proxy.
- **Session persistence is localStorage-first** — schema version is checked on read; corrupt/missing sessions are silently skipped.
- **Guest → user migration** runs automatically on sign-in via `migrateAllGuestSessions(userId)` in `sessionStorage.js`.
