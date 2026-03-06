.PHONY: dev dev-orchestrator dev-worker dev-web lint test docker-up docker-down

# ─── Local Development ───────────────────────────────────────────

dev: dev-orchestrator dev-worker dev-web

dev-orchestrator:
	cd services/orchestrator && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

dev-worker:
	cd services/agent_worker && python -m worker

dev-web:
	cd apps/web && npm run dev

# ─── Docker ──────────────────────────────────────────────────────

docker-up:
	cd infra && docker compose up -d

docker-down:
	cd infra && docker compose down

# ─── Quality ─────────────────────────────────────────────────────

lint:
	cd services/orchestrator && python -m ruff check .
	cd services/agent_worker && python -m ruff check .
	cd apps/web && npm run lint

test:
	python -m pytest packages/schema/tests/ -v
	python -m pytest services/orchestrator/tests/ -v

# ─── Setup ───────────────────────────────────────────────────────

install:
	pip install -e packages/schema
	pip install -r services/orchestrator/requirements.txt
	pip install -r services/agent_worker/requirements.txt
	cd apps/web && npm install

# ─── Export ──────────────────────────────────────────────────────

export-brief:
	@echo "Use the web UI or call: POST http://localhost:8000/session/{id}/export"
