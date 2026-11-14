# remote-buzzers Specification

## Purpose
Lets remote players buzz from a web page in online mode, through a secret
per-team link and a dedicated listener that exposes nothing of the host or
the viewer, and lets the host hand out, replace and monitor those links.

## Requirements

### Requirement: Remote buzzers exist only in online mode
The buzzer page, team links and the host's link controls SHALL exist only when the server runs in online mode, which is the only mode with a guest port.

#### Scenario: Offline
- **WHEN** the operator runs `ceopardy serve` without `--online`
- **THEN** nothing listens on the guest port and the top drawer shows no link controls

### Requirement: Each team has one secret link per game
Each team SHALL have a buzzer link carrying a random token of at least 128 bits, created when first needed. Tokens SHALL persist across a server restart within a game and SHALL be replaced when a new game starts, so last game's links stop working.

#### Scenario: Restart
- **WHEN** the server restarts mid-game with the same public URL
- **THEN** links handed out before the restart still work

#### Scenario: New game
- **WHEN** a new game is started
- **THEN** links from the previous game are refused

### Requirement: The token stays out of requests and screens
A link SHALL carry the token in the URL fragment, which is never sent over HTTP. The page SHALL keep the token for the tab, remove it from the address bar, and send it only in the socket's connection handshake, never in a URL. The token is never logged.

#### Scenario: Opening a link
- **WHEN** a player opens their link
- **THEN** the address bar no longer shows the token and no HTTP request or log line contains it

#### Scenario: Reload
- **WHEN** a player reloads the buzzer page in the same tab
- **THEN** the page reconnects as the same team

### Requirement: A link binds the player to one team
On connection the server SHALL match the token against each team's token in constant time and bind the connection to that team. Buzz messages SHALL NOT name a team. A missing or unknown token SHALL be refused, and the page SHALL say the link is not valid.

#### Scenario: Valid link
- **WHEN** a player connects with team 2's token
- **THEN** every buzz on that connection counts for team 2

#### Scenario: Unknown token
- **WHEN** a client connects with a missing or wrong token
- **THEN** the connection is refused and the page asks for the team's link

### Requirement: Several players can share a team link
Any number of players up to a per-team limit (16 by default) SHALL be able to connect with the same team link at once. A connection over the limit SHALL be refused, and the page SHALL say the team's link has too many players.

#### Scenario: Two teammates
- **WHEN** two players open team 1's link
- **THEN** both pages show team 1's name and either can buzz for team 1

#### Scenario: Over the limit
- **WHEN** a 17th player connects with one team's link under the default limit
- **THEN** the connection is refused

### Requirement: The buzzer page sees only its own team
The buzzer page SHALL receive only: its team's name (on connect and on rename), buzzers opening with a race number, buzzers closing with whether its team won, its team's place and margin in a race it entered, being excluded as a locked-out team, latency pings, and link revocation. It SHALL NOT receive scores, other teams' names or reactions, questions, answers, the board or game broadcasts.

#### Scenario: Rename
- **WHEN** the host renames team 1
- **THEN** team 1's buzzer pages show the new name and no other page receives it

#### Scenario: Question selected
- **WHEN** the host selects a question
- **THEN** the buzzer page learns only that buzzers are open, not the question text

#### Scenario: Race decided
- **WHEN** team 2 beats team 1 by 8 ms
- **THEN** team 1's pages learn they were second by 8 ms, but not team 2's name or reaction

### Requirement: Buzzer page shows the game's buzzer state
The buzzer page SHALL show the team name and one large button, with distinct states for connecting, waiting, open, buzzed, won, another team faster, too early, team already answered, invalid link, team full, revoked link and reconnecting. Pressing (pointer down, Space or Enter) while open SHALL buzz.

#### Scenario: Open
- **WHEN** the host selects a question
- **THEN** the button lights up and a press buzzes for the team

#### Scenario: Team already answered
- **WHEN** buzzers re-open after the player's team was marked wrong
- **THEN** the page reads that the team already answered and the button stays inactive

#### Scenario: Lost the race
- **WHEN** another team wins the race
- **THEN** the page says another team was faster

#### Scenario: Host closes
- **WHEN** the host locks the buzzers without a winner
- **THEN** the page returns to waiting

### Requirement: Buzzer page stays usable on phones
The buzzer page SHALL avoid double-tap zoom delay on the button and SHALL keep the screen awake while visible where the browser supports it.

#### Scenario: Phone between questions
- **WHEN** a player leaves the page open on a phone that supports screen wake lock
- **THEN** the screen does not sleep while the page is visible

### Requirement: The host hands out links from the top drawer
In online mode, each team row in the host's top drawer SHALL offer a copy control that puts that team's link on the clipboard and briefly confirms. When the clipboard is unavailable it SHALL show the link in a prompt to copy by hand. The token SHALL NOT be displayed on the page otherwise.

#### Scenario: Copy
- **WHEN** the host clicks the copy icon next to team 1
- **THEN** team 1's link is on the clipboard and the icon shows a check mark for 1.5 seconds

#### Scenario: Renamed team
- **WHEN** the host renames a team
- **THEN** that team's link is unchanged

### Requirement: The host can replace a team's link
The host SHALL be able to give a team a new link after confirming. The old token SHALL stop working at once, that team's connected pages SHALL be told the link is revoked and be disconnected, and other host windows SHALL refresh their links.

#### Scenario: Rotate
- **WHEN** the host confirms a new link for team 1
- **THEN** open team 1 pages show the link is no longer valid, the old link is refused, and the new link works

#### Scenario: Cancel
- **WHEN** the host dismisses the confirmation
- **THEN** team 1's link is unchanged

### Requirement: The host sees who has joined
In online mode, each team row in the top drawer SHALL show how many players are connected on that team's link, highlighted once at least one has joined, and updated live as players connect and disconnect.

#### Scenario: Player joins
- **WHEN** a player opens team 2's link
- **THEN** team 2's count goes up by one and is highlighted

### Requirement: Links are kept away from the viewer
Team links SHALL be served only to the host through a dedicated endpoint on the host port. They SHALL NOT appear in the full game state, in game broadcasts, or on the guest port, and the endpoint SHALL NOT be readable cross-origin.

#### Scenario: Viewer
- **WHEN** the viewer loads the game state
- **THEN** it contains no team link or token

#### Scenario: Rotation broadcast
- **WHEN** a link is rotated
- **THEN** the game broadcast tells host windows to refetch, without carrying any link

### Requirement: The buzzer page is a guest page
The buzzer page SHALL be served at `/` on the guest port, under the rules of the `guest-port` capability.

#### Scenario: Buzzer page
- **WHEN** a client requests `/` on the guest port
- **THEN** it receives the buzzer page

### Requirement: Buzzer page shows how close the race was
When told its team's standing, the buzzer page SHALL show the margin in whole milliseconds under the won or lost message: `8 ms ahead` for the first place, and the place with the margin behind the winner, such as `2nd · +8 ms`, for any other. The line SHALL clear when buzzers open again, when the team is excluded, or when the host closes the buzzers without a winner.

#### Scenario: Winner
- **WHEN** the player's team wins by 8 ms over the runner-up
- **THEN** the page reads "You're in! Answer now." and `8 ms ahead`

#### Scenario: Runner-up
- **WHEN** the player's team finishes second, 8 ms behind the winner
- **THEN** the page reads "Another team was faster." and `2nd · +8 ms`

#### Scenario: Buzzing after the decision
- **WHEN** the page shows "Another team was faster." with no margin and the player then buzzes
- **THEN** the page keeps reading "Another team was faster." without showing too early, sends the player's reaction measured from the race's open cue, and adds its team's place and margin, such as `3rd · +640 ms`

#### Scenario: No margin to show
- **WHEN** the player's team won alone with nobody buzzing after, or never buzzed
- **THEN** the page shows its won or lost message with no margin line

#### Scenario: Next question
- **WHEN** buzzers open for the next question
- **THEN** the margin line is gone
