# Repair the dev container's per-start state on start, not only on create

Implementation plan for [obilodeau/ceopardy#44](https://github.com/obilodeau/ceopardy/pull/44).

## Problem

`.devcontainer/post-create.sh` runs from `postCreateCommand`, which fires only
when the container is *created*. Three of the things it sets up have a lifetime
shorter than the container's, so once any of them goes missing, nothing brings
it back short of a full rebuild:

- **`.venv/`** is a Docker named volume. It outlives rebuilds (that is the
  point), but it disappears on `docker volume rm ceopardy-venv` or a
  `docker volume prune`, and it is left *empty* when `post-create.sh` fails
  partway through (a failed `npm install`, a network blip). The container then
  comes up with an empty `.venv/`: no interpreter, `make test` / `lint` / `run`
  all fail, and the VS Code Python interpreter path points at a file that is
  not there.
- **`~/.gitconfig`** is deliberately not persisted, so a container that starts
  without re-running post-create has no git identity — every commit fails with
  *Author identity unknown* — and no `https://github.com` credential helper, so
  push and pull over HTTPS stop working.
- **`~/.claude/settings.json`** is not persisted either, so Claude Code comes
  up without the container's settings.

## Approach

Split the setup **by lifetime**, not by when it is convenient to run.

- `post-create.sh` keeps only what lives in the container's own filesystem and
  lasts exactly as long as it does: the frontend dependency install and the
  global Claude Code install.
- A new `post-start.sh`, wired to `postStartCommand`, takes everything else. It
  runs on every start — and still on the first build, since `postStartCommand`
  runs after `postCreateCommand`.

Losing any of the per-start state then costs a restart rather than a rebuild.
Every step in `post-start.sh` must be idempotent and quiet when there is
nothing to do.

## Changes

### 1. `.devcontainer/post-start.sh` (new, executable, ~90 lines)

`#!/usr/bin/env bash`, `set -euo pipefail`, `cd "$(dirname "$0")/.."`. A header
comment states why each item cannot be a create-time side effect. Sections:

**Python virtualenv**
- If `.venv` exists but is not writable, `sudo chown "$(id -u):$(id -g)" .venv`
  — Docker creates volume mount points root-owned when the path does not exist
  in the image, so a fresh volume must be taken over before writing into it.
- If `.venv/bin/python` is not executable, print `==> No virtualenv in .venv:
  creating it` and run `make venv`. Testing `bin/python` rather than the
  directory is what distinguishes "empty fresh volume" from "working venv"; on
  a normal start this is a silent no-op.

**Claude Code**
- `mkdir -p ~/.claude` and write `~/.claude/settings.json` unconditionally with
  `permissions.defaultMode = "bypassPermissions"`. Rewriting on every start is
  deliberate: the container is the isolation boundary, and a restart is now
  enough to undo anything that edited the file in place.
- Report whether `CLAUDE_CODE_OAUTH_TOKEN` is set, reusing the existing
  guidance text for the unset case.

**git**
- When `GIT_USER_NAME` and `GIT_USER_EMAIL` are both set, `git config --global`
  the identity (`--global`, not the repo's config: `.git/` is bind-mounted from
  the host). Otherwise print the existing warning.
- When `GITHUB_TOKEN` is set, set
  `credential."https://github.com".helper` to `!gh auth git-credential` and run
  `gh auth status || true`. Otherwise print the existing skip message. Note in
  a comment that the env file is read by `docker run`, so a *changed* token
  still needs a rebuild to reach the container.

All of the Claude Code and git blocks move over verbatim from `post-create.sh`;
only the comments change ("on every rebuild" → "on every start").

### 2. `.devcontainer/post-create.sh` (−53, +6)

- Drop the `make venv` step and narrow the `chown` to `frontend/node_modules`
  only (`.venv` is now post-start's problem).
- Delete the `~/.claude/settings.json` block, the `CLAUDE_CODE_OAUTH_TOKEN`
  check, the git identity block, and the GitHub credential-helper block.
- Leaves: chown `frontend/node_modules`, `npm --prefix frontend install`,
  `npm install -g @anthropic-ai/claude-code`.
- Extend the header comment to say only container-filesystem work belongs here
  and to point at `post-start.sh` for the rest.

### 3. `.devcontainer/devcontainer.json` (+5)

Add, right after `postCreateCommand`, with a comment explaining that it runs on
every start and re-establishes the `.venv/` volume plus the unpersisted
`~/.claude` and `~/.gitconfig`:

```jsonc
"postStartCommand": "bash .devcontainer/post-start.sh",
```

### 4. `.devcontainer/README.md` (+17, −7)

- In the `GIT_USER_NAME`/`GIT_USER_EMAIL` step: "post-create rewrites the
  identity on every rebuild" → "post-start rewrites the identity on every
  start".
- Rewrite the "first build" paragraph: `post-create.sh` installs the frontend
  dependencies and Claude Code; `post-start.sh` then runs, on that first build
  and on every later start, creating the virtualenv when `.venv/` is empty,
  writing Claude Code's settings, setting the git identity, and pointing git at
  the token — with one sentence on *why* none of that is create-time work.
- Add to the token paragraph: `devcontainer.env` is read by Docker when it
  *creates* the container, so a restart is not enough to pick up a change in
  there — that genuinely still needs a rebuild.

## Commit sequence

Two commits, matching the PR:

1. **Recreate the dev container venv on start, not only on create** — the venv
   move: new `post-start.sh` with just the venv section, `postStartCommand` in
   `devcontainer.json`, venv bits removed from `post-create.sh`.
2. **Move the git and Claude Code setup to post-start.sh too** — the remaining
   three blocks move across, plus the `.devcontainer/README.md` update.

## Testing

Run `post-start.sh` against each state the `.venv` mount can be in:

| `.venv` state | expected |
| --- | --- |
| missing entirely | creates |
| populated | silent no-op |
| empty (fresh volume) | creates |
| empty and root-owned | chowns, then creates |
| populated and root-owned | chowns, no rebuild |

Then end-to-end against a scratch `HOME`:

- a fresh container with everything configured — venv built, `settings.json`
  written, identity and credential helper set, `gh auth status` green;
- a restart over that same state — idempotent: venv not rebuilt, no duplicated
  git config;
- `settings.json` overwritten with a malicious `PreToolUse` hook — the next
  start reverts it;
- none of `GIT_USER_NAME` / `GIT_USER_EMAIL` / `GITHUB_TOKEN` /
  `CLAUDE_CODE_OAUTH_TOKEN` set — prints the existing guidance for each and
  still exits 0.

Finally, `make ci` per `AGENTS.md` (no Python or frontend code changes here, so
this is just a regression check).

## Risks and notes

- `set -euo pipefail` plus `postStartCommand` means a failure in this script
  now blocks *every* start, not just creation. Each external call is therefore
  either guarded (`gh auth status || true`) or genuinely required (`make venv`).
- `make venv` on a start where the volume was pruned adds the full pip install
  to that start's time. Acceptable: the alternative is a broken container.
- The `chown` is guarded by a writability test so a normal start does not
  invoke `sudo` at all.
- `postStartCommand` also runs on the first build, right after
  `postCreateCommand` — so the split introduces no gap on a fresh container.
