# dev-container Specification

## Purpose
Defines the development container as a disposable trust boundary. Coding
agents and third-party dependency code run in it with access to the
workspace and a few narrowly scoped secrets. They cannot reach the rest of
the developer's machine, and a rebuild removes anything a compromise left
behind outside the workspace.

## Requirements

### Requirement: Host access is limited to the workspace
The dev container SHALL mount no host path other than the project workspace. It MUST NOT mount the developer's home directory, SSH agent, Docker socket or host credential stores.

#### Scenario: Agent looks for host secrets
- **WHEN** code inside the container tries to read the host user's `~/.ssh`, cloud credentials or browser profiles
- **THEN** those files are not present in the container

### Requirement: Secrets come only from a gitignored env file
Secrets SHALL reach the container only as environment variables read from `.devcontainer/devcontainer.env` when the container is created. That file MUST be gitignored, and secrets MUST NOT be written into the image or any committed file. A missing env file MUST NOT prevent the container from starting.

#### Scenario: Fresh clone
- **WHEN** the container is opened from a checkout without `devcontainer.env`
- **THEN** an empty one is created from the example on the host and the container starts

#### Scenario: Token kept out of git
- **WHEN** the developer adds a token to `devcontainer.env`
- **THEN** git status does not show the file as a change to commit

### Requirement: GitHub access is scoped to this repository
The documented GitHub credential SHALL be a fine-grained personal access token restricted to this repository, with no account permissions. Git operations over HTTPS SHALL use that token.

#### Scenario: Leaked token
- **WHEN** the token is stolen from the container's environment
- **THEN** it grants access to this repository only, and can be revoked from GitHub without affecting the developer's other credentials

### Requirement: A rebuild discards agent and git config
The dev container MUST NOT persist `~/.claude` or `~/.gitconfig` across a rebuild. Claude Code SHALL authenticate from `CLAUDE_CODE_OAUTH_TOKEN` so that a rebuilt container is still signed in.

#### Scenario: Injected hook
- **WHEN** a postinstall script adds a hook or `apiKeyHelper` to Claude Code's user settings and the developer rebuilds the container
- **THEN** the rebuilt container has no trace of it

#### Scenario: Signed in after rebuild
- **WHEN** the container is rebuilt with `CLAUDE_CODE_OAUTH_TOKEN` set
- **THEN** Claude Code is authenticated without an interactive login

### Requirement: Agent permission prompts are skipped only in the container
Claude Code's permission prompts SHALL be bypassed through user-level settings written inside the container. The bypass MUST NOT be committed to the repository, so it does not apply when the checkout is used on the host.

#### Scenario: Same checkout on the host
- **WHEN** the developer runs Claude Code on the host against the same checkout
- **THEN** permission prompts behave as the host's own settings define

### Requirement: Dependency installs stay out of the host checkout
The Python virtualenv and the frontend `node_modules` SHALL live in container-only volumes mounted over the workspace. Files written there by dependency installs MUST NOT appear in the host's checkout.

#### Scenario: Postinstall writes into node_modules
- **WHEN** an npm package's install script writes files into `frontend/node_modules` in the container
- **THEN** the host's `frontend/node_modules` is unchanged

### Requirement: The host's git config is never written
Container setup SHALL write git settings only to the container user's global config. It MUST NOT modify the repository's `.git/config`, which belongs to the host.

#### Scenario: Identity set
- **WHEN** container setup configures the git identity
- **THEN** the repository's `.git/config` is unchanged

### Requirement: Per-start setup runs on every start
The dev container SHALL run its per-start setup on every container start, including the first start after creation, where it MUST run after the create-time setup. Create-time setup SHALL be limited to work in the container's own filesystem: installing the frontend dependencies and Claude Code.

#### Scenario: First build
- **WHEN** the container is created and started for the first time
- **THEN** the create-time setup runs, followed by the per-start setup

#### Scenario: Restart of an existing container
- **WHEN** a stopped container is started again without being recreated
- **THEN** the per-start setup runs and the create-time setup does not

### Requirement: Virtualenv is restored on start
On start, the dev container SHALL ensure `.venv/` holds a working Python virtualenv with the project's runtime and dev dependencies, creating it when no interpreter is present. When `.venv/` exists but is not writable by the container user, it MUST take ownership of it first. A start where the virtualenv already works MUST NOT rebuild it.

#### Scenario: Volume missing or empty
- **WHEN** the container starts and `.venv/` is absent or contains no Python interpreter
- **THEN** a virtualenv is created in `.venv/` with the project dependencies installed

#### Scenario: Fresh root-owned volume
- **WHEN** the container starts and `.venv/` is an empty, root-owned mount point
- **THEN** ownership is taken by the container user and the virtualenv is then created

#### Scenario: Working virtualenv
- **WHEN** the container starts and `.venv/` already contains a working interpreter
- **THEN** the virtualenv is left untouched

### Requirement: Claude Code settings are reset on start
On every start, the dev container SHALL write Claude Code's user settings afresh with permission prompts bypassed, replacing any existing content. It SHALL report whether `CLAUDE_CODE_OAUTH_TOKEN` is set and, when it is not, explain how to provide it.

#### Scenario: Settings edited in place
- **WHEN** the user settings file was modified during a session, for example by an injected hook
- **THEN** the next start replaces it with the default settings

#### Scenario: OAuth token unset
- **WHEN** the container starts without `CLAUDE_CODE_OAUTH_TOKEN`
- **THEN** guidance on minting and adding the token is printed and the start continues

### Requirement: Git identity is set on start
On every start, when both `GIT_USER_NAME` and `GIT_USER_EMAIL` are set, the dev container SHALL configure them as the user's global git identity. It MUST NOT write to the repository's own git config. When either is unset, it SHALL print a warning and continue.

#### Scenario: Identity configured
- **WHEN** the container starts with `GIT_USER_NAME` and `GIT_USER_EMAIL` set
- **THEN** commits made in the container are authored with that name and email

#### Scenario: Identity missing
- **WHEN** the container starts with either variable unset
- **THEN** a warning that commits will fail is printed and the start succeeds

### Requirement: GitHub HTTPS credentials are configured on start
On every start, when `GITHUB_TOKEN` is set, the dev container SHALL configure git to authenticate to `https://github.com` with that token and report the GitHub CLI's auth status without failing on it. When the token is unset, it SHALL print a message saying GitHub auth was skipped and continue.

#### Scenario: Token present
- **WHEN** the container starts with `GITHUB_TOKEN` set
- **THEN** git push and pull over HTTPS to GitHub authenticate with the token

#### Scenario: Token absent
- **WHEN** the container starts without `GITHUB_TOKEN`
- **THEN** a skip message is printed and the start succeeds

### Requirement: Per-start setup is idempotent
Repeated starts over the same state SHALL leave the same result as a single start, without duplicating configuration or redoing work that is already in place.

#### Scenario: Restart over configured state
- **WHEN** the container is restarted after a successful start
- **THEN** the virtualenv is not rebuilt and the git configuration holds a single value per setting
