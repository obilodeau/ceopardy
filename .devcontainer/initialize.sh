#!/usr/bin/env bash
# Runs on the *host* before the container is created.
#
# docker refuses to start when --env-file points at a missing file, so make
# sure an (empty) devcontainer.env always exists. The real token is filled in
# by the user; see .devcontainer/README.md.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f devcontainer.env ]; then
    cp devcontainer.env.example devcontainer.env
    echo "Created .devcontainer/devcontainer.env — add your GitHub token there."
fi
