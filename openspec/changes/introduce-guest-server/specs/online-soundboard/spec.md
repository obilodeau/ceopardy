# Spec Delta

## MODIFIED Requirements

### Requirement: Soundboard exists only in online mode
The soundboard page, its link, and the host's soundboard controls SHALL exist only when
the server runs with `--online`.

#### Scenario: Offline server
- **WHEN** the server runs without `--online`
- **THEN** no soundboard link can be fetched, the host's top drawer shows no soundboard row, and nothing listens on the guest port

#### Scenario: Online server
- **WHEN** the server runs with `--online`
- **THEN** the soundboard page is served at `/soundboard.html` on the guest port and the host's top drawer shows a soundboard row

### Requirement: Soundboard page sees only sound names
The soundboard page SHALL receive only the sound list (labels and identifiers) and
connection status. It SHALL NOT receive game state, scores, clues, team names, buzzer
links or audio files. The guest port SHALL NOT serve the sound files.

#### Scenario: What the guest port serves
- **WHEN** anyone requests a sound file or the host or viewer pages from the guest port
- **THEN** the response is 404

#### Scenario: What the page receives
- **WHEN** the soundboard page is connected during a game
- **THEN** the messages it receives contain only the sound list
