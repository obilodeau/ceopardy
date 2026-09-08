#!/usr/bin/env bash
# Runs inside the container on every start, including the ones that don't
# re-run post-create.sh (starting a stopped container, "Reopen in Container"
# on an existing one).
#
# Everything set up here has a lifetime shorter than the container's, so none
# of it can be a create-time side effect:
#
#   - .venv/ is a Docker volume. It survives container rebuilds, but it also
#     disappears on `docker volume rm` / `docker volume prune`, and it is left
#     empty when post-create.sh fails partway through.
#   - ~/.claude and ~/.gitconfig are deliberately not persisted at all (see
#     devcontainer.json), so they are missing in any container that comes up
#     without post-create.sh having run.
#
# Doing this at start instead means losing any of it costs a restart rather
# than a rebuild. Every step below is idempotent.
set -euo pipefail

cd "$(dirname "$0")/.."

# ── Python virtualenv ────────────────────────────────────────────────────────

# Docker creates volume mount points root-owned when the path doesn't exist in
# the image, so take ownership before writing into a freshly created volume.
# When there is no .venv at all (no volume mounted), `make venv` makes it.
if [ -d .venv ] && [ ! -w .venv ]; then
    sudo chown "$(id -u):$(id -g)" .venv
fi

if [ ! -x .venv/bin/python ]; then
    echo "==> No virtualenv in .venv: creating it"
    make venv
fi

# ── Claude Code ──────────────────────────────────────────────────────────────

# The container is the isolation boundary (disposable, no host filesystem
# access outside the bind-mounted workspace), so skip permission prompts
# here. This only ever affects the container: ~/.claude is not persisted
# (see devcontainer.json), so this file is written fresh on every start and
# never survives a rebuild on its own. Rewriting it unconditionally is the
# point — a start is enough to undo anything that edited it in place.
mkdir -p ~/.claude
cat > ~/.claude/settings.json <<'EOF'
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  }
}
EOF

# ~/.claude is intentionally not persisted (see devcontainer.json), so the
# token from devcontainer.env is what keeps you logged in across rebuilds.
if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    echo "==> Claude Code will authenticate with CLAUDE_CODE_OAUTH_TOKEN"
else
    echo "==> CLAUDE_CODE_OAUTH_TOKEN is not set: run 'claude setup-token' on"
    echo "    the host and add it to .devcontainer/devcontainer.env, or sign"
    echo "    in from the Claude tab (that login is lost on rebuild)."
fi

# ── git ──────────────────────────────────────────────────────────────────────

# ~/.gitconfig isn't persisted either, so identity comes from the env file on
# every start. --global rather than the repo's config: .git/ is bind-mounted
# from the host, and the container has no business writing to it.
if [ -n "${GIT_USER_NAME:-}" ] && [ -n "${GIT_USER_EMAIL:-}" ]; then
    echo "==> Setting the git identity to $GIT_USER_NAME <$GIT_USER_EMAIL>"
    git config --global user.name "$GIT_USER_NAME"
    git config --global user.email "$GIT_USER_EMAIL"
else
    echo "==> GIT_USER_NAME/GIT_USER_EMAIL are not set: commits made in this"
    echo "    container will fail until you set them. Add them to"
    echo "    .devcontainer/devcontainer.env and rebuild."
fi

# Let git push/pull over HTTPS use the scoped token from devcontainer.env.
# The env file is read by `docker run`, so a changed token needs a rebuild to
# reach the container even though this runs on every start.
if [ -n "${GITHUB_TOKEN:-}" ]; then
    echo "==> Configuring git to authenticate to GitHub with GITHUB_TOKEN"
    # Set the helper explicitly rather than via `gh auth setup-git`, which
    # wants a stored login; `gh auth git-credential` serves the env token.
    git config --global credential."https://github.com".helper '!gh auth git-credential'
    gh auth status || true
else
    echo "==> GITHUB_TOKEN is not set: skipping GitHub auth setup."
    echo "    Add it to .devcontainer/devcontainer.env and rebuild the container."
fi

# ── Headless browser ─────────────────────────────────────────────────────────

# Playwright keeps its browsers in ~/.cache/ms-playwright, which is not
# persisted, so a rebuilt container comes up without one. The shared
# libraries it links against are image-level state and live in post-create.sh.
#
# --only-shell skips the full Chromium build, which is needed only to run
# headed: 266 MB rather than 658 MB. `playwright install` is idempotent, so
# this is a fast no-op once the browser is there.
if [ -x frontend/node_modules/.bin/playwright ]; then
    echo "==> Making sure the headless browser is installed"
    frontend/node_modules/.bin/playwright install --only-shell chromium
else
    echo "==> Skipping the headless browser: frontend/node_modules is empty."
    echo "    Run 'npm --prefix frontend install' and restart the container."
fi
