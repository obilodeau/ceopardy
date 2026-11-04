# Spec Delta

## Purpose

Lets remote players buzz from a web page in online mode, through a secret
per-team link and a dedicated listener that exposes nothing of the host or
the viewer, and lets the host hand out, replace and monitor those links.

## ADDED Requirements

### Requirement: Remote buzzers exist only in online mode
The buzzer listener, team links and the host's link controls SHALL exist only when the server runs in online mode. Offline, no buzzer port is opened and no tunnel is created.

#### Scenario: Offline
- **WHEN** the operator runs `ceopardy serve` without `--online`
- **THEN** nothing listens on the buzzer port and the top drawer shows no link controls

### Requirement: Players use a separate listener
The buzzer page SHALL be served from its own listener bound to `127.0.0.1`, on port `5001` by default or the port given with `--buzzer-port`. If the port cannot be bound, the server SHALL exit with a message naming the port and suggesting `--buzzer-port`.

#### Scenario: Default port
- **WHEN** the operator runs `ceopardy serve --online`
- **THEN** the buzzer page is served on `127.0.0.1:5001`

#### Scenario: Port in use
- **WHEN** another process already holds the buzzer port
- **THEN** `ceopardy serve --online` exits with an error suggesting `--buzzer-port`

### Requirement: The player listener exposes only the buzzer page
The player listener SHALL answer only `GET` or `HEAD` of `/` (the buzzer page), the exact files that page loads, and the buzzer socket. Every other path or method SHALL return 404, including host and viewer routes, the host API, the game socket, host and viewer assets, sounds and the build manifest.

#### Scenario: Buzzer page
- **WHEN** a client requests `/` on the buzzer port
- **THEN** it receives the buzzer page

#### Scenario: Host surface
- **WHEN** a client requests `/host`, `/api/v1/state`, `/api/v1/question/select`, `/socket.io/` or a host asset on the buzzer port
- **THEN** it receives 404

#### Scenario: Path tricks
- **WHEN** a client requests a buzzer asset path with `..` segments pointing at another file
- **THEN** it receives 404

#### Scenario: Other methods
- **WHEN** a client sends a `POST` to `/` on the buzzer port
- **THEN** it receives 404

### Requirement: Unbuilt buzzer page is reported
When the frontend has not been built, a request for `/` on the player listener SHALL return 503 with a message saying the buzzer page has not been built.

#### Scenario: No build
- **WHEN** the buzzer page has not been built and a client requests `/`
- **THEN** it receives 503 explaining that the page must be built

### Requirement: Player listener responses are locked down
Every response from the player listener SHALL carry a Content-Security-Policy allowing only same-origin resources and connections and forbidding framing, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`. The page SHALL load no third-party resources.

#### Scenario: Headers
- **WHEN** any path on the buzzer port is requested, including one that returns 404
- **THEN** the response carries the Content-Security-Policy and the other security headers

### Requirement: Buzzer socket accepts only known origins
The buzzer socket SHALL accept connections only from its own origin, including the origin a proxy reports through forwarded-protocol and forwarded-host headers, and from the origin of the configured public URL.

#### Scenario: Through a tunnel
- **WHEN** a player loads the page through the tunnel and connects
- **THEN** the connection is accepted

#### Scenario: Foreign site
- **WHEN** a page on another origin tries to open the buzzer socket
- **THEN** the connection is refused

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
The buzzer page SHALL receive only: its team's name (on connect and on rename), buzzers opening with a race number, buzzers closing with whether its team won, being excluded as a locked-out team, latency pings, and link revocation. It SHALL NOT receive scores, other teams' names, questions, answers, the board or game broadcasts.

#### Scenario: Rename
- **WHEN** the host renames team 1
- **THEN** team 1's buzzer pages show the new name and no other page receives it

#### Scenario: Question selected
- **WHEN** the host selects a question
- **THEN** the buzzer page learns only that buzzers are open, not the question text

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
Team links SHALL be served only to the host through a dedicated endpoint on the host port. They SHALL NOT appear in the full game state, in game broadcasts, or on the buzzer port, and the endpoint SHALL NOT be readable cross-origin.

#### Scenario: Viewer
- **WHEN** the viewer loads the game state
- **THEN** it contains no team link or token

#### Scenario: Rotation broadcast
- **WHEN** a link is rotated
- **THEN** the game broadcast tells host windows to refetch, without carrying any link

### Requirement: Choosing the public buzzer URL
At start-up in online mode, the public URL for links SHALL be chosen in order: the `--buzzer-url` given (no tunnel opened); none with `--no-tunnel`; an ngrok tunnel if an authtoken is found; otherwise none. With no public URL, links point at the local buzzer port.

#### Scenario: Manual URL
- **WHEN** the operator passes `--buzzer-url https://example.trycloudflare.com`
- **THEN** no ngrok tunnel is opened and links are built on that URL

#### Scenario: No tunnel
- **WHEN** the operator passes `--no-tunnel` with an authtoken set
- **THEN** no tunnel is opened and links point at `http://127.0.0.1:5001/`

#### Scenario: Token found
- **WHEN** an ngrok authtoken is available and neither flag is given
- **THEN** a tunnel is opened and links are built on its URL

### Requirement: Finding the ngrok authtoken
The authtoken SHALL be taken from `NGROK_AUTHTOKEN` first, otherwise from the ngrok agent's own config file in its usual locations. It SHALL NOT be accepted on the command line, and SHALL NOT be logged, printed or sent to any client, including in an ngrok error message.

#### Scenario: Agent config
- **WHEN** `NGROK_AUTHTOKEN` is unset and the operator previously ran `ngrok config add-authtoken`
- **THEN** that token is used

#### Scenario: Error echoing the token
- **WHEN** ngrok rejects the token with a message containing it
- **THEN** the reason shown to the operator has the token masked

### Requirement: The tunnel reaches only the buzzer port
The tunnel SHALL always forward to `127.0.0.1` on the buzzer port, an address that no configuration or flag can change. `--tunnel-domain` or `NGROK_DOMAIN` SHALL request a fixed ngrok domain, so links survive a restart.

#### Scenario: Custom buzzer port
- **WHEN** the operator runs with `--buzzer-port 6001` and a token
- **THEN** the tunnel forwards to `127.0.0.1:6001`

#### Scenario: Static domain
- **WHEN** the operator sets `NGROK_DOMAIN` and restarts mid-game
- **THEN** previously copied links still work

### Requirement: Tunnel problems never stop the game
If the tunnel cannot be opened, or no authtoken is found, the game SHALL still start with local-only links, and the start-up banner SHALL say why and, without a token, where to get one.

#### Scenario: No token
- **WHEN** the operator runs `ceopardy serve --online` with no authtoken
- **THEN** the game starts and the banner says links are local only and links to the ngrok authtoken page

#### Scenario: ngrok fails
- **WHEN** ngrok refuses to open the tunnel
- **THEN** the game starts and the banner gives ngrok's reason

### Requirement: The buzzer URL is shown to the operator
The start-up banner SHALL print the buzzer URL and how it was obtained. The top drawer SHALL show the public URL when there is one, or a warning that links only work on this machine and how to fix it.

#### Scenario: Tunnel open
- **WHEN** the tunnel opens
- **THEN** the banner and the drawer show its public URL

#### Scenario: Local only
- **WHEN** there is no public URL
- **THEN** the drawer warns that links only work on this machine and suggests setting `NGROK_AUTHTOKEN` and restarting

### Requirement: Development server follows the same rules
`make run` SHALL enable online mode with `CEOPARDY_ONLINE`, take a manual public URL from `CEOPARDY_BUZZER_URL`, and otherwise open a tunnel whenever an authtoken is available unless `CEOPARDY_TUNNEL=0`. With auto-reload, the buzzer listener and tunnel SHALL start once, in the serving process only.

#### Scenario: Local dev links
- **WHEN** a developer runs `CEOPARDY_ONLINE=1 CEOPARDY_BUZZER_URL=http://localhost:5173/buzzer.html make run`
- **THEN** links point at the Vite dev server and no tunnel is opened

#### Scenario: Auto-reload
- **WHEN** the server runs with `--debug --online`
- **THEN** it starts without an address-in-use error and opens a single tunnel
