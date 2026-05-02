# Agent guidelines

## Type hints

Add type hints to all new functions and methods.

## Before every commit

Run the full CI check suite:

```
make ci
```

This runs ruff lint, ruff format check, and pytest. All three must pass.

To auto-fix formatting and safe lint issues before checking:

```
ruff format .
ruff check --fix .
make ci
```

## Running tests

```
pytest              # all tests
pytest tests/       # same, explicit path
```

Tests live in `tests/` and cover pure utility functions that need no Flask
app context. Keep new tests free of Flask/database dependencies where possible.

## Frontend (when working in `frontend/`)

```
make frontend-lint  # prettier check over src/**/*.{js,vue}
```

The frontend is a Vite + Vue 3 SPA. `npm --prefix frontend install` installs
its deps. Prettier is the formatter; no separate ESLint config exists yet.
