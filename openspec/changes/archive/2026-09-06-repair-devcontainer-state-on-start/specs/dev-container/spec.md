# Spec Delta

## ADDED Requirements

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
