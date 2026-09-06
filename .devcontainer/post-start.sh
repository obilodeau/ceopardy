#!/usr/bin/env bash
# Runs inside the container on every start, including the ones that don't
# re-run post-create.sh (starting a stopped container, "Reopen in Container"
# on an existing one).
#
# .venv/ is a Docker volume with a lifetime of its own: it survives container
# rebuilds, but it also disappears on `docker volume rm` / `docker volume
# prune`, and it is left empty when post-create.sh fails partway through.
# Any of those leaves you attached to a container with no interpreter and
# nothing scheduled to create one. So make the venv a start-time invariant
# rather than a create-time side effect.
set -euo pipefail

cd "$(dirname "$0")/.."

# Docker creates volume mount points root-owned when the path doesn't exist in
# the image, so take ownership before writing into a freshly created volume.
# When there is no .venv at all (no volume mounted), `make venv` makes it.
if [ -d .venv ] && [ ! -w .venv ]; then
    sudo chown "$(id -u):$(id -g)" .venv
fi

if [ -x .venv/bin/python ]; then
    exit 0
fi

echo "==> No virtualenv in .venv: creating it"
make venv
