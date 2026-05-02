.PHONY: ci lint format-check test install-dev

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

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt
