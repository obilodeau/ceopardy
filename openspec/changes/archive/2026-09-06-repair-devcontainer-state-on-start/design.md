# Design

## Context

See proposal.md for the problem. `.venv/` and `frontend/node_modules/` are
Docker volumes mounted over the bind-mounted workspace; `~/.claude` and
`~/.gitconfig` are kept out of any volume on purpose, so that a rebuild undoes
anything a malicious npm postinstall wrote there. `devcontainer.env` is passed
to `docker run`, so its values are fixed at container creation.

## Goals / Non-Goals

**Goals:**
- Losing any per-start state costs a restart, not a rebuild.
- A normal start does no work it does not need: no venv rebuild, no `sudo`.

**Non-Goals:**
- Picking up a changed `devcontainer.env` on restart. Docker reads it at
  creation; that still needs a rebuild.
- Persisting `~/.claude` or `~/.gitconfig`.

## Decisions

**Split setup by lifetime, not convenience.** `post-create.sh` keeps only what
lives in the container's own filesystem and lasts exactly as long as it does
(frontend install, global Claude Code install). Everything on a volume or in
the unpersisted home directory moves to `post-start.sh`. `postStartCommand`
also runs on the first build, right after `postCreateCommand`, so a fresh
container sees no gap. Rejected: keeping everything in post-create and
documenting "rebuild if broken" — that is the status quo the change fixes.

**Detect the venv by `.venv/bin/python`, not by the directory.** An empty
fresh volume and a missing directory both lack the interpreter; a working
venv has it. Testing the directory would treat an empty volume as healthy.
When missing, `make venv` builds it.

**Guard the `chown` with a writability test.** Docker creates a volume mount
point root-owned when the path does not exist in the image, so a fresh
`.venv` volume must be taken over before writing. Checking `-w` first keeps
`sudo` off the normal start path. The post-create `chown` narrows to
`frontend/node_modules`.

**Rewrite `~/.claude/settings.json` unconditionally.** It sets
`permissions.defaultMode` to `bypassPermissions` (the container is the
isolation boundary). Writing it on every start, rather than only when absent,
means a restart undoes any in-place edit, such as an injected hook. This
strengthens the reason `~/.claude` is kept ephemeral.

**Git config goes to `--global`, not the repo.** `.git/` is bind-mounted from
the host and the container should not write to it. The credential helper is
set explicitly to `!gh auth git-credential` for `https://github.com`, rather
than via `gh auth setup-git`, which wants a stored login; the helper serves
`GITHUB_TOKEN` from the environment.

**Missing env vars warn, never fail.** Unset `GIT_USER_NAME`/`GIT_USER_EMAIL`,
`GITHUB_TOKEN` or `CLAUDE_CODE_OAUTH_TOKEN` each print guidance and the script
continues. The Claude Code and git blocks moved from post-create verbatim
apart from comments ("every rebuild" → "every start").

## Risks / Trade-offs

- [`set -euo pipefail` under `postStartCommand` makes any failure block every
  start] → Each external call is either guarded (`gh auth status || true`) or
  genuinely required (`make venv`).
- [A start after the volume was pruned pays a full pip install] → Accepted;
  the alternative is a broken container.
- [Idempotence] → `git config --global` overwrites rather than appends, and
  the settings file is rewritten whole, so repeated starts do not accumulate
  state.

## Testing

Ran `post-start.sh` against each `.venv` state: missing (creates), populated
(silent no-op), empty fresh volume (creates), empty and root-owned (chowns,
then creates), populated and root-owned (chowns, no rebuild). Then end-to-end
against a scratch `HOME`: a fully configured fresh start; a restart over the
same state (venv not rebuilt, no duplicated git config); `settings.json`
replaced with a malicious `PreToolUse` hook (next start reverts it); and no
env vars set (guidance printed for each, exit 0). `make ci` as a regression
check.

## Divergences from the plan

- The first commit also updated `.devcontainer/README.md` for the venv move;
  the plan had all README changes in the second commit.
- Later changes, outside this one, built on `post-start.sh`: a headless
  browser download step, an OpenSpec global install in `post-create.sh`, a
  trimmed README that states the lifetime split instead of listing each
  script's steps, and per-checkout volume names
  (`ceopardy-venv-${devcontainerId}` rather than `ceopardy-venv`).
