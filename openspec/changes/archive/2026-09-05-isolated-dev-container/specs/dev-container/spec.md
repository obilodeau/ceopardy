# Spec Delta

## Purpose

Defines the development container as a disposable trust boundary. Coding
agents and third-party dependency code run in it with access to the
workspace and a few narrowly scoped secrets. They cannot reach the rest of
the developer's machine, and a rebuild removes anything a compromise left
behind outside the workspace.

## ADDED Requirements

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
