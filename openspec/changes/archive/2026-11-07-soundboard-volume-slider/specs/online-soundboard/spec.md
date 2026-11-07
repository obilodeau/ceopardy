# Spec Delta

## ADDED Requirements

### Requirement: Soundboard volume slider
The soundboard page SHALL have a volume slider from 0 to 100 %. Moving it SHALL set
the volume of every soundboard sound on the viewer, those already playing and those
started later. It SHALL NOT change the volume of the game's own sounds or the thinking
music.

#### Scenario: Turn down a playing sound
- **WHEN** `applause` is playing on the viewer and the operator drags the slider to 30 %
- **THEN** `applause` keeps playing at 30 % volume, and the next sound pressed also plays at 30 %

#### Scenario: Game sounds unaffected
- **WHEN** the soundboard volume is 20 % and a team buzzes in
- **THEN** the buzzer sound plays at its usual volume

#### Scenario: Mute
- **WHEN** the operator drags the slider to 0 %
- **THEN** soundboard sounds are silent on the viewer and still play when pressed

### Requirement: Soundboard volume defaults to 85 %
The soundboard volume SHALL be 85 % when the server starts.

#### Scenario: Fresh server
- **WHEN** the server starts and the operator opens the soundboard page
- **THEN** the slider shows 85 % and the first sound pressed plays at 85 % on the viewer

### Requirement: Soundboard volume is shared
The server SHALL keep one soundboard volume. A soundboard page SHALL show the current
volume when it connects and SHALL follow changes made from other soundboard pages. A
viewer that reloads SHALL play the next soundboard sound at the current volume.

#### Scenario: Two operators
- **WHEN** two soundboard pages are connected and one moves the slider to 50 %
- **THEN** the other page's slider moves to 50 %

#### Scenario: Late join
- **WHEN** the volume was set to 40 % and a new soundboard page connects
- **THEN** its slider shows 40 %

#### Scenario: Viewer reload
- **WHEN** the volume was set to 40 % before the viewer was reloaded and the operator presses a sound
- **THEN** the reloaded viewer plays it at 40 %

### Requirement: Only valid volumes are applied
The server SHALL accept a volume only when it is a number from 0 to 100. Anything else
SHALL be ignored and nothing broadcast.

#### Scenario: Invalid volume
- **WHEN** a client sends a volume of `150`, `-1`, `"loud"` or no value
- **THEN** the volume is unchanged and nothing is broadcast

## MODIFIED Requirements

### Requirement: Playback is bounded
The viewer SHALL play at most 8 soundboard sounds at once, stopping the oldest to start
a new one. The server SHALL ignore more than 5 play requests per second from one
soundboard connection. The soundboard page SHALL send at most one volume change every
100 ms while the slider moves, always sending the value it stops on, and the server
SHALL ignore more than 20 volume changes per second from one soundboard connection.

#### Scenario: Button mashing
- **WHEN** a client sends 50 play requests in one second
- **THEN** at most 5 are broadcast, and the viewer never has more than 8 soundboard sounds playing

#### Scenario: Slider drag
- **WHEN** the operator drags the slider continuously for one second and lets go at 60 %
- **THEN** the page sends at most about 10 volume changes, and the viewer ends at 60 %

#### Scenario: Volume flood
- **WHEN** a client sends 100 volume changes in one second
- **THEN** at most 20 are broadcast

### Requirement: Soundboard page sees only sound names
The soundboard page SHALL receive only the sound list (labels and identifiers), the
current soundboard volume and connection status. It SHALL NOT receive game state,
scores, clues, team names, buzzer links or audio files. The guest port SHALL NOT serve
the sound files.

#### Scenario: What the guest port serves
- **WHEN** anyone requests a sound file or the host or viewer pages from the guest port
- **THEN** the response is 404

#### Scenario: What the page receives
- **WHEN** the soundboard page is connected during a game
- **THEN** the messages it receives contain only the sound list and the soundboard volume
