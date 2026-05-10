# Put the project venv first on PATH so targets work the same whether or not
# the user has activated it (or has direnv loaded). `make venv` creates it.
export PATH := $(CURDIR)/.venv/bin:$(PATH)

.PHONY: ci lint format-check test install-dev run venv

# Run all CI checks — called by GitHub Actions.
ci: lint format-check frontend-lint test

# ── Python ──────────────────────────────────────────────────────────────────

lint:
	ruff check .

format-check:
	ruff format --check .

test:
	pytest

# ── Frontend (run manually when working on frontend/) ────────────────────────

frontend-lint:
	npm --prefix frontend run lint

# ── Dev setup ────────────────────────────────────────────────────────────────

venv:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

# ── Run dev servers (Flask + Vite) in one terminal ──────────────────────────

# Reinstalls when package.json is newer than the install marker.
frontend/node_modules/.package-lock.json: frontend/package.json
	npm install --prefix frontend
	@touch frontend/node_modules/.package-lock.json

run: frontend/node_modules/.package-lock.json
	@exec sh -c 'trap "kill 0" INT TERM; \
		python run.py & \
		npm run dev --prefix frontend & \
		wait'
