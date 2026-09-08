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

# The Node feature adds a dl.yarnpkg.com source signed with a key yarn has
# since rotated, so every apt-get update fails on NO_PUBKEY. Nothing here
# uses yarn, so drop the source rather than work around the error.
sudo rm -f /etc/apt/sources.list.d/yarn.list

# Lets Claude screenshot the viewer to check a UI change. Libraries only;
# post-start.sh downloads the browser. Not `playwright install-deps`, which
# adds ~80 packages a headless run never uses.
echo "==> Installing the headless browser's shared libraries"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libcairo2 \
    libcups2 libdrm2 libgbm1 libnspr4 libnss3 libpango-1.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxkbcommon0 libxrandr2
