.PHONY: dev dev-orchestrator dev-worker dev-web lint test docker-up docker-down

# ─── Local Development ───────────────────────────────────────────

dev: dev-orchestrator dev-worker dev-web

dev-orchestrator:
	cd services/orchestrator && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

dev-worker:
	cd services/agent_worker && python3 worker.py dev

dev-web:
	cd apps/web && npm run dev

# ─── Docker ──────────────────────────────────────────────────────

docker-up:
	cd infra && docker compose up -d

docker-down:
	cd infra && docker compose down

# ─── Quality ─────────────────────────────────────────────────────

lint:
	cd services/orchestrator && python3 -m ruff check .
	cd services/agent_worker && python3 -m ruff check .
	cd apps/web && npm run lint

test:
	python3 -m pytest packages/schema/tests/ -v
	python3 -m pytest services/orchestrator/tests/ -v

# ─── Setup ───────────────────────────────────────────────────────

install:
	pip3 install -e packages/schema
	pip3 install -r services/orchestrator/requirements.txt
	pip3 install -r services/agent_worker/requirements.txt
	cd apps/web && npm install

# ─── Export ──────────────────────────────────────────────────────

export-brief:
	@echo "Use the web UI or call: POST http://localhost:8000/session/{id}/export"
