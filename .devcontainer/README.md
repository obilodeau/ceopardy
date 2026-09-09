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

2. Add the name and address you want your commits authored by, to the same
   file:

       GIT_USER_NAME=Your Name
       GIT_USER_EMAIL=you@example.com

   Neither is secret; they're here because the container's `~/.gitconfig` is
   no more persisted than `~/.claude` is, so post-start rewrites the
   identity on every start. Without them, committing from inside the
   container fails with *Author identity unknown*.

3. In VS Code: **Dev Containers: Reopen in Container**.

The first build runs `.devcontainer/post-create.sh`. Then
`.devcontainer/post-start.sh` runs, on that first build and on every later
start.

The split between them is by lifetime. Whatever belongs to the container's
own filesystem is set up at create time; whatever can go missing without the
container being recreated — the `.venv/` volume, the unpersisted `~/.claude`
and `~/.gitconfig`, the browser under `~/.cache` — is set up at start, so
losing any of it costs a restart rather than a rebuild. The scripts say what
each one does.

If you open the container before creating the token, add it to
`devcontainer.env` and run **Dev Containers: Rebuild Container**. Docker
reads that file when it *creates* the container, so a restart is not enough
to pick up anything you change in there.

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

## Claude Code

Authenticate with a long-lived token minted on the **host**:

    claude setup-token

and put it in `.devcontainer/devcontainer.env`:

    CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat...

Revoke it from your Claude account settings if it ever leaks.

You *can* instead sign in from the Claude tab, but that login is lost on
every rebuild, and the browser round-trip ends at a loopback port inside the
container that the host browser can't always reach.

### Why ~/.claude is not persisted

Nothing under `/home/vscode/.claude` survives a rebuild, on purpose.

`npm install` runs package postinstall scripts as `vscode`, which is the
foothold supply-chain worms like Shai-Hulud use. Such a script can write
anywhere that user can — including Claude's own config, where
`settings.json` hooks and `apiKeyHelper` are *shell commands the agent runs
automatically*. Put that directory in a Docker volume and the injected
commands outlive "Rebuild Container", which is exactly the remediation
you'd reach for.

Keeping it ephemeral doesn't stop a compromise from reading your
credentials during the session — nothing in the container can, since the
tools need them at hand. What it buys is that a rebuild is genuinely clean.

Note the tradeoff this makes: both tokens are environment variables in the
container, and env is the first place credential harvesters look. They stay
long-lived and identical across rebuilds, so treat `devcontainer.env` as the
secret it is, keep the GitHub token scoped to this one repo, and rotate both
if you suspect anything.

## Headless browser

The container carries a headless Chromium so a UI change can be *looked at*
from in here, not just type-checked: Claude screenshots the viewer and
checks its own work rather than asking you to be the renderer.

- `post-create.sh` installs the shared libraries it links against.
- `post-start.sh` downloads `chrome-headless-shell`, 266 MB, into
  `~/.cache` — which no rebuild persists, so a rebuild re-downloads it.
- `playwright` is pinned in `frontend/package.json`.

Headless only: `--only-shell` skips the full Chromium build that headed runs
and video capture need. There are no browser tests yet, so this is tooling
rather than a regression net — GitHub Actions installs its own browsers, so
CI is unaffected either way.

## What runs where

- Flask back-end on port 5000, Vite dev server on port 5173 — both
  auto-forwarded to the host. `make run` starts them together.
- `.venv/` and `frontend/node_modules/` live in Docker volumes rather than
  the bind-mounted workspace, so the container's dependencies don't collide
  with the ones on your host.
- The headless browser lives in `~/.cache/ms-playwright`; `playwright` is a
  devDependency of the front-end. See above.
- Claude Code runs from the token in `devcontainer.env`; run `claude` in the
  container terminal, or use the Claude tab. Project-level settings that
  should be shared belong in the repo's `.claude/settings.json`, which is
  version-controlled and reviewable — not in a shared home directory.
