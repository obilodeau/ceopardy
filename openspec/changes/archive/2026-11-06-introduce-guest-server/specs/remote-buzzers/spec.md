# Spec Delta

## ADDED Requirements

### Requirement: The buzzer page is a guest page
The buzzer page SHALL be served at `/` on the guest port, under the rules of the `guest-port` capability.

#### Scenario: Buzzer page
- **WHEN** a client requests `/` on the guest port
- **THEN** it receives the buzzer page

## MODIFIED Requirements

### Requirement: Remote buzzers exist only in online mode
The buzzer page, team links and the host's link controls SHALL exist only when the server runs in online mode, which is the only mode with a guest port.

#### Scenario: Offline
- **WHEN** the operator runs `ceopardy serve` without `--online`
- **THEN** nothing listens on the guest port and the top drawer shows no link controls

### Requirement: Links are kept away from the viewer
Team links SHALL be served only to the host through a dedicated endpoint on the host port. They SHALL NOT appear in the full game state, in game broadcasts, or on the guest port, and the endpoint SHALL NOT be readable cross-origin.

#### Scenario: Viewer
- **WHEN** the viewer loads the game state
- **THEN** it contains no team link or token

#### Scenario: Rotation broadcast
- **WHEN** a link is rotated
- **THEN** the game broadcast tells host windows to refetch, without carrying any link

## REMOVED Requirements

### Requirement: Players use a separate listener
**Reason**: The listener now serves every guest page, not only the buzzers.
**Migration**: See "Guests use a separate listener" in `guest-port`. `--buzzer-port` is now `--guest-port`.

### Requirement: The player listener exposes only the buzzer page
**Reason**: The listener now serves every guest page, not only the buzzers.
**Migration**: See "The guest port exposes only guest pages" in `guest-port`, and "The buzzer page is a guest page" above.

### Requirement: Unbuilt buzzer page is reported
**Reason**: An unbuilt front-end affects every guest page.
**Migration**: See "Unbuilt guest pages are reported" in `guest-port`.

### Requirement: Player listener responses are locked down
**Reason**: The headers apply to every guest page.
**Migration**: See "Guest port responses are locked down" in `guest-port`.

### Requirement: Buzzer socket accepts only known origins
**Reason**: Every guest page shares one socket and its origin check.
**Migration**: See "The guest socket accepts only known origins" in `guest-port`.

### Requirement: Choosing the public buzzer URL
**Reason**: The public URL serves every guest page.
**Migration**: See "Choosing the public guest URL" in `guest-port`. `--buzzer-url` is now `--guest-url`.

### Requirement: Finding the ngrok authtoken
**Reason**: The tunnel belongs to the guest port, not to the buzzers.
**Migration**: See "Finding the ngrok authtoken" in `guest-port`; the behavior is unchanged.

### Requirement: The tunnel reaches only the buzzer port
**Reason**: The tunnel belongs to the guest port, not to the buzzers.
**Migration**: See "The tunnel reaches only the guest port" in `guest-port`.

### Requirement: Tunnel problems never stop the game
**Reason**: The tunnel belongs to the guest port, not to the buzzers.
**Migration**: See "Tunnel problems never stop the game" in `guest-port`; the behavior is unchanged.

### Requirement: The buzzer URL is shown to the operator
**Reason**: The URL serves every guest page.
**Migration**: See "The guest URL is shown to the operator" in `guest-port`.

### Requirement: Development server follows the same rules
**Reason**: The dev server starts the guest port, not only the buzzers.
**Migration**: See "Development server follows the same rules" in `guest-port`. `CEOPARDY_BUZZER_URL` is now `CEOPARDY_GUEST_URL`.
