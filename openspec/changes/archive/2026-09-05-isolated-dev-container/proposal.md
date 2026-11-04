# Proposal

## Why

Coding agents run with their permission prompts turned off, and `npm install`
runs third-party postinstall scripts. Worms like Shai-Hulud use those scripts
to steal credentials and plant commands in an agent's config. Running either
directly on a developer's machine exposes everything that user can reach:
SSH keys, cloud credentials, browser profiles and broadly scoped tokens. The
project needs a place where agents and dependencies run against the checkout
and little else, and that can be thrown away and rebuilt clean after a
suspected compromise ([#43](https://github.com/obilodeau/ceopardy/pull/43)).

## What Changes

- Add a VS Code dev container (Python 3.11, Node 20, GitHub CLI, Claude
  Code). The only part of the host it mounts is the workspace.
- Secrets come from a gitignored `.devcontainer/devcontainer.env`, read by
  Docker at container creation. They are never baked into the image or
  committed. The GitHub token is a fine-grained PAT scoped to this one
  repository.
- `~/.claude` and `~/.gitconfig` are not persisted. Rebuilding the container
  removes anything a compromised script wrote there. Claude Code signs in
  from `CLAUDE_CODE_OAUTH_TOKEN`, so a clean rebuild is still logged in.
- Claude Code's permission prompts are skipped only inside the container, by
  a user-level settings file the container writes. There is no committed
  workspace setting that would also take effect on the host.
- `.venv/` and `frontend/node_modules/` are Docker volumes over the
  workspace, so what dependency installs write stays out of the host's
  checkout.
- Git identity comes from the same env file and is set globally in the
  container, never in the bind-mounted `.git/config`.

## Capabilities

### New Capabilities

- `dev-container`: the development container as a disposable trust boundary
  for coding agents and third-party dependency code, and what it guarantees
  on create and start.

### Modified Capabilities

None.

## Impact

- New `.devcontainer/` (`devcontainer.json`, `initialize.sh`,
  `post-create.sh`, `devcontainer.env.example`, `README.md`), a `.gitignore`
  entry for `devcontainer.env`, and a pointer in the top-level `README.md`.
- No change to the application or to the non-container dev workflow.
