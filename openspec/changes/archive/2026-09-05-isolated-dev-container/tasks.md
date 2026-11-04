# Tasks

## 1. Container and secrets

- [x] 1.1 Add `devcontainer.json` (Python 3.11 image, Node 20 and GitHub CLI features, workspace-only mounts) and verify "Rebuild Container" completes
- [x] 1.2 Read secrets with `--env-file .devcontainer/devcontainer.env`, gitignore the file, and add `initialize.sh` to create it from `devcontainer.env.example`; verify a checkout without the file still starts
- [x] 1.3 Wire git to the repo-scoped PAT through `gh auth git-credential`; verify `gh auth status` and an HTTPS `git push`

## 2. Agent and git config

- [x] 2.1 Leave `~/.claude` unpersisted and sign Claude Code in from `CLAUDE_CODE_OAUTH_TOKEN`; verify it is authenticated after a rebuild
- [x] 2.2 Write `bypassPermissions` to the container's `~/.claude/settings.json`, not to a committed `.claude/settings.json`; verify Claude Code does not prompt in the container
- [x] 2.3 Set the git identity from `GIT_USER_NAME` / `GIT_USER_EMAIL` with `--global`; verify a commit from the container is attributed correctly and `.git/config` is unchanged

## 3. Dependencies and docs

- [x] 3.1 Mount `.venv/` and `frontend/node_modules/` as Docker volumes; verify `make venv`, pytest, and the Flask and Vite servers come up
- [x] 3.2 Document the token scopes, the unpersisted `~/.claude`, and the env-var trade-off in `.devcontainer/README.md`, and list every `devcontainer.env` variable in the top-level `README.md`
