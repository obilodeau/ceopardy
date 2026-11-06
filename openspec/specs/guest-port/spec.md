# guest-port Specification

## Purpose
The one listener meant to be reachable from the internet in online games. It
serves guest pages, such as the players' buzzers and the remote soundboard, to
people who are not the host, and exposes nothing of the host or the viewer.

## Requirements

### Requirement: The guest port exists only in online mode
The guest port SHALL be opened only when the server runs in online mode. Offline, no guest port is opened and no tunnel is created.

#### Scenario: Offline
- **WHEN** the operator runs `ceopardy serve` without `--online`
- **THEN** nothing listens on the guest port and no tunnel is opened

### Requirement: Guests use a separate listener
Guest pages SHALL be served from their own listener bound to `127.0.0.1`, on port `5001` by default or the port given with `--guest-port`. If the port cannot be bound, the server SHALL exit with a message naming the port and suggesting `--guest-port`.

#### Scenario: Default port
- **WHEN** the operator runs `ceopardy serve --online`
- **THEN** the guest pages are served on `127.0.0.1:5001`

#### Scenario: Custom port
- **WHEN** the operator runs `ceopardy serve --online --guest-port 6001`
- **THEN** the guest pages are served on `127.0.0.1:6001`

#### Scenario: Port in use
- **WHEN** another process already holds the guest port
- **THEN** `ceopardy serve --online` exits with an error suggesting `--guest-port`

### Requirement: The guest port exposes only guest pages
The guest port SHALL answer only `GET` or `HEAD` of each guest page, the exact files those pages load, and the guest socket. Every other path or method SHALL return 404, including host and viewer routes, the host API, the game socket, host and viewer assets, sounds, game media and the build manifest.

#### Scenario: Host surface
- **WHEN** a client requests `/host`, `/api/v1/state`, `/api/v1/question/select`, `/socket.io/` or a host asset on the guest port
- **THEN** it receives 404

#### Scenario: Path tricks
- **WHEN** a client requests a guest page asset path with `..` segments pointing at another file
- **THEN** it receives 404

#### Scenario: Other methods
- **WHEN** a client sends a `POST` to `/` on the guest port
- **THEN** it receives 404

### Requirement: Unbuilt guest pages are reported
When the frontend has not been built, a request for `/` on the guest port SHALL return 503 with a message saying the guest pages have not been built.

#### Scenario: No build
- **WHEN** the guest pages have not been built and a client requests `/`
- **THEN** it receives 503 explaining that the pages must be built

### Requirement: Guest port responses are locked down
Every response from the guest port SHALL carry a Content-Security-Policy allowing only same-origin resources and connections and forbidding framing, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`. Guest pages SHALL load no third-party resources.

#### Scenario: Headers
- **WHEN** any path on the guest port is requested, including one that returns 404
- **THEN** the response carries the Content-Security-Policy and the other security headers

### Requirement: The guest socket accepts only known origins
The guest socket SHALL accept connections only from its own origin, including the origin a proxy reports through forwarded-protocol and forwarded-host headers, and from the origin of the configured public URL.

#### Scenario: Through a tunnel
- **WHEN** a guest loads a page through the tunnel and connects
- **THEN** the connection is accepted

#### Scenario: Foreign site
- **WHEN** a page on another origin tries to open the guest socket
- **THEN** the connection is refused

### Requirement: Choosing the public guest URL
At start-up in online mode, the public URL that guest links are built on SHALL be chosen in order: the `--guest-url` given (no tunnel opened); none with `--no-tunnel`; an ngrok tunnel if an authtoken is found; otherwise none. With no public URL, guest links point at the local guest port.

#### Scenario: Manual URL
- **WHEN** the operator passes `--guest-url https://example.trycloudflare.com`
- **THEN** no ngrok tunnel is opened and guest links are built on that URL

#### Scenario: No tunnel
- **WHEN** the operator passes `--no-tunnel` with an authtoken set
- **THEN** no tunnel is opened and guest links point at `http://127.0.0.1:5001/`

#### Scenario: Token found
- **WHEN** an ngrok authtoken is available and neither flag is given
- **THEN** a tunnel is opened and guest links are built on its URL

### Requirement: Finding the ngrok authtoken
The authtoken SHALL be taken from `NGROK_AUTHTOKEN` first, otherwise from the ngrok agent's own config file in its usual locations. It SHALL NOT be accepted on the command line, and SHALL NOT be logged, printed or sent to any client, including in an ngrok error message.

#### Scenario: Agent config
- **WHEN** `NGROK_AUTHTOKEN` is unset and the operator previously ran `ngrok config add-authtoken`
- **THEN** that token is used

#### Scenario: Error echoing the token
- **WHEN** ngrok rejects the token with a message containing it
- **THEN** the reason shown to the operator has the token masked

### Requirement: The tunnel reaches only the guest port
The tunnel SHALL always forward to `127.0.0.1` on the guest port, an address that no configuration or flag can change. `--tunnel-domain` or `NGROK_DOMAIN` SHALL request a fixed ngrok domain, so guest links survive a restart.

#### Scenario: Custom guest port
- **WHEN** the operator runs with `--guest-port 6001` and a token
- **THEN** the tunnel forwards to `127.0.0.1:6001`

#### Scenario: Static domain
- **WHEN** the operator sets `NGROK_DOMAIN` and restarts mid-game
- **THEN** previously copied guest links still work

### Requirement: Tunnel problems never stop the game
If the tunnel cannot be opened, or no authtoken is found, the game SHALL still start with local-only guest links, and the start-up banner SHALL say why and, without a token, where to get one.

#### Scenario: No token
- **WHEN** the operator runs `ceopardy serve --online` with no authtoken
- **THEN** the game starts and the banner says links are local only and links to the ngrok authtoken page

#### Scenario: ngrok fails
- **WHEN** ngrok refuses to open the tunnel
- **THEN** the game starts and the banner gives ngrok's reason

### Requirement: The guest URL is shown to the operator
The start-up banner SHALL print the guest pages' URL and how it was obtained. The host's top drawer SHALL NOT show the URL, since the host hands out complete links instead; when there is no public URL it SHALL warn that links only work on this machine and how to fix it.

#### Scenario: Tunnel open
- **WHEN** the tunnel opens
- **THEN** the banner shows its public URL and the drawer shows no URL or warning

#### Scenario: Local only
- **WHEN** there is no public URL
- **THEN** the drawer warns that links only work on this machine and suggests setting `NGROK_AUTHTOKEN` and restarting

### Requirement: Development server follows the same rules
`make run` SHALL enable online mode with `CEOPARDY_ONLINE`, take a manual public URL from `CEOPARDY_GUEST_URL`, and otherwise open a tunnel whenever an authtoken is available unless `CEOPARDY_TUNNEL=0`. With auto-reload, the guest listener and tunnel SHALL start once, in the serving process only.

#### Scenario: Local dev links
- **WHEN** a developer runs `CEOPARDY_ONLINE=1 CEOPARDY_GUEST_URL=http://localhost:5173/buzzer.html make run`
- **THEN** guest links point at the Vite dev server and no tunnel is opened

#### Scenario: Auto-reload
- **WHEN** the server runs with `--debug --online`
- **THEN** it starts without an address-in-use error and opens a single tunnel
