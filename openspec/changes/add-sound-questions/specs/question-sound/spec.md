# Spec Delta

## Purpose

Lets a question file make a clue that is a sound, optionally with text,
played to the audience from the window that carries the game's audio, with
the host able to replay or stop it from the embedded viewer preview.

## ADDED Requirements

### Requirement: Question files accept a sound tag
A question containing `[sound:<file>]` anywhere on its line SHALL be a sound clue. `<file>` SHALL name a file in the game's `game-media/` folder, served at `/static/game-media/<file>`, the same folder `[img:]` and `[video:]` use. Only the first such tag SHALL count; later ones are shown as text. The tag SHALL also be accepted after the `[dbl]` daily-double prefix.

#### Scenario: Sound clue
- **WHEN** a question in `Questions.cp` reads `[sound:theme.mp3]`
- **THEN** that question is a sound clue playing `/static/game-media/theme.mp3`

#### Scenario: Tag with surrounding text
- **WHEN** a question reads `Name this tune: [sound:theme.mp3]`
- **THEN** it is a sound clue playing `theme.mp3`

#### Scenario: Daily double sound clue
- **WHEN** a question reads `[dbl] Who sings this? [sound:theme.mp3]`
- **THEN** it is a daily double whose clue is a sound clue

#### Scenario: Two tags
- **WHEN** a question reads `[sound:a.mp3] or [sound:b.mp3]?`
- **THEN** it plays `a.mp3` and its text reads `or [sound:b.mp3]?`

#### Scenario: File name with markup characters
- **WHEN** a question reads `[sound:a"b<c>.mp3]`
- **THEN** the file name cannot inject markup into the host or viewer page

### Requirement: Sound clues show a speaker icon and their text
While a sound clue is open, the viewer's clue overlay and the host's clue box SHALL show a speaker icon followed by the question's text with the sound tag removed, formatted like any other clue text. They SHALL not show an audio player.

#### Scenario: Clue with text
- **WHEN** the host selects a clue reading `Name this tune: [sound:theme.mp3]`
- **THEN** the viewer and the host show a speaker icon and `Name this tune:`, without the tag

#### Scenario: Clue with only the tag
- **WHEN** the host selects a clue reading `[sound:theme.mp3]`
- **THEN** the viewer and the host show only a speaker icon

### Requirement: Sound clues play once when shown
When a sound clue is shown, its sound SHALL play once from the start on the window that plays game sounds as defined by `game-sound` (the host in normal mode, the top-level viewer in online mode, never an embedded viewer preview). For a daily double, this SHALL happen when the clue is revealed, not when the daily double is selected.

#### Scenario: Normal mode
- **WHEN** online mode is off and the host selects a sound clue
- **THEN** the sound plays once on the host window and the viewer stays silent

#### Scenario: Online mode
- **WHEN** online mode is on and the host selects a sound clue
- **THEN** the sound plays once on the top-level viewer, and the host window and its embedded preview stay silent

#### Scenario: Daily double
- **WHEN** the host selects a daily double whose clue is a sound clue
- **THEN** nothing from the clue plays until the host reveals it, and then the sound plays once

#### Scenario: Missing file
- **WHEN** the sound clue names a file that is not in `game-media/`
- **THEN** no sound plays and the game otherwise continues normally

### Requirement: Sound stops when the clue closes
Closing a sound clue SHALL stop its sound on every client that is playing it.

#### Scenario: Host closes the clue mid-sound
- **WHEN** a sound clue is still playing and the host closes the clue
- **THEN** the sound stops

### Requirement: Embedded viewer preview offers Replay and Stop
While a sound clue is open, a viewer embedded in another page, such as the host's viewer preview, SHALL show Replay and Stop buttons on the clue. Replay SHALL restart the sound from the beginning and Stop SHALL silence it, on the window that plays game sounds. A top-level viewer SHALL never show these buttons, and neither SHALL any viewer for other clues.

#### Scenario: Replay in online mode
- **WHEN** online mode is on, a sound clue is open, and the host clicks Replay in the embedded preview
- **THEN** the top-level viewer plays the sound again from the beginning, and the host page stays silent

#### Scenario: Replay in normal mode
- **WHEN** online mode is off, a sound clue is open, and the host clicks Replay in the embedded preview
- **THEN** the host window plays the sound again from the beginning, once

#### Scenario: Stop
- **WHEN** a sound clue is playing and the host clicks Stop in the embedded preview
- **THEN** the sound stops and the clue stays open

#### Scenario: Audience viewer
- **WHEN** a sound clue is open on a top-level viewer
- **THEN** that viewer shows no Replay or Stop button

#### Scenario: Text clue
- **WHEN** the open clue is not a sound clue
- **THEN** the embedded preview shows no Replay or Stop button

### Requirement: Replay and stop requests are validated
`POST /api/v1/question-sound` SHALL accept a JSON body with an `action` of exactly `play` or `stop` and broadcast it to all game clients. It SHALL answer HTTP 400 with a failure result and broadcast nothing when the action is anything else, the body is missing or malformed, or the open clue is not a sound clue or is a daily double not yet revealed.

#### Scenario: Valid replay
- **WHEN** a sound clue is open and a client posts `{"action": "play"}`
- **THEN** the server answers success and broadcasts a question-sound play cue

#### Scenario: No sound clue open
- **WHEN** no clue, or a text clue, is open and a client posts `{"action": "play"}`
- **THEN** the server answers 400 with an error and broadcasts nothing

#### Scenario: Daily double not yet revealed
- **WHEN** a daily double sound clue is selected but not revealed and a client posts `{"action": "play"}`
- **THEN** the server answers 400 with an error and broadcasts nothing

#### Scenario: Unknown action
- **WHEN** a sound clue is open and a client posts `{"action": "pause"}`
- **THEN** the server answers 400 with an error and broadcasts nothing

### Requirement: Joining mid-clue does not start the sound
A client that loads or reconnects while a sound clue is open SHALL show the clue but SHALL not start the sound on its own; it SHALL play only on a later Replay.

#### Scenario: Viewer reloads in online mode
- **WHEN** online mode is on, a sound clue is open, and the viewer is reloaded
- **THEN** the viewer shows the clue and stays silent until the host uses Replay
