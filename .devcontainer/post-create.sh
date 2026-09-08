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

echo "==> Installing the headless browser's shared libraries"
# Lets Claude (and any future Playwright test) screenshot the viewer to check
# a UI change instead of asking you to look. Only the shared libraries belong
# here: the browser binary itself is a ~/.cache download, so it is installed
# in post-start.sh.
#
# Deliberately not `playwright install-deps`: that pulls ~80 packages —
# xvfb, LLVM, -dev headers — that only a headed browser needs, and it shells
# out to `apt-get update`, which fails here (see below).
#
# `|| true` because dl.yarnpkg.com, added to the image by the Node feature,
# is signed with a key yarn has since rotated, so `apt-get update` always
# exits 100 on NO_PUBKEY even though every Debian list refreshes fine. The
# install below is the step that actually has to succeed, and `set -e` still
# catches it if it doesn't.
sudo apt-get update || true
sudo apt-get install -y --no-install-recommends \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libcairo2 \
    libcups2 libdrm2 libgbm1 libnspr4 libnss3 libpango-1.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxkbcommon0 libxrandr2
