#!/usr/bin/env bash
# Runs inside the container, once, after it is created.
set -euo pipefail

cd "$(dirname "$0")/.."

# Docker creates volume mount points root-owned when the path doesn't exist in
# the image. Claude Code fails to log in if it can't write its config dir.
sudo chown "$(id -u):$(id -g)" .venv frontend/node_modules "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

echo "==> Creating the Python virtualenv"
make venv

echo "==> Installing frontend dependencies"
npm --prefix frontend install

echo "==> Installing Claude Code"
npm install -g @anthropic-ai/claude-code

# A browser OAuth round-trip can't reach the container's loopback listener, so
# the smoothest path is a long-lived token minted on the host with
# `claude setup-token`. See .devcontainer/README.md.
if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    echo "==> Claude Code will authenticate with CLAUDE_CODE_OAUTH_TOKEN"
else
    echo "==> CLAUDE_CODE_OAUTH_TOKEN is not set: sign in from the Claude tab,"
    echo "    or add a token to .devcontainer/devcontainer.env."
fi

# Let git push/pull over HTTPS use the scoped token from devcontainer.env.
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
