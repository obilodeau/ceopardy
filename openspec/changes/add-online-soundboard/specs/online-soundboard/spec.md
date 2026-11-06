# Spec Delta

## Purpose

Lets a remote sound operator play the game's own sound files through the viewer tab
that is shared to the online audience, without exposing anything else on the
internet-facing port.

## ADDED Requirements

### Requirement: Soundboard exists only in online mode
The soundboard page, its link, and the host's soundboard controls SHALL exist only when
the server runs with `--online`.

#### Scenario: Offline server
- **WHEN** the server runs without `--online`
- **THEN** no soundboard link can be fetched, the host's top drawer shows no soundboard row, and nothing listens on the buzzer port

#### Scenario: Online server
- **WHEN** the server runs with `--online`
- **THEN** the soundboard page is served on the buzzer port and the host's top drawer shows a soundboard row

### Requirement: Sounds come from the game's soundboard folder
The soundboard SHALL offer one sound per audio file (`.mp3`, `.wav`, `.ogg`, `.m4a`,
`.opus`) directly inside the `soundboard/` folder of the game directory, sorted by file
name. Each is labelled with the file name minus its extension. Hidden files,
subfolders and other file types SHALL be ignored.

#### Scenario: Folder with sounds
- **WHEN** `soundboard/` holds `01-applause.mp3`, `airhorn.wav`, `notes.txt` and `.DS_Store`
- **THEN** the soundboard shows two buttons, `01-applause` then `airhorn`

#### Scenario: Missing or empty folder
- **WHEN** `soundboard/` does not exist or holds no audio file
- **THEN** the soundboard page says there are no sounds and shows only the Stop all button

#### Scenario: Files added during the game
- **WHEN** the operator adds a file to `soundboard/` and the soundboard page refreshes its list
- **THEN** the new sound appears

### Requirement: `ceopardy init` creates the folder
`ceopardy init` SHALL create an empty `soundboard/` folder in the game directory when it
does not exist, and leave an existing one untouched.

#### Scenario: Fresh game directory
- **WHEN** the operator runs `ceopardy init` in an empty directory
- **THEN** `soundboard/` exists and the output lists it as created

### Requirement: Soundboard link is a secret of its own
There SHALL be one soundboard secret, separate from every team's buzzer secret. The
soundboard page SHALL connect only with that secret, and a buzzer connection SHALL NOT
accept it.

#### Scenario: Soundboard link
- **WHEN** someone opens the soundboard link the host copied
- **THEN** the page connects and lists the sounds

#### Scenario: Buzzer secret on the soundboard
- **WHEN** a page tries to connect to the soundboard with a team's buzzer secret
- **THEN** the connection is refused

#### Scenario: Soundboard secret on the buzzer
- **WHEN** a page tries to connect as a buzzer with the soundboard secret
- **THEN** the connection is refused

#### Scenario: Secret stays out of logs
- **WHEN** the host copies the soundboard link
- **THEN** the secret is in the URL fragment, which browsers do not send to the server or the tunnel

### Requirement: Host hands out and replaces the link
In the top drawer, the host SHALL be able to copy the soundboard link, replace it, and
see how many soundboard pages are connected. Replacing it SHALL disconnect every page
using the old link.

#### Scenario: Replace a leaked link
- **WHEN** the host replaces the soundboard link while a page is connected with the old one
- **THEN** that page is disconnected, tells its user the link is no longer valid, and cannot reconnect with it

#### Scenario: Presence count
- **WHEN** two soundboard pages are connected
- **THEN** the host's soundboard row shows 2

### Requirement: The soundboard link is never sent to the viewer
The soundboard link and secret SHALL only ever be sent to the host, on request. They
SHALL NOT appear in the game state or in any broadcast the viewer receives.

#### Scenario: Viewer state
- **WHEN** the viewer loads the game state or receives any broadcast
- **THEN** none of them contain the soundboard secret

### Requirement: Pressing a sound plays it on the viewer
When a soundboard button is pressed, the viewer SHALL play that sound once, from the
start. Sounds already playing keep playing, so sounds can overlap. The host page,
including its embedded viewer preview, and the soundboard page SHALL NOT play it.

#### Scenario: Play
- **WHEN** the sound operator presses `airhorn`
- **THEN** the viewer tab plays `airhorn.wav` once, and the host tab stays silent

#### Scenario: Overlap
- **WHEN** the operator presses `applause` and then `airhorn` while applause is still playing
- **THEN** the viewer plays both at once

### Requirement: Stop all silences the soundboard
Stop all SHALL immediately stop every soundboard sound playing on the viewer. It SHALL
NOT stop the game's own sounds or the thinking music.

#### Scenario: Stop all during thinking music
- **WHEN** the thinking music and two soundboard sounds are playing and the operator presses Stop all
- **THEN** both soundboard sounds stop and the thinking music keeps playing

### Requirement: Only listed sounds can be played
The server SHALL play only a sound in the current folder listing. Any other name,
including a path, SHALL be ignored.

#### Scenario: Path traversal attempt
- **WHEN** a client asks to play `../data/Questions.cp` or `/etc/passwd`
- **THEN** nothing is played and nothing is broadcast

#### Scenario: Deleted file
- **WHEN** a client asks to play a sound whose file was removed from the folder
- **THEN** nothing is played

### Requirement: Playback is bounded
The viewer SHALL play at most 8 soundboard sounds at once, stopping the oldest to start
a new one. The server SHALL ignore more than 5 play requests per second from one
soundboard connection.

#### Scenario: Button mashing
- **WHEN** a client sends 50 play requests in one second
- **THEN** at most 5 are broadcast, and the viewer never has more than 8 soundboard sounds playing

### Requirement: Soundboard page sees only sound names
The soundboard page SHALL receive only the sound list (labels and identifiers) and
connection status. It SHALL NOT receive game state, scores, clues, team names, buzzer
links or audio files. The buzzer port SHALL NOT serve the sound files.

#### Scenario: What the buzzer port serves
- **WHEN** anyone requests a sound file or the host or viewer pages from the buzzer port
- **THEN** the response is 404

#### Scenario: What the page receives
- **WHEN** the soundboard page is connected during a game
- **THEN** the messages it receives contain only the sound list

### Requirement: Viewer must have sound enabled
Soundboard sounds SHALL use the viewer's existing "click to enable sound" step and play
nothing until it is done.

#### Scenario: Viewer not yet clicked
- **WHEN** the viewer has not been clicked yet and the operator presses a sound
- **THEN** no sound plays, and the viewer still shows its enable-sound prompt
