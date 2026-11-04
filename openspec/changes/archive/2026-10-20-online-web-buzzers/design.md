# Design

## Context

See proposal.md for motivation. Three facts about the code before this
change shaped the design:

1. **Every route on `:5000` is a host route.** There is no auth, CORS is `*`,
   and `/api/v1/answer`, `/init`, `/finish` and `/question/select` (which
   returns the *answer*) share a server with the viewer. Tunnelling `:5000`
   would hand every player the host's controls.
2. **The buzzer lock lived in the host's browser**, as a local `ref` in
   `HostView.vue`. It opened on question select and when a team was marked
   wrong. The server never knew whether buzzers were open, so it could not
   judge a race, and two host windows could both award one keypress.
3. **Nothing stopped a team from buzzing again after a wrong answer.** Marking
   a team *Bad* re-opened the buzzers for everyone, the team that missed
   included. On the show, that team is locked out for the rest of the clue.

### Threat model

| Who | Has | Must not be able to |
| --- | --- | --- |
| Anyone on the internet | the tunnel hostname (assume public) | reach anything without a valid link; reach the host API or the viewer at all |
| A player | their own team's link | buzz as another team; learn another team's link; read questions, answers, scores or game state; drive the game |
| A player with a modified client | their link + devtools | win races they did not earn by more than a small, fixed, host-visible margin |

Out of scope: a player forwarding their own link (social; the host can
rotate it), bots that press on the cue (any buzzer can be botted; we flag
it), and the existing exposure of `:5000` to websites the host visits in the
same browser (CORS `*`, unchanged except for the links endpoint).

## Goals / Non-Goals

**Goals:**

- Isolation that is structural: no code path from the tunnelled port to the
  host API, so a forgotten decorator cannot open one.
- Fairness that does not depend on distance to the server, with any cheat
  bounded and visible to the host.
- One buzz path for keyboard and web buzzers, so hybrid events work.
- No extra operator steps beyond having an ngrok authtoken.

**Non-Goals:**

- Authentication on the host API (`contrib/authentication-and-blueprint-api.patch`).
  Worth doing, independent of this.
- Per-player identity, QR codes, rate limiting, changing the tunnel from the
  host UI (see Deferred).

## Decisions

1. **A separate listener for players.** The buzzer runs on its own port
   (`127.0.0.1:5001`) as a bare `python-socketio` server: no Flask app, no
   blueprint, no SPA catch-all. Only that port is tunnelled.
2. **One capability link per team.** A random token in the URL fragment
   identifies the team. The server binds the socket to that team at connect
   time; buzz messages never name a team.
3. **The server judges the race**, using reaction time measured from the
   buzzer page's own "open" cue, corrected for latency and bounded so a lying
   client gains little.
4. **The buzzer lock moves to the server**, in both modes, as a `State` row.
   Keypresses go through the same server path as web buzzes.
5. **Selecting a question still opens the buzzers, in both modes.** The
   operator reports stream delay is negligible in practice, so players see
   the clue on the stream as their page lights up. No new host step.
6. **Links are per game.** They live in a new table, so they rotate with the
   database on a new game.
7. **A team marked wrong is locked out for the rest of the clue, in both
   modes**, enforced by the server for keypresses and web buzzes alike, and
   shown as a red scoring panel on the host.
8. **Keyboard buzzers keep working in online mode**, through the same arbiter
   as web buzzes.
9. **Ceopardy opens the ngrok tunnel itself** through ngrok's Python SDK when
   an authtoken is available. `--buzzer-url` remains for other tunnels;
   `--no-tunnel` turns it off.
10. **Copying a team's link is one click** on an icon next to that team's name
    in the top drawer.

### Rejected alternatives

- **Tunnel `:5000` and filter paths in middleware** (allow `/buzz/*`, deny
  requests carrying `X-Forwarded-For`). Deny-by-header is allow-by-default:
  a tunnel that doesn't add the header, or a route added later and missed,
  exposes the host. The filter would also have to understand Socket.IO
  namespaces on the shared `/socket.io` path, since `/game` carries question
  text.
- **Authenticate the host API and tunnel `:5000`.** A much larger change that
  still puts the host UI on the internet behind one password. Defence in
  depth on top of (1), not a replacement.
- **Leave the tunnel to the operator** (`ngrok http 5001` in a second
  terminal, paste the URL). Two extra steps and a copy-paste just before the
  event. Still supported through `--buzzer-url`.
- **Spawn the `ngrok` binary** and read its URL from `:4040`. Needs the binary
  installed, a process to babysit, and clashes with an operator's own ngrok.
- **First message to arrive wins.** Rewards the player nearest the server.
- **Trust client timestamps.** Clocks differ and a client can lie freely.

### Two listeners

```
players ── https ──▶ ngrok edge ══ in-process SDK ══▶ 127.0.0.1:5001   buzzer server
                                                          │  GET /                → buzzer.html
                                                          │  GET /assets/<file>   → buzzer chunks only
                                                          │  /buzz-io  Socket.IO, namespace /buzz
                                                          │  anything else        → 404
                                                          ▼  (in-process call)
                                                        arbiter ──▶ award ──▶ Controller + emit on /game
host, viewer ───────────────────────────────────────────▶ 127.0.0.1:5000   Flask app (never tunnelled)
```

Both run in the `ceopardy serve` process. The buzzer server is
`socketio.WSGIApp` from `python-socketio` (already a Flask-SocketIO
dependency), served by `werkzeug.serving.make_server(..., threaded=True)` in
a daemon thread. Werkzeug sets `werkzeug.socket`, which `simple-websocket`
needs for WebSocket in threading mode, so no new dependency is required.

**Static allow-list.** Vite builds a second entry, `buzzer.html`, with
`build.manifest: true`. At start-up the buzzer server reads
`dist/.vite/manifest.json` and maps `/` to `buzzer.html` plus every file in
that entry's closure (`file`, `css`, `imports`, `assets`, recursively). Exact
path lookup, no prefix matching. Host and viewer chunks are not in the map,
so they 404. The code is open source, so this is about minimal surface, not
secrecy. If the frontend isn't built, `/` returns 503 saying so.

**Response headers**, added by a WSGI wrapper on every response, 404s
included:

```
Content-Security-Policy: default-src 'self'; connect-src 'self'; img-src 'self' data:;
                         frame-ancestors 'none'; base-uri 'none'; form-action 'none'
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Cache-Control: no-store
```

**Socket.IO settings:** `async_mode="threading"`; `socketio_path="buzz-io"`,
distinct from `/socket.io` so the Vite dev proxy can route the two to
different ports; `max_http_buffer_size=1024` (no legitimate message exceeds
~60 bytes); connect refused on a missing or unknown token (`invalid link`)
and over the per-team player limit (`team full`). The origin check accepts
same-origin, including the origin rebuilt from
`X-Forwarded-Proto`/`X-Forwarded-Host` as engine.io does by default (so ngrok
needs no configuration), plus the public URL's origin (needed when the page
comes from the Vite dev server).

Bind to `127.0.0.1` only. Under `--debug`, Werkzeug's reloader runs the
module twice; the buzzer server and tunnel start only when
`WERKZEUG_RUN_MAIN == "true"` or debug is off, otherwise the second start
fails with "address in use" and a parent-process tunnel would be orphaned.

### The tunnel

All ngrok-specific code is one module that runs once at start-up and hands
back a URL. Nothing else knows about ngrok; the buzzer server needs only some
public HTTPS URL that forwards to its port.

**The library.** [`ngrok`](https://pypi.org/project/ngrok/), ngrok's official
Python SDK (1.4.0, MIT or Apache-2.0), embeds the agent as a native extension,
so no `ngrok` binary is needed: `ngrok.forward("127.0.0.1:<port>",
authtoken=..., domain=...)` returns a listener whose `url()` is the public
URL. Listeners are kept referenced for the life of the process.

**A regular dependency, not an extra.** The operator install is a pipx install
of a release wheel URL, and extras on a URL install are the step people get
wrong. The cost is an ~8 MB native wheel. It is imported lazily, so a game
without `--online` never loads it and a platform without a wheel only loses
the tunnel.

**Start-up with `--online`:**

1. Pick the public URL, first match wins: `--buzzer-url` (open no tunnel);
   `--no-tunnel` (none); an authtoken is found (open ngrok); otherwise none.
2. Store it in config before the buzzer server starts, along with how it was
   obtained (`ngrok`, `manual` or `none`).
3. Start the buzzer server. A bind failure exits with a hint to use
   `--buzzer-port`.
4. Print the banner, e.g. `Buzzers: https://quiet-owl.ngrok-free.app (ngrok
   -> http://127.0.0.1:5001/)`, or `... (local only; set NGROK_AUTHTOKEN to
   open a tunnel: https://dashboard.ngrok.com/get-started/your-authtoken)`, or
   `... (local only; ngrok failed: <reason>)`.

A tunnel failure never stops the game from starting.

**Finding the authtoken**, first match wins: `NGROK_AUTHTOKEN`; then the
ngrok agent's config file (`$XDG_CONFIG_HOME/ngrok/ngrok.yml` or
`~/.config/ngrok/ngrok.yml`, `~/Library/Application Support/ngrok/ngrok.yml`,
legacy `~/.ngrok2/ngrok.yml`). A line regex for `authtoken: <value>` handles
both v2 (top level) and v3 (`agent:` block) layouts without a YAML
dependency. Not a CLI argument: it would show in `ps` and shell history. The
token is never logged or printed; ngrok error messages that echo it are
masked before display.

**Stable links across restarts.** Tokens persist in the database, so after a
crash the old links work if the domain is the same. `--tunnel-domain` (or
`NGROK_DOMAIN`) passes `domain=` to ngrok. Free accounts include one static
domain. Without it, a restart may change the hostname; the host copies the
links again, tokens unchanged.

**What the tunnel can reach.** The forward address is built from the buzzer
port alone, as `127.0.0.1:<port>`, and takes no address from config or the
command line. A test pins it.

### Capability links

- A new `BuzzerLink(tid unique, token)` table, not a column on `Team`:
  `db.create_all()` creates missing tables on an existing database but never
  alters existing ones, and there is no migration tooling. A new game already
  starts an empty database, which gives per-game rotation.
- `secrets.token_urlsafe(16)` (128 bits), created on first request for each
  team.
- Lookup with `hmac.compare_digest` against every team's token (a handful).
- The link is `<public-url>/#<token>`. A fragment is never sent over HTTP, so
  it is absent from ngrok's inspector, the server log and `Referer`. The page
  moves it to `sessionStorage` and strips it with `history.replaceState`, so a
  player's own screen share doesn't show it and a reload still works. If
  storage is blocked, the token stays in the URL.
- The token travels once, in the Socket.IO `auth` payload (inside CONNECT,
  never the query string). The server binds the socket to its team and puts
  it in that team's room.
- **Rotate:** replaces the token, sends `revoked` to that team's sockets and
  disconnects them, and emits a bare `buzzer-links` on `/game` so other host
  windows refetch. The event carries no data because the viewer gets it too.
- The host gets links from `GET /api/v1/buzzers/links` on `:5000`, never from
  `/api/v1/state` or `/game`, which the viewer (the shared tab) receives. CORS
  is not enabled on that endpoint, so another site the host visits cannot
  read it. The response is `{public_url, tunnel, links: {tid: url},
  presence: {tid: n}}`; links fall back to `http://127.0.0.1:<port>/`.

### Fairness

**What the race is.** The starting gun is the buzzer page turning green, not
the stream. Stream delay is negligible in practice (decision 5) but not
measurable, whereas the page's cue reaches every player over the same socket
as their buzz, so its latency can be measured and removed. On the page:

```
reaction_client = performance.now() at press − performance.now() at "open" received
```

`performance.now()` is monotonic and needs no clock sync. The press is
`pointerdown` or `keydown` (Space, Enter), not `click`, which fires on
release.

**What the server checks.** Per socket it keeps the last 8 round-trip times:
an application `ping` every 2 s, plus the ack of `open`, a sample taken at
race time. For a buzz:

```
E        = arrival − time "open" was sent to this socket       (server clock)
rtt      = min(median(recent RTTs), RTT_CAP)    (RTT_CAP when no samples yet)
r_server = E − rtt
r        = clamp(max(reaction_client, r_server − TOLERANCE), 0, E)
r        = max(r, early-press floor)
```

- An honest client has `reaction_client ≈ r_server`, so `r = reaction_client`:
  precise and unaffected by distance. A player on a 300 ms link reacting in
  210 ms beats a player on a 5 ms link reacting in 260 ms.
- A client claiming 0 ms gets `r_server − tolerance`: it gains at most the
  tolerance (50 ms).
- A client that also slows its ping replies gains at most `RTT_CAP` (250 ms)
  minus its real RTT. That is the residual cheat: bounded, needs a modified
  client, visible to the host in the result line.
- A non-numeric, boolean or non-finite report is replaced by `r_server`.
- A reaction under the human floor (100 ms) is flagged, not rejected.

**Collecting the race.** The first buzz of an epoch starts a window, then the
lowest `r` wins:

```
window = min(RTT_CAP, max rtt among sockets with samples) + TOLERANCE
```

A later arrival can only have a lower `r` if its extra latency is larger, and
the window covers the largest possible difference. With the defaults, at
most 300 ms between the first press and the decision.

**Teams.** A team's `r` is the lowest across its players in the window; a slow
teammate cannot hurt the team. Ties go to the earliest arrival.

**Epochs.** Each open increments an epoch, sent with `open` and echoed in
`buzz`. A buzz for a stale epoch, while closed, or after the decision does not
count. Closing cancels a race in progress, and a decision that lands after
the host closed the buzzers is dropped.

**Early presses.** Without a penalty, players hammer the button and
"reaction" becomes the hammer rate. A press while closed is sent to the
server, which records it; the page shows "Too early" for 250 ms. If the next
`open` reaches that player within 250 ms of the press, their `r` is floored
at the remaining lockout. The client shows it; the server enforces it.

**Keyboard buzzers** in online mode enter the same arbiter with no latency
correction: `r` is the time from open to arrival.

The arbiter is a pure class with an injectable clock and a `threading.Lock`,
no Flask or Socket.IO imports, so it is unit-tested with a fake clock.

### Protocol on `/buzz`

The complete server-to-page protocol. Each payload has a builder, and a test
pins its exact keys.

| Direction | Event | Payload | When |
| --- | --- | --- | --- |
| server → page | `team` | `{name}` | on connect; when the host renames that team |
| server → page | `open` | `{epoch}` (+ ack) | buzzers open, or on connect while open |
| server → page | `closed` | `{won: true \| false \| null}` | decision, or host closes (`null`) |
| server → page | `excluded` | `{}` | buzzers open but this team is locked out |
| server → page | `ping` | `{n}` (+ ack) | every 2 s |
| server → page | `revoked` | `{}` | link rotated, just before disconnect |
| page → server | `buzz` | `{epoch, reaction_ms}` | press (also while closed, as an early press) |

Connect errors carry `invalid link` or `team full`. The page gets no scores,
other team names, question or answer text, board or `/game` traffic. Team
names are rendered as text, never `v-html`.

The host gets the race numbers on `/game` as `buzz-result {winner, entries:
[{tid, reaction_ms, suspicious}]}`, and presence as `buzzer-presence {tid:
n}` whenever a player connects or disconnects.

### Server-owned buzzer state

- `State("buzzers")`: `"open"` or `""` (a missing row reads as closed).
  Broadcast on `/game` as `buzzers {open, locked_out}` and included in
  `/api/v1/state`.
- `POST /api/v1/buzzers {action?: "open" | "close", locked_out?: [tid]}`.
  Either key may be omitted; no `action` keeps the current state. In online
  mode it also opens or closes an arbiter epoch, which emits `open`,
  `excluded` or `closed` on `/buzz`.
- `POST /api/v1/buzz {tid}` (host keypress): `ignored` while closed or locked
  out; offline, awarded at once; online, submitted to the arbiter (`pending`).
- Awarding is one function, for keypresses and races alike: set the selected
  team, close the buzzers (which sends `closed {won}` per page), emit
  `team-select`, `sound buzzerN` (when that sound exists) and, for races,
  `buzz-result`. The arbiter calls it from a buzzer-server thread inside its
  own app context. A module-level lock serialises opens, closes and awards so
  two buzzes cannot both see the buzzers open.
- Question select opens (clearing the lock-out); a daily double and a
  deselect close (clearing it).

### Locking out a team that answered wrong

- `State("locked-out")`: comma-separated tids (the name fits `State.name`'s
  10 characters). Cleared on question select and deselect, and broadcast in
  `buzzers {open, locked_out}`.
- The host sends the list of teams whose slider is on *Bad*:
  - a team **joins** the list: also `action: "open"`, the rebound minus the
    team that missed;
  - a team **leaves** it (the host corrects a slider): list only;
  - **every** team is on the list: the server keeps the buzzers closed.

  This replaces the old deep watch, which re-opened on *any* slider change
  while some team was on *Bad*. The host skips the request when its list
  already matches the server's, which avoids an echo after a reload.
- The list is validated against real tids; duplicates dropped, order kept.
- A locked-out team's buzz does nothing: the keypress endpoint ignores it and
  the arbiter drops it. On `open`, its pages get `excluded` and read "Your
  team already answered this one."
- **Red panel.** The team scoring panel gets `team-locked-out` from the
  store's `lockedOut` getter, turning the frame and inner boxes red from a
  new `--ceopardy-wrong` token. It is declared after `.team-selected` so red
  wins over the white frame. It follows server state, not the local slider,
  so every host window agrees. Suppressed during a daily double.
- **Reload.** Sliders are local and reset on mount; resetting seeds `-1` for
  each locked-out team, so a reload keeps sliders, red panels and lock-out
  consistent. Otherwise the first slider change after a reload would send an
  empty list and silently unlock those teams.

### Host view

- The lock icon reads `game.buzzersOpen` (a store getter over the state row)
  and calls `POST /api/v1/buzzers`.
- The keypress handler posts `/api/v1/buzz` and no longer selects the team or
  plays the sound; the `team-select` and `sound` broadcasts do.
- **Result line** in the bottom-right box after a race:
  `Team 2 212 ms · Team 1 +48 ms`, with a warning icon on flagged reactions.
  Cleared on `question-show` and `question-hide`. This is how the host
  settles disputes and spots the residual cheat.
- **Top drawer, online mode.** Each team row gains, after the name input:
  - **Copy link** (`fa-regular fa-copy`): copies `<public-url>/#<token>`; turns
    into `fa-check` for 1.5 s. Falls back to `window.prompt` where the
    Clipboard API is missing (host UI over plain HTTP on a LAN address).
  - **New link** (`fa-solid fa-key`, not `fa-rotate`, already the Save icon),
    behind a `confirm()`.
  - **Presence** (`fa-solid fa-user` + count), highlighted at ≥ 1.

  The icons are `div`s like Save, so clicking them never submits the
  team-name form. The token is never shown, only copied. A status line shows
  `Buzzers: <public url>`, or a warning that links only work on this machine
  with the fix (set `NGROK_AUTHTOKEN` and restart). Links are fetched when
  the drawer opens in online mode and after a `buzzer-links` event, and kept
  out of the store.

### The buzzer page

A second Vite entry, not a route in the SPA, so the bundle carries no host,
viewer, router or Pinia code: `frontend/buzzer.html`,
`frontend/src/buzzer/main.ts`, `frontend/src/buzzer/BuzzerApp.vue`, with
`io("/buzz", {path: "/buzz-io", auth: {token}, transports: ["websocket",
"polling"]})`.

- One full-screen button and a status line. Phases: connecting, reconnecting,
  invalid, full, revoked, locked, open, early, buzzed, won, lost, excluded.
- `touch-action: manipulation`; the Screen Wake Lock API where available,
  re-requested on visibility change; a short vibration on buzz.
- No Font Awesome, web fonts or third-party anything (CSP `'self'`).

In dev, Vite proxies `/buzz-io` to `127.0.0.1:5001` with `ws: true`, and
`CEOPARDY_BUZZER_URL=http://localhost:5173/buzzer.html` builds links on the
dev server. Never tunnel `:5173`: Vite proxies `/api` to the host.

### Divergences from the original plan

What was built differs from the plan (`docs/plans/2026-10-04-online-web-buzzers.md`) in these ways; the specs describe the built behaviour.

- **Dev tunnel.** The plan opened a tunnel from `make run` only with
  `CEOPARDY_TUNNEL=1`. It now follows `ceopardy serve`: a tunnel opens
  whenever an authtoken is found, unless `CEOPARDY_BUZZER_URL` is set or
  `CEOPARDY_TUNNEL=0`.
- **CORS on the links endpoint.** The plan left `:5000`'s CORS `*` untouched.
  The links endpoint is excluded from CORS so a site the host visits cannot
  read every team's token.
- **Links response** also carries `presence`, so the drawer shows counts on
  open; rotation returns the new link.
- **Socket origin check.** The public URL's origin is added to same-origin
  rather than replacing it.
- **Authtoken lookup** also honours `XDG_CONFIG_HOME` and the legacy
  `~/.ngrok2/ngrok.yml`; ngrok errors are masked of the token.
- **Start-up order.** The public URL is settled before the buzzer server
  starts, so the socket's origin check knows it. A bind failure on the buzzer
  port exits with a hint.
- **Unbuilt page** returns 503 with an explanation; only `GET`/`HEAD` are
  served.
- **No `State("buzzers")` seed** at game init; a missing row reads as closed.
- **Arbiter details** not in the plan: a socket with no RTT samples is
  credited the full RTT cap; the window counts only sockets with samples;
  malformed reactions fall back to the server estimate; a decision is
  dropped if the host closed the buzzers during the window.
- **Buzzer page**: an extra "team full" phase; "Too early" shows red rather
  than grey; the early press is reported to the server as a `buzz` for a
  stale epoch; vibration on buzz.
- **Result line** clears on the next question show or hide; formatted without
  the em dash.
- **Red panel** is suppressed during a daily double; a daily double also
  explicitly closes the buzzers and clears the lock-out.

## Risks / Trade-offs

- [Tuning: tolerance, RTT cap and window are guesses; an honest player whose
  RTT spikes past the tolerance mid-race is clamped upward] → the result line
  exposes the numbers; defaults are in config.
- [Mobile background tabs suspend the socket] → page shows "reconnecting" on
  resume; wake lock reduces it; presence shows who is actually connected.
- [Long-polling fallback has higher, noisier latency] → compensation covers it
  up to the cap; the client prefers `websocket`.
- [SQLite from a second thread: awards run from buzzer-server threads] → the
  buzz lock serialises decisions; each runs in its own app context with
  Flask-SQLAlchemy's scoped session.
- [DoS through the tunnel] → unauthenticated sockets refused at connect,
  messages capped at 1 KB, each team counts once per epoch. Werkzeug's server
  is not built for a flood; ngrok's edge limits are the protection.
- [`connect-src 'self'` and `wss:` on older Safari] → current browsers treat
  `'self'` as covering same-host WebSockets; add the explicit `wss://` host if
  one refuses.
- [Buzzer sounds exist only for 3 teams] → pre-existing; extra teams buzz
  silently.
- [ngrok needs an account and shows a free-plan warning page once] → README
  tells operators and players; the banner links to the token page.
- [A new ~8 MB native dependency for everyone] → lazy import; moving it to an
  extra is a one-line change if needed.
- [The tunnel publishes a port as soon as the server starts, even for an
  operator who used `--online` only for viewer sound] → only the token-gated
  buzzer port is published; the banner says so; `--no-tunnel` turns it off.
- [ngrok session drops mid-game] → the SDK reconnects; pages show
  "reconnecting"; with a static domain the URL is stable.
- [Old DB backups contain old tokens] → harmless; only the live database is
  matched.
- [The lock-out changes live events: a team marked wrong can no longer buzz
  again] → intended (decision 7); mention in release notes; the host can undo
  it by moving the slider back.
- [Lock-out follows host-local sliders; two host windows are last-writer-wins]
  → same as every other host control.
- [Auto-open assumes negligible stream delay] → a switch to stop auto-opening
  is deferred until needed.

## Migration Plan

No migration step. `db.create_all()` adds the `buzzer_link` table to an
existing database, and the new state rows are created on first write. The
lock-out applies to offline games as soon as they upgrade.

## Deferred

- Auto-discover a separately run ngrok agent through `127.0.0.1:4040/api/tunnels`.
- Set or change the public URL, or start or stop the tunnel, from the host UI.
- ngrok basic auth or OAuth as a second gate in front of the links (costs
  turnkey-ness: players would need a password too).
- QR codes for the links in the host drawer.
- Per-player names on the buzzer page and in the result line.
- Per-IP rate limiting on the buzzer port.
- A config switch to stop auto-opening on question select, for events with
  noticeable stream delay.
- Authentication for the host API on `:5000`.
