# Design

## Context

See proposal.md for the motivation. The threats are two kinds of code
running as the developer: a malicious dependency's install script, and a
coding agent with prompts disabled that misbehaves or follows injected
instructions. On the host, either can read any file the user can, and can
leave something behind that runs again later.

## Goals / Non-Goals

**Goals:**
- Limit what these threats can reach on the host to the workspace and the
  secrets the container needs.
- Limit the damage if a secret leaks: one repository, revocable tokens.
- Make "Rebuild Container" a real fix. Nothing a compromise writes outside
  the workspace survives it.

**Non-Goals:**
- Stopping a compromise from reading the container's own credentials during a
  session. The tools need them, so anything running as the user can read
  them.
- Network egress filtering.
- Protecting the workspace itself. It is bind-mounted read-write, because the
  container exists to edit it.

## Decisions

**Mount only the workspace.** No home directory, SSH agent, Docker socket or
host credential store is passed in. Whatever the container can read from the
host, it can read through the checkout.

**Secrets through a gitignored env file, not the image or the repo.**
`runArgs --env-file` reads `.devcontainer/devcontainer.env` at creation.
`initialize.sh` creates an empty copy from the example on the host, so a
missing file can't fail the start. Rejected: committing credentials to
`devcontainer.json`, or putting them in the image, where they would follow
every clone or image push.

**A fine-grained PAT scoped to this repository**, wired into git through
`gh auth git-credential`. A stolen token can push to Ceopardy and nothing
else. Rejected: forwarding the host's `gh` login or SSH agent, which carry
the developer's full account.

**Don't persist `~/.claude`.** `settings.json` hooks and `apiKeyHelper` are
shell commands Claude Code runs automatically, so they are where a
postinstall script would plant itself. A volume on `~/.claude` would let that
survive "Rebuild Container", which is the obvious remediation. Claude signs in
from `CLAUDE_CODE_OAUTH_TOKEN` in the env file, so dropping the directory
costs nothing. Rejected: a persisted `~/.claude` volume (convenient, but it
outlives the fix), and an interactive login (lost on every rebuild).

**Skip permission prompts only inside the container**, through
`~/.claude/settings.json` that the setup writes. A committed
`.claude/settings.json` in the workspace would follow the repo onto the host,
where there is no boundary.

**Keep dependency trees in container-only volumes.** `.venv/` and
`frontend/node_modules/` are Docker volumes mounted over the workspace. This
also keeps the host's absolute paths and native builds out of the container.

**Git identity in `--global`, not `.git/config`.** `.git/` belongs to the
host, so the setup never writes there. `~/.gitconfig` is not persisted
either, so identity comes from `GIT_USER_NAME` / `GIT_USER_EMAIL` in the env
file.

## Risks / Trade-offs

- [Tokens live in environment variables, which credential harvesters check
  first] → keep the GitHub token scoped to this repository, treat
  `devcontainer.env` as a secret, rotate both tokens on suspicion. Documented
  in `.devcontainer/README.md`.
- [Tokens are long-lived and identical across rebuilds, so a rebuild does not
  revoke a stolen one] → revocation happens on GitHub and in the Claude
  account settings, not in the container.
- [The workspace, `.git/` included, is writable from the container and later
  used on the host] → a compromise could plant a git hook, a Makefile target
  or a package script that the host runs. Nothing in the container prevents
  this. Run git, `make` and `npm` for this checkout from inside the container
  only, and review changes before running them on the host.
- [Settings were written only at creation, so a compromise could still edit
  them in place until the next rebuild] → closed by
  `2026-09-06-repair-devcontainer-state-on-start`, which rewrites them on
  every start.

## Divergences from what later shipped

- The setup that writes Claude's settings and the git identity moved from
  `post-create.sh` to `post-start.sh` in #44.
- The volume names gained `${devcontainerId}` in #49, so each checkout gets
  its own volumes.
