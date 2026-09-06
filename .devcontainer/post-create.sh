#!/usr/bin/env bash
# Runs inside the container, once, after it is created.
#
# Only what genuinely belongs to the container's own filesystem lives here.
# Anything on a volume or in the (unpersisted) home directory can go missing
# without the container being recreated, so it belongs in post-start.sh —
# which runs after this script on a first build, and on every start after.
set -euo pipefail

cd "$(dirname "$0")/.."

# Docker creates volume mount points root-owned when the path doesn't exist in
# the image.
sudo chown "$(id -u):$(id -g)" frontend/node_modules

echo "==> Installing frontend dependencies"
npm --prefix frontend install

echo "==> Installing Claude Code"
npm install -g @anthropic-ai/claude-code
