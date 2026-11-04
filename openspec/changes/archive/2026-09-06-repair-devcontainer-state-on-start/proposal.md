# Proposal

## Why

`post-create.sh` ran only when the container was created, but three things it
set up live shorter than the container: the `.venv/` Docker volume (removed by
`docker volume rm`/prune, or left empty by a failed post-create), and the
deliberately unpersisted `~/.gitconfig` and `~/.claude/settings.json`. Once any
went missing, only a rebuild brought it back: no interpreter, commits failing
with *Author identity unknown*, no GitHub HTTPS credentials, no Claude Code
settings.

## What Changes

- New `.devcontainer/post-start.sh`, wired to `postStartCommand`, runs on every
  start (including the first build, after post-create). It recreates the
  virtualenv when `.venv/` has no interpreter, rewrites Claude Code's settings,
  and sets the git identity and GitHub credential helper from
  `devcontainer.env`.
- `post-create.sh` keeps only container-filesystem work: the frontend
  dependency install and the global Claude Code install.
- `.devcontainer/README.md` describes the create/start split and notes that a
  change to `devcontainer.env` still needs a rebuild.

## Capabilities

### New Capabilities

- `dev-container`: what the dev container guarantees on create and on every
  start — a working virtualenv, Claude Code settings, git identity and GitHub
  credentials, restored by a restart rather than a rebuild.

### Modified Capabilities

None.

## Impact

`.devcontainer/post-start.sh` (new), `.devcontainer/post-create.sh`,
`.devcontainer/devcontainer.json`, `.devcontainer/README.md`. No application
code changes. A failure in `post-start.sh` now blocks every start, not just
creation.
