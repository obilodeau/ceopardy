# Dev container

Opens Ceopardy in a container with everything the dev workflow needs:
Python 3.11, Node 20, the GitHub CLI, and Claude Code.

## First run

1. Create the GitHub token (see below) and put it in
   `.devcontainer/devcontainer.env`:

       GITHUB_TOKEN=github_pat_...

   That file is gitignored; `.devcontainer/devcontainer.env.example` is the
   template. It is read verbatim by Docker, so no quotes and no spaces
   around `=`.

2. In VS Code: **Dev Containers: Reopen in Container**.

The first build runs `.devcontainer/post-create.sh`, which creates the
virtualenv (`make venv`), installs the frontend dependencies, installs
Claude Code, and points git at the token for GitHub HTTPS.

If you open the container before creating the token, add it to
`devcontainer.env` and run **Dev Containers: Rebuild Container**.

## The GitHub token

Use a **fine-grained personal access token** scoped to this repository only:
<https://github.com/settings/personal-access-tokens/new>

- **Resource owner:** your account
- **Repository access:** *Only select repositories* → `obilodeau/ceopardy`
- **Expiration:** whatever you're comfortable re-issuing (90 days is a
  reasonable default)

Repository permissions:

| Permission     | Access         | Why                                    |
| -------------- | -------------- | -------------------------------------- |
| Metadata       | Read           | mandatory, granted automatically       |
| Contents       | Read and write | clone, fetch, push branches            |
| Pull requests  | Read and write | `gh pr create`, review comments        |
| Issues         | Read and write | `gh issue` (optional)                  |
| Workflows      | Read and write | only if you edit `.github/workflows/`  |
| Actions        | Read           | `gh run list/view` for CI (optional)   |

Grant nothing else — no account permissions are needed.

The token stays on the host in `devcontainer.env` and is passed to the
container as an environment variable. It is never written into the image or
into the repository. To revoke it, delete it at
<https://github.com/settings/personal-access-tokens>.

## What runs where

- Flask back-end on port 5000, Vite dev server on port 5173 — both
  auto-forwarded to the host. `make run` starts them together.
- `.venv/` and `frontend/node_modules/` live in Docker volumes rather than
  the bind-mounted workspace, so the container's dependencies don't collide
  with the ones on your host.
- Claude Code's login persists in a volume across rebuilds; run `claude` in
  the container terminal.
