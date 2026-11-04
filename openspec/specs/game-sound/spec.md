# game-sound Specification

## Purpose
Defines which sounds Ceopardy plays during a game and which window plays
them, so the audience hears the cues whether they are in the room with the
host or watching a screen-shared viewer online.

## Requirements

### Requirement: Game events trigger sound cues
The host's game actions SHALL trigger these sound cues: a team buzzing in plays that team's buzzer sound, selecting a daily double plays the daily-double sound, the host's timeout control plays the timeout sound, and the host's music control starts or stops the waiting music.

#### Scenario: Team buzzes in
- **WHEN** team 2 buzzes in
- **THEN** the buzzer sound for team 2 plays

#### Scenario: Daily double selected
- **WHEN** the host selects a question that is a daily double
- **THEN** the daily-double sound plays

#### Scenario: Timeout
- **WHEN** the host uses the timeout control
- **THEN** the timeout sound plays

#### Scenario: Teams beyond the available buzzer sounds
- **WHEN** a team numbered higher than the number of buzzer sounds buzzes in
- **THEN** no buzzer sound plays and the buzz is otherwise unaffected

### Requirement: Sound cues reach every connected client
Every sound cue SHALL be sent through the server and broadcast to all connected game clients, including other host windows and viewers on other machines or browsers. Each client SHALL decide locally whether it plays the cue.

#### Scenario: Viewer on another machine receives a cue
- **WHEN** the host triggers the timeout sound and a viewer is open on a different machine
- **THEN** the viewer receives the timeout cue

### Requirement: Host plays sound in normal mode
When online mode is off, top-level host windows SHALL play every sound cue and viewers SHALL stay silent.

#### Scenario: Default mode
- **WHEN** the server runs without online mode and the host triggers a buzzer
- **THEN** the buzzer plays on the host window
- **AND** the viewer plays nothing

### Requirement: Viewer plays sound in online mode
When online mode is on, top-level viewer windows SHALL play every sound cue and host windows SHALL stay silent.

#### Scenario: Online mode
- **WHEN** the server runs in online mode and the host triggers the daily-double sound
- **THEN** the daily-double sound plays on the viewer
- **AND** the host window plays nothing

### Requirement: Embedded viewer preview is always silent
A viewer embedded inside another page, such as the live viewer preview on the host page, SHALL never play sound, in either mode.

#### Scenario: Host preview in online mode
- **WHEN** online mode is on and the host page shows its embedded viewer preview
- **THEN** the preview plays no sound and the host page stays silent

#### Scenario: Host preview in normal mode
- **WHEN** online mode is off and the host triggers a buzzer
- **THEN** the buzzer plays once on the host, not a second time from the preview

### Requirement: Online mode is opt-in at server start
Online mode SHALL be off by default and turned on with the `--online` flag of `ceopardy serve`, or with `CEOPARDY_ONLINE` set to a value other than empty or `0` when using the development server. The server SHALL advertise the mode to clients in the game state and SHALL say so in its startup banner when it is on.

#### Scenario: Default start
- **WHEN** the operator runs `ceopardy serve`
- **THEN** the game state reports online mode as off

#### Scenario: Online start
- **WHEN** the operator runs `ceopardy serve --online`
- **THEN** the startup banner states that sounds play on the viewer
- **AND** the game state reports online mode as on from the first request

### Requirement: Sound registry is served by the server
The server SHALL publish, in the full game state, the map of sound names to playable URLs. Clients SHALL play only sounds present in that map, and every name in it SHALL be accepted by the sound endpoint.

#### Scenario: Client loads the registry
- **WHEN** a client fetches the game state
- **THEN** the response contains a URL for each of buzzer1, buzzer2, buzzer3, timeout, reveal, thinking and dailydouble

### Requirement: Sound requests are validated
`POST /api/v1/sound` SHALL accept a JSON body with a `name` from the sound registry and an `action` of exactly `play` or `stop`, then broadcast the cue and answer success. Any other name or action, including a missing or malformed body, SHALL be rejected with HTTP 400, a failure result and an error message, and SHALL broadcast nothing.

#### Scenario: Valid request
- **WHEN** a client posts `{"name": "timeout", "action": "play"}`
- **THEN** the server answers success and broadcasts a timeout play cue

#### Scenario: Unknown sound name
- **WHEN** a client posts a name not in the registry, such as `buzzer4` or a path
- **THEN** the server answers 400 with an error and broadcasts nothing

#### Scenario: Unknown action
- **WHEN** a client posts `{"name": "timeout", "action": "pause"}`
- **THEN** the server answers 400 with an error and broadcasts nothing

### Requirement: Waiting music loops until stopped
The waiting music SHALL loop continuously from the moment it is started until the host stops it, and the host's music control SHALL toggle it between playing and stopped.

#### Scenario: Long break
- **WHEN** the host starts the waiting music and leaves it on longer than the track
- **THEN** the music keeps playing from the start of the track again

#### Scenario: Toggle off
- **WHEN** the waiting music is playing and the host uses the music control
- **THEN** the music stops on every client that was playing it

### Requirement: Waiting music state survives joins and reloads
The server SHALL keep whether the waiting music is on as part of the game state. A client that loads or reconnects while the music is on SHALL start playing it if it is the window that plays sound.

#### Scenario: Viewer reloads mid-break in online mode
- **WHEN** online mode is on, the waiting music is playing, and the viewer is reloaded
- **THEN** the reloaded viewer resumes the waiting music

### Requirement: Viewer asks for one click to enable sound in online mode
In online mode a top-level viewer SHALL show an "enable sound" overlay until it is clicked, so the browser allows audio. After one click the overlay SHALL not return for the rest of that browser tab's session, including across reloads. The overlay SHALL not appear in normal mode or in an embedded viewer preview.

#### Scenario: First viewer load in online mode
- **WHEN** online mode is on and the viewer is opened in a fresh tab
- **THEN** the overlay is shown, and clicking anywhere on it dismisses it and enables sound

#### Scenario: Reload after unlocking
- **WHEN** the overlay was already clicked in this tab and the viewer is reloaded
- **THEN** the overlay is not shown again

#### Scenario: Normal mode
- **WHEN** online mode is off
- **THEN** the viewer never shows the overlay

### Requirement: Missing sound files fail silently
A sound file that cannot be loaded SHALL not raise an error or disrupt the game; the cue is skipped.

#### Scenario: Fresh clone without licensed sounds
- **WHEN** the timeout sound file is absent and the host triggers a timeout
- **THEN** no sound plays and the game continues without an error shown
