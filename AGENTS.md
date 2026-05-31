# Agent guidelines

## Type hints

Add type hints to all new functions and methods.

## Before every commit

Run the full CI check suite:

```
make ci
```

This runs ruff lint, ruff format check, prettier (frontend), `vue-tsc`
(frontend type-check), and pytest. All must pass.

To auto-fix Python formatting and safe lint issues before checking:

```
make format
make ci
```

## Running tests

```
make test           # pytest under the project's venv
```

Tests live in `tests/` and cover pure utility functions that need no Flask
app context. Keep new tests free of Flask/database dependencies where
possible.

## Frontend (when working in `frontend/`)

The frontend is a Vite + Vue 3 SPA written in **TypeScript** (strict mode).
Single-file components use `<script setup lang="ts">`.

```
make frontend-lint        # prettier check over src/**/*.{ts,vue}
make frontend-type-check  # vue-tsc --noEmit
```

Both are part of `make ci`. Prettier is the formatter; there is no separate
ESLint config. State lives in a Pinia store at `src/stores/game.ts` —
prefer adding getters there over duplicating fallback expressions in
components.

## README

`README.md` has two top-level paths the project commits to:

- **Running Ceopardy (operators)** — pipx install of a release wheel, then
  `ceopardy init` + `ceopardy serve`.
- **Hacking on Ceopardy (developers)** — clone + `make venv` + `make run`.

When you change the install, run, or dev workflow, update the matching
section. When you change a command name, port, or default behavior the
README documents, update the README in the same change.
