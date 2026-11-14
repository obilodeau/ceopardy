# Spec Delta

## Purpose

Gives each team a shared, hand-drawn answer sheet on the page behind its
secret buzzer link, so remote teams can write a Final Jeopardy wager and
answer without exposing anything else on the internet-facing port.

## ADDED Requirements

### Requirement: Canvas uses the buzzer link and port
The canvas SHALL be reached only through a team's buzzer link, on the buzzer
port. It SHALL use the same link check, per-team player limit, and HTTP
security headers as the buzzer. No new URL or port is exposed.

#### Scenario: Valid link during the final round
- **WHEN** a player opens their team's buzzer link while the game is in the final round
- **THEN** the page shows the team's name and its canvas

#### Scenario: Invalid link
- **WHEN** a player opens the buzzer page with a token that matches no team
- **THEN** the connection is refused and no canvas or drawing is shown

#### Scenario: Revoked link
- **WHEN** the host replaces a team's link during the final round
- **THEN** players on the old link are disconnected and can no longer draw

### Requirement: Page follows the game between buzzer and canvas
The page SHALL show the buzzer outside the final round and the canvas during
it. A page already open SHALL switch when the round starts, without a
reload.

#### Scenario: Final round starts
- **WHEN** a player's page shows the buzzer and the host starts the final round
- **THEN** the page switches to the wager canvas

#### Scenario: Joining mid-round
- **WHEN** a player opens the link while the phase is `clue`
- **THEN** the page shows the answer canvas, with the wager canvas read-only

### Requirement: Each canvas is open in one phase only
Each team SHALL have a wager canvas, which accepts strokes only in the
`category` phase, and an answer canvas, which accepts strokes only in the
`clue` phase. The server SHALL drop any stroke, undo or clear for a canvas
that is not open, and the page SHALL show closed canvases as read-only.

#### Scenario: Wager locks at the clue reveal
- **WHEN** the host reveals the clue
- **THEN** the wager canvas stops accepting strokes and the answer canvas starts accepting them

#### Scenario: Late stroke after lock
- **WHEN** a player's stroke for the answer canvas reaches the server after the host locked the answers
- **THEN** the stroke is not stored and is not shown to anyone

### Requirement: Teammates share one live canvas
Every stroke a player draws SHALL appear on the screens of the other players
connected with the same team link while it is drawn. Strokes SHALL NOT reach
players of other teams.

#### Scenario: Two teammates
- **WHEN** two players are on Team 1's link and one draws on the answer canvas
- **THEN** the other player sees the stroke appear on their canvas

#### Scenario: Other teams see nothing
- **WHEN** a player on Team 1 draws
- **THEN** no player on Team 2 or Team 3 receives that stroke

### Requirement: Joining or reconnecting restores the drawing
A player who connects or reconnects during the final round SHALL receive their
team's current wager and answer drawings.

#### Scenario: Reconnect after a dropped connection
- **WHEN** a player's connection drops and comes back while the phase is `clue`
- **THEN** their canvases show every stroke the team has drawn so far

### Requirement: Players can undo and clear
On an open canvas, a player SHALL be able to undo their own last stroke and to
clear the whole canvas. Both SHALL reach every teammate.

#### Scenario: Undo
- **WHEN** a player undoes on the answer canvas
- **THEN** their most recent stroke on that canvas disappears for the whole team, and teammates' strokes stay

#### Scenario: Clear
- **WHEN** a player clears the wager canvas while it is open
- **THEN** the wager canvas is empty for the whole team

### Requirement: Stroke data is validated and bounded
The server SHALL accept only well-formed strokes: coordinates within the
canvas, a color from a fixed palette, a width from a fixed set, and a bounded
number of points per message. Each canvas SHALL have a cap on total points.
Invalid strokes and strokes past the cap SHALL be dropped.

#### Scenario: Malformed stroke
- **WHEN** a client sends a stroke with coordinates outside the canvas, an unknown color, or a non-numeric point
- **THEN** the stroke is dropped and the connection stays open

#### Scenario: Canvas full
- **WHEN** a team's answer canvas reaches its point cap
- **THEN** further strokes on it are dropped and the page tells the player the canvas is full

### Requirement: Page receives only its own team's data
During the final round the page SHALL receive only the phase, the category,
its own team's name and its own team's drawings. It SHALL NOT receive the
clue, scores, other teams' drawings, or judgments.

#### Scenario: What the page receives
- **WHEN** the phase is `clue`
- **THEN** the messages the page receives contain no clue text, no score, and no other team's strokes

### Requirement: Drawings are kept with the game
When the answers are locked, each team's drawings SHALL be saved with the game
in the same database, so the host and viewer can still show them after a
reload or a server restart.

#### Scenario: Server restart after lock
- **WHEN** the phase is `locked` and the server is restarted
- **THEN** the host still shows every team's wager and answer drawings
