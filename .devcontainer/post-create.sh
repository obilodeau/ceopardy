#!/usr/bin/env bash
# Runs inside the container, once, after it is created.
set -euo pipefail

cd "$(dirname "$0")/.."

# Docker creates volume mount points root-owned when the path doesn't exist in
# the image.
sudo chown "$(id -u):$(id -g)" frontend/node_modules

# The virtualenv is not created here: post-start.sh owns it, so that a .venv
# volume that goes missing later is rebuilt on the next start rather than only
# on the next container creation.

echo "==> Installing frontend dependencies"
npm --prefix frontend install

echo "==> Installing Claude Code"
npm install -g @anthropic-ai/claude-code

# The container is the isolation boundary (disposable, no host filesystem
# access outside the bind-mounted workspace), so skip permission prompts
# here. This only ever affects the container: ~/.claude is not persisted
# (see devcontainer.json), so this file is rewritten fresh by this script
# on every container creation and never survives a rebuild on its own.
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

# ~/.gitconfig isn't persisted either, so identity comes from the env file on
# every rebuild. --global rather than the repo's config: .git/ is bind-mounted
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
