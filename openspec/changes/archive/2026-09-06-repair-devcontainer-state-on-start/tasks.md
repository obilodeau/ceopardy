# Tasks

## 1. Recreate the virtualenv on start

- [x] 1.1 Add `.devcontainer/post-start.sh` with the virtualenv section: guarded `chown` of a non-writable `.venv`, then `make venv` when `.venv/bin/python` is not executable; verify each `.venv` state (missing, empty, empty root-owned, populated, populated root-owned) gives the expected result
- [x] 1.2 Wire it to `postStartCommand` in `.devcontainer/devcontainer.json`; verify it runs after `postCreateCommand` on a first build and alone on a restart
- [x] 1.3 Remove `make venv` from `post-create.sh` and narrow its `chown` to `frontend/node_modules`; verify a fresh build still ends with a working venv
- [x] 1.4 Update `.devcontainer/README.md` to say the venv is created at start; verify the first-run steps read correctly

## 2. Move git and Claude Code setup to start

- [x] 2.1 Move the `~/.claude/settings.json` write and the `CLAUDE_CODE_OAUTH_TOKEN` check into `post-start.sh`; verify a restart reverts a settings file carrying a malicious `PreToolUse` hook
- [x] 2.2 Move the git identity and GitHub credential-helper blocks into `post-start.sh`; verify identity, helper and `gh auth status` against a scratch `HOME`, and that a restart duplicates no git config
- [x] 2.3 Reduce `post-create.sh` to the frontend and Claude Code installs, with a header pointing at `post-start.sh`; verify with no env vars set that each guidance message prints and the start exits 0
- [x] 2.4 Update `devcontainer.json`'s `postStartCommand` comment and `.devcontainer/README.md` (identity rewritten on every start, the create/start split, `devcontainer.env` changes still need a rebuild); verify the README matches the scripts
- [x] 2.5 Run `make ci` as a regression check and verify it passes
