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

The first build runs `.devcontainer/post-create.sh`, which installs the
frontend dependencies, Claude Code, and the headless browser's shared
libraries — the things that live in the container's own filesystem and last
exactly as long as it does.

Then `.devcontainer/post-start.sh` runs, on that first build and on every
later start. It creates the virtualenv with `make venv` when `.venv/` is
empty, writes Claude Code's settings, sets the git identity, points git at
the token for GitHub HTTPS, and downloads the headless browser. None of that
is create-time work: `.venv/` is a Docker volume with a lifetime of its own,
and `~/.claude` and
`~/.gitconfig` are deliberately not persisted at all, so a container can
come up missing any of them. Setting them at start means a *restart* repairs
that, rather than a rebuild.

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
from in here — Claude screenshots the viewer and checks its own work rather
than asking you to be the renderer. Ceopardy's whole product is a screen in
front of a crowd, and neither `vue-tsc` nor the Python tests can see it.

It arrives in three pieces, each placed by the same lifetime rule as
everything else here:

- **16 shared libraries**, in `post-create.sh` — image state, with exactly
  the container's own lifetime.
- **`chrome-headless-shell`, 266 MB**, in `post-start.sh` — a `~/.cache`
  download, and that is not persisted.
- **A pinned `playwright`**, in `frontend/package.json` — so the client and
  the browser build can't drift apart.

So a *restart* costs a second, and a *rebuild* re-downloads 266 MB. Making
that survive would mean a Docker volume over `~/.cache`, which is exactly
the kind of writable path that outlives the rebuild you'd reach for as
remediation — not worth it for a binary that re-downloads in a minute.

Two things worth knowing if you extend this:

- **Don't reach for `playwright install-deps`.** It pulls ~80 packages —
  xvfb, LLVM, `-dev` headers — that only a headed browser needs, and it
  shells out to `apt-get update`, which exits 100 in this image: the Node
  feature adds a `dl.yarnpkg.com` source signed with a key yarn has since
  rotated. Every Debian list still refreshes, so `post-create.sh` tolerates
  that exit code and lets the install itself be the step that must succeed.
- **`--only-shell` means headless only.** No headed runs, no video capture.
  Drop the flag and you get full Chromium too, at 658 MB instead of 266 MB.

There are no browser tests yet: today this is tooling, not a regression net.
Adding a couple of smoke tests (the viewer renders the board, the host page
loads, the enable-sound overlay appears in online mode) and a target in
`make ci` is what would turn it into one. GitHub Actions installs its own
browsers, so CI is unaffected until then.

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
