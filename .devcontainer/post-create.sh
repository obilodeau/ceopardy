#!/usr/bin/env bash
# Runs inside the container, once, after it is created.
set -euo pipefail

cd "$(dirname "$0")/.."

# The volume mounts for .venv and frontend/node_modules are created root-owned.
sudo chown "$(id -u):$(id -g)" .venv frontend/node_modules

echo "==> Creating the Python virtualenv"
make venv

echo "==> Installing frontend dependencies"
npm --prefix frontend install

echo "==> Installing Claude Code"
npm install -g @anthropic-ai/claude-code

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
