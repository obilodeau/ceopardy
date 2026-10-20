# Plan: online mode — web buzzers for remote players

Issue: [#42](https://github.com/obilodeau/ceopardy/issues/42)
Date: 2026-10-04

## Context

Today a buzzer is a USB device that types `1`, `2` or `3`. The host page
catches the key (`HostView.vue:60-70`), selects the team, plays
`buzzerN` and locks. For an online event (`ceopardy serve --online`, #40) the
players are remote and have no keyboard plugged into the host machine.

Done means:

- each remote player opens a web page, likely through ngrok, that shows their
  **team name** and a **buzz button**;
- a web buzz has the same effect in the host view as a keypress does today;
- the race is **fair**: being close to the server does not mean always winning;
- a player **cannot load another team's buzzer**;
- **several players per team** work, and any one of them buzzing is the team
  buzzing;
- the page **exposes nothing** from the host or the viewer.

Three facts about the current code shape the design:

1. **Every route on `:5000` is a host route.** There is no auth
   (`__init__.py:70-79`), CORS is `*`, and `/api/v1/answer`, `/init`,
   `/finish` and `/question/select` (which returns the *answer*,
   `routes.py:415-420`) are all on the same server as the viewer. Tunnelling
   `:5000` would hand every player the host's controls.
2. **The buzzer lock lives in the host's browser.** `buzzersLocked` is a
   local `ref` in `HostView.vue:48`. It opens automatically on question
   select (`:91`) and when a team is marked wrong (`:131-142`). The server
   never knows whether buzzers are open, so it cannot judge a race.
3. **Nothing stops a team from buzzing again after a wrong answer.** Marking
   a team *Bad* re-opens the buzzers for everyone, the team that just missed
   included (`HostView.vue:131-142`). On the show, that team is locked out
   for the rest of the clue.

## Threat model

| Who | Has | Must not be able to |
| --- | --- | --- |
| Anyone on the internet | the tunnel hostname (assume public) | reach anything without a valid link; reach the host API or the viewer at all |
| A player | their own team's link | buzz as another team; learn another team's link; read questions, answers, scores or game state; drive the game |
| A player with a modified client | their link + devtools | win races they did not earn by more than a small, fixed, host-visible margin |

Out of scope: a player forwarding their own link to someone else (social, the
host can rotate it), bots that press on the cue (any buzzer can be botted; we
flag it, see *Fairness*), and the pre-existing exposure of `:5000` to
websites the host visits in the same browser (CORS `*`; unchanged here).

## Decisions

1. **A separate listener for players.** The buzzer runs on its own port
   (`127.0.0.1:5001`) as a bare `python-socketio` server — no Flask app, no
   blueprint, no SPA catch-all. Only **that port** is tunnelled.
   Isolation is structural: there is no code path from the tunnelled port to
   the host API, so a forgotten decorator cannot open one.
2. **One capability link per team.** A random token in the URL *fragment*
   identifies the team. The server binds the socket to that team at connect
   time; buzz messages never name a team.
3. **The server judges the race**, using reaction time measured from the
   buzzer page's own "open" cue, corrected for latency and bounded so a lying
   client gains little. Details below.
4. **The buzzer lock moves to the server**, in both modes, as a `State` row.
   Keypresses go through the same server path as web buzzes.
5. **Selecting a question still opens the buzzers, in both modes.** The
   operator reports that stream delay is negligible in practice, so players
   see the clue on the stream as their page lights up. No new step for the
   host.
6. **Links are per game.** They live in a new table, so they rotate with the
   database on a new game: last game's team 1 cannot buzz for this game's.
7. **A team marked wrong is locked out for the rest of the clue, in both
   modes.** The server enforces it for keypresses and web buzzes alike. On the
   host, that team's whole scoring panel turns red, so it is obvious who can
   no longer buzz.
8. **Keyboard buzzers keep working in online mode**, for hybrid events. They
   go through the same arbiter as web buzzes, so the two kinds don't
   conflict.
9. **Ceopardy opens the ngrok tunnel itself.** With an ngrok authtoken
   available, `ceopardy serve --online` opens the tunnel in-process through
   ngrok's Python SDK and fills in the public URL. There is no separate ngrok
   install, no second terminal, and no URL to paste. The tunnel can only ever
   point at the buzzer port. `--buzzer-url` remains for other tunnels
   (Cloudflare, Tailscale), and `--no-tunnel` turns it off.
10. **Copying a team's link is one click** on a clipboard icon next to that
    team's name in the top drawer. The host pastes it to that team privately.

### Rejected alternatives

- **Tunnel `:5000` and filter paths in middleware** (allow `/buzz/*`, deny the
  rest for requests carrying `X-Forwarded-For`). Deny-by-header is
  allow-by-default: any tunnel or proxy that doesn't add the header, or a
  route added later and missed in the list, exposes the host. The filter would
  also have to understand Socket.IO namespaces on the shared `/socket.io`
  path, since `/game` broadcasts carry question text.
- **Add authentication to the host API and tunnel `:5000`.** Worthwhile on its
  own (see `contrib/authentication-and-blueprint-api.patch`), but it is a much
  larger change, and it still puts the host UI on the internet behind one
  password. It does not replace (1); it would be defence in depth on top.
- **Leave the tunnel to the operator** (`ngrok http 5001` in a second
  terminal, then paste the URL into `--buzzer-url`). That is two extra steps
  and a copy-paste at the worst moment, just before the event. It stays
  supported through `--buzzer-url`, but it is no longer the default path.
- **Spawn the `ngrok` binary as a subprocess** and read its URL from the local
  API on `:4040`. That still needs the binary installed, a process to babysit
  and clean up, and a port-4040 clash if the operator already runs ngrok. The
  SDK needs none of those.
- **First message to arrive wins.** Rewards the player nearest the server.
- **Trust client timestamps.** Clocks differ and a client can lie freely.

## Design

### Two listeners

```
players ── https ──▶ ngrok edge ══ in-process SDK ══▶ 127.0.0.1:5001   buzzer server
                                                          │  GET /                → buzzer.html
                                                          │  GET /assets/<file>   → buzzer chunks only
                                                          │  /buzz-io  Socket.IO, namespace /buzz
                                                          │  anything else        → 404
                                                          ▼  (in-process call)
                                                        BuzzArbiter ──▶ award(tid) ──▶ Controller + emit on /game
host, viewer ───────────────────────────────────────────▶ 127.0.0.1:5000   Flask app (unchanged, never tunnelled)
```

Both run in the `ceopardy serve` process. The buzzer server is
`socketio.WSGIApp(sio, static_files=...)` from `python-socketio` (already a
dependency of Flask-SocketIO), served by `werkzeug.serving.make_server(...,
threaded=True)` in a daemon thread. Werkzeug's server sets `werkzeug.socket`,
which is what `simple-websocket` needs for WebSocket in threading mode, so no
new dependency is required.

**Static allow-list.** Vite builds a second entry, `buzzer.html`, with
`build.manifest: true`. At start-up the buzzer server reads
`dist/.vite/manifest.json` and maps `/` to `buzzer.html` plus every file in
that entry's closure (`file`, `css`, `imports`, `assets`, recursively). Host
and viewer chunks are not in the map, so they 404 through the tunnel. The
code is open source, so this is about keeping the surface minimal, not
secrecy.

**Response headers**, added by a small WSGI wrapper on every response:

```
Content-Security-Policy: default-src 'self'; connect-src 'self'; img-src 'self' data:;
                         frame-ancestors 'none'; base-uri 'none'; form-action 'none'
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Cache-Control: no-store
```

**Socket.IO server settings:**

- `async_mode="threading"`, `path="buzz-io"` (distinct from `/socket.io`, so
  the Vite dev proxy can route the two to different ports);
- `cors_allowed_origins=None` (same-origin). This works behind ngrok without
  configuration: engine.io also accepts the origin rebuilt from
  `X-Forwarded-Proto`/`X-Forwarded-Host` (`engineio/base_server.py:284-300`).
  Once the public URL is known (the tunnel's, or `--buzzer-url`), its origin
  is the allow-list instead;
- `max_http_buffer_size=1024`: no legitimate message is bigger than ~60 bytes;
- connect refused (`ConnectionRefusedError`) on a missing or unknown token,
  and over `BUZZER_MAX_PLAYERS_PER_TEAM` sockets for one team.

Bind to `127.0.0.1` only. With `--debug`, Werkzeug's reloader runs the module
twice; start the thread only when `WERKZEUG_RUN_MAIN == "true"` (or debug is
off), otherwise the second start fails with "address in use".

### The tunnel

**How deep the ngrok integration goes.** The ngrok-specific code is one small
module, `ceopardy/tunnel.py`, that runs once at start-up and hands back a
URL. Nothing else in the design knows about ngrok. The buzzer server only
needs *some* public HTTPS URL that forwards to `127.0.0.1:5001`, and
`--buzzer-url` accepts any tunnel's URL.

**The library.** [`ngrok`](https://pypi.org/project/ngrok/) on PyPI is
ngrok's official Python SDK (1.4.0, MIT or Apache-2.0). It embeds the agent
as a native extension, so it doesn't need the `ngrok` binary:

```python
listener = ngrok.forward(f"127.0.0.1:{port}", authtoken=token, domain=domain or None)
public_url = listener.url()  # "https://<name>.ngrok-free.app"
```

Without a valid token it fails fast with ngrok's own message (sign-up and
authtoken links, `ERR_NGROK_4018`), which `tunnel.py` passes through.

**It is a regular dependency, not an extra**, pinned like the others in
`pyproject.toml` and `requirements.txt`. The operator install is a pipx
install of a release wheel URL, and extras on a URL install
(`"ceopardy[ngrok] @ https://…whl"`) are exactly the step people get wrong.
The cost is an ~8 MB native wheel. Import it lazily inside `tunnel.py`, so a
game without `--online` never loads it, and a platform without a wheel only
loses the tunnel.

**Start-up, with `--online`:**

1. Start the buzzer server on `127.0.0.1:5001`.
2. Pick the public URL, first match wins:
   - `--buzzer-url` given: use it, open no tunnel (Cloudflare, Tailscale,
     self-run ngrok);
   - `--no-tunnel`: none (local testing; links point at `127.0.0.1:5001`);
   - otherwise, if an authtoken is found: `ngrok.forward(...)`;
   - otherwise: none, and the banner says how to get a token.
3. Store the result in `config["BUZZER_PUBLIC_URL"]` before `create_app()`, as
   `ONLINE_MODE` already is (`__main__.py:29-31`).
4. Print it in the banner:
   `Buzzers: https://quiet-owl.ngrok-free.app  (ngrok → 127.0.0.1:5001)`.

A tunnel failure never stops the game from starting. The host drawer shows the
same warning as the banner (see *Host view*).

**Finding the authtoken**, pure helper `tunnel.find_authtoken(env,
config_paths) -> str | None`, first match wins:

1. `NGROK_AUTHTOKEN` in the environment;
2. the ngrok agent's own config file, for operators who already ran
   `ngrok config add-authtoken`: `~/.config/ngrok/ngrok.yml` on Linux and
   `~/Library/Application Support/ngrok/ngrok.yml` on macOS. A line parser for
   `authtoken: <value>` handles both the v2 (top level) and v3
   (`agent:` block) layouts without adding a YAML dependency.

Not a CLI argument: a token on the command line shows up in `ps` and in shell
history. The token is never logged, printed or sent to any client.

**Stable links across restarts.** Tokens persist in the database, so after a
crash the old links still work, but only if the domain is the same.
`--tunnel-domain` (or `NGROK_DOMAIN`) passes `domain=` to ngrok. Free accounts
include one static domain, so the README recommends setting it once. Without
it, a restart may produce a new hostname. The host then just copies the links
again; the tokens are unchanged.

**What the tunnel can reach.** `tunnel.py` builds the forward address itself
from the buzzer port, as `127.0.0.1:<buzzer port>`, and takes no address from
config or the command line. A test pins that, so it can't be pointed at
`:5000`.

### Capability links

- New model `BuzzerLink(tid: str unique, token: str)`. A new table, not a
  column on `Team`: `db.create_all()` creates missing tables on an existing
  database but never alters existing ones, and the project has no migration
  tooling (`docs/todo-next-major.md`). `db_backup_and_create_new()` already
  starts an empty database, which gives the per-game rotation of decision 6.
- `token = secrets.token_urlsafe(16)` (128 bits), created on first request for
  each `tid`.
- Lookup with `hmac.compare_digest` against each team's token (a handful of
  teams), in a pure helper `utils.match_buzzer_token(token, links) -> tid |
  None`.
- The link is `<public-url>/#<token>`. A fragment is never sent over HTTP, so
  it does not appear in ngrok's traffic inspector, the server log, or a
  `Referer`. The page reads it, keeps it in `sessionStorage`, and removes it
  from the address bar with `history.replaceState`. A player sharing their own
  screen doesn't show it, and a reload in the same tab still works.
- The token travels once, in the Socket.IO `auth` payload (inside the
  CONNECT packet, never the query string). The server stores `tid` in the
  socket's session and puts the socket in room `tid`. `buzz` carries no team,
  so there is nothing to tamper with.
- **Rotate:** the host replaces a team's token. The server sends `revoked` to
  that team's room and disconnects it; the page says "This link is no longer
  valid — ask the host for a new one".
- The host gets links from `GET /api/v1/buzzers/links` on `:5000`. They are
  **not** in `/api/v1/state` and **not** on the `/game` namespace, because
  the viewer receives both, and the viewer is the tab being screen-shared.

### Fairness

**What the race is.** The starting gun is the buzzer page turning green, not
the stream. Stream delay is negligible in practice (decision 5), but it is
not measurable, whereas the page's cue reaches every player over the same
socket as their buzz, so its latency can be measured and taken out. On the
page:

```
reaction_client = performance.now() at press − performance.now() at "open" received
```

`performance.now()` is monotonic and needs no clock sync. The press is
`pointerdown` / `keydown` (Space, Enter), not `click`, which fires on release.

**What the server checks.** The server cannot trust `reaction_client`, but it
can bound it. For each socket it keeps recent round-trip times: an
application `ping` every 2 s, plus the ack of the `open` message itself, which
is a sample taken at race time. For a buzz:

```
E        = arrival time − time "open" was sent to this socket      (server clock)
rtt      = min(median(recent RTTs), BUZZER_RTT_CAP_MS)
r_server = E − rtt                                                   the server's own estimate
r        = clamp(max(reaction_client, r_server − BUZZER_JITTER_TOLERANCE_MS), 0, E)
```

- An honest client has `reaction_client ≈ r_server`, so `r = reaction_client`:
  precise, unaffected by jitter, and unaffected by distance. A player on a
  300 ms link who reacts in 210 ms beats a player on a 5 ms link who reacts
  in 260 ms.
- A client that claims 0 ms gets `r_server − tolerance`: it gains at most the
  tolerance (default 50 ms).
- A client that also slows its ping replies to inflate `rtt` gains at most up
  to `BUZZER_RTT_CAP_MS` (default 250 ms) minus its real RTT. That is the
  residual cheat. It is bounded, it needs a modified client, and it is visible
  to the host (next bullet).
- A reaction below `BUZZER_HUMAN_FLOOR_MS` (100 ms) is **flagged** to the host,
  not rejected: the host judges, as with any dispute.

**Collecting the race.** The first buzz of an epoch starts a window, then the
lowest `r` wins:

```
window = min(BUZZER_RTT_CAP_MS, max rtt among connected sockets) + tolerance
```

A later arrival can only have a lower `r` if its extra latency is bigger, and
the window covers the largest possible difference. With the defaults it is at
most 300 ms between the first press and the host seeing the result.

**Teams.** A team's `r` is the lowest across its players in the window. One
player is enough, and a slow teammate cannot hurt the team. Later buzzes from
the same team are ignored. Ties go to the earliest arrival.

**Epochs.** Each open increments an `epoch`, which is sent with `open` and
echoed in `buzz`. A buzz for a stale epoch, while closed, or after the
decision is ignored. This handles a press that crosses a re-open.

**Early presses.** Without a penalty, players hammer the button before the
cue and "reaction" becomes the hammer rate. As on the show, a press while
closed locks that **player** out for `BUZZER_EARLY_LOCKOUT_MS` (250 ms). The
page greys the button and says "Too early". The server records the press and,
if the next open falls inside the lockout, floors that player's `r` at the
remaining lockout. The client shows the lockout; the server enforces it.

**Local keyboard buzzers** (hybrid events) go through the same arbiter with
`rtt = 0` and `r = E`.

All of this lives in `ceopardy/buzzer.py`: a pure `BuzzArbiter` class with an
injectable `now()` clock and a `threading.Lock`, with no Flask or Socket.IO
imports, so it is unit-tested directly (AGENTS.md).

### What the buzzer page can see

This is the complete protocol on `/buzz`. Each payload is built by a small
function in `buzzer.py`, and a test pins its exact keys.

| Direction | Event | Payload | When |
| --- | --- | --- | --- |
| server → page | `team` | `{name}` | on connect; when the host renames that team |
| server → page | `open` | `{epoch}` (+ ack) | buzzers open |
| server → page | `closed` | `{won: true \| false \| null}` | decision, or host locks (`null`) |
| server → page | `excluded` | `{}` | buzzers open but this team already answered wrong (decision 7) |
| server → page | `ping` | `{n}` (+ ack) | every 2 s |
| server → page | `revoked` | `{}` | link rotated, just before disconnect |
| page → server | `buzz` | `{epoch, reaction_ms}` | press |

The page gets no scores, no other team names, no question or answer text, no
board, and no `/game` traffic. Team names are rendered as text, never `v-html`.

### Server-owned buzzer state

- `State("buzzers")`: `"open"` or `""`. Broadcast on `/game` as
  `buzzers {open, locked_out}`; included in `/api/v1/state` like every other
  state row.
- `POST /api/v1/buzzers {action: "open" | "close"}` (host): sets the state,
  and in online mode opens or closes an arbiter epoch, which emits
  `open`/`closed` on `/buzz`.
- `POST /api/v1/buzz {tid}` (host keypress): offline mode awards immediately
  if open; online mode submits a local buzz to the arbiter.
- `award(tid)` is the single place a buzz takes effect, whether it comes from
  a keypress or from the arbiter: `set_state("team", tid)`,
  `set_state("buzzers", "")`, then emit `team-select`, `sound buzzerN`,
  `buzzers {open: false}` and, for arbitrated races, `buzz-result` on `/game`;
  and `closed {won}` to each team room on `/buzz`. It runs inside the main
  app's `app_context()`, since the arbiter fires from a buzzer-server thread.

This also fixes a latent bug: two host windows today each keep their own lock
and could both award the same keypress.

### Locking out a team that answered wrong

- `State("locked-out")`: comma-separated tids barred from buzzing on the
  current clue. The name is 10 characters, which fits `State.name`. It is
  cleared on question select and deselect, and broadcast on `/game` as part
  of `buzzers {open, locked_out}`.
- `POST /api/v1/buzzers` takes an optional `locked_out: [tid]` next to
  `action`. The host sends the list of teams whose slider is on *Bad*:
  - when a team **joins** the list, the request also carries
    `action: "open"`. This is the rebound, as today, minus the team that
    missed;
  - when a team **leaves** it (the host corrects a slider), the list is
    updated without opening the buzzers;
  - when **every** team is on the list, the buzzers stay closed.

  This replaces today's deep watch, which re-opens on *any* slider change
  while some team is on *Bad*, including changes to other teams' sliders.
- A buzz from a locked-out team does nothing: `/api/v1/buzz` ignores it, and
  the arbiter drops it. On `open`, a locked-out team's buzzer pages get
  `excluded` instead and read "Your team already answered".
- The daily double is unaffected: it has no race, and no rebound.

**Red panel.** `TeamScoringPanel.vue` gets a `lockedOut` computed from the
store (`game.lockedOut.includes(tid)`), and the panel's `.black-box` gets a
`team-locked-out` class. In `main.css`, that class turns the frame and the
panel's background red, from a new `--ceopardy-wrong` token on `:root`. It
takes precedence over `.team-selected` (white frame), because the team that
just missed is usually still the selected one. The colour follows the server
state, not the local slider. Every host window agrees, and the host sees
exactly the teams the server is blocking.

**Reload.** The slider values are local to `HostView.vue` and reset to *No
Answer* on mount. `resetAnswers()` seeds `-1` for each locked-out team
instead, so a host reload mid-clue keeps the sliders, the red panels and the
lock-out consistent. Without this, the first slider change after a reload
would send an empty list and silently unlock those teams.

### Host view

- The lock icon in `HostControls.vue` reads `game.buzzersOpen` (new store
  getter over `ui_state.buzzers`) instead of a local `ref`; clicking it calls
  `POST /api/v1/buzzers`.
- `HostView.vue` keeps its triggers (select question, mark a team wrong,
  submit, deselect) but calls the API instead of flipping a `ref`.
- The keypress handler posts `/api/v1/buzz` and no longer plays the sound or
  selects the team itself; the `team-select` and `sound` broadcasts do.
- **Online mode, top drawer** (`HostHeaderDrawer.vue`): the team-name screen
  becomes the place to hand out links. See the next section.
- **Result line** in the bottom-right box after an arbitrated race:
  `Team 2 — 212 ms · Team 1 +48 ms · Team 3 +130 ms`, with ⚠ on reactions
  under the human floor. Data from `buzz-result` on `/game`. This is what the
  host uses to settle disputes and spot the residual cheat.

### Handing out links: the top drawer

Each team row today is `team1 [ Team name ………… ]`
(`HostHeaderDrawer.vue:54-66`). In online mode it gains icons right after the
name input, in the drawer's existing `form-icon form-click` style:

```
team1  [ The Hackers ……………… ]  📋  🔑  👤 3
team2  [ Root Beer ………………… ]  📋  🔑  👤 0
team3  [ Segfault ………………… ]  📋  🔑  👤 1
Buzzers: https://quiet-owl.ngrok-free.app
```

- **📋 Copy link** (`fa-regular fa-copy`), title "Copy The Hackers' buzzer
  link". One click puts `<public-url>/#<token>` on the clipboard. The icon turns
  into `fa-check` for 1.5 s as confirmation. Only the bare URL is copied: the
  host pastes it into that team's private channel (a DM or the team's
  breakout chat), never a shared one, since anyone with the link plays as that
  team.
- **🔑 New link** (`fa-solid fa-key`, not `fa-rotate`, which is already the
  drawer's *Save* icon), behind a `confirm()`: "Give The Hackers a new link?
  Their players will be disconnected until you send it." It rotates the
  token, and the 📋 icon copies the new link straight away.
- **👤 n** players connected, from `buzzer-presence {team1: 3, ...}` on
  `/game`. It turns green at ≥ 1, so the host can see at a glance which team
  hasn't joined yet.
- **Status line** under the rows, from the same response as the links:
  - a public URL: `Buzzers: https://…`;
  - no tunnel: a warning that links point at `127.0.0.1` and only work on this
    machine, plus the banner's one-line fix (set `NGROK_AUTHTOKEN` and
    restart).

The icons are `div`s like the *Save* icon, not buttons, so clicking them
never submits the team-name form. The token is never shown on screen, only
copied, in case the host shares the wrong window. The Clipboard API needs a
secure context, which `localhost` is. If the host UI is opened over plain HTTP
on a LAN address, `navigator.clipboard` is missing, and the icon falls back
to `window.prompt("Copy this link:", url)`.

Data: `GET /api/v1/buzzers/links` returns `{public_url, tunnel: "ngrok" |
"manual" | "none", links: {tid: url}}`. The drawer fetches it when it opens
and after a rotation. A rotation from another host window emits a bare
`buzzer-links` event on `/game`, which tells the other windows to fetch again.
The event carries no data, because the viewer receives it too.

### The buzzer page

A second Vite entry, not a route in the SPA, so the bundle carries no host,
viewer, router or Pinia code:

- `frontend/buzzer.html`, `frontend/src/buzzer/main.ts`,
  `frontend/src/buzzer/BuzzerApp.vue`, and its own `io("/buzz", {path:
  "/buzz-io", auth: {token}})`;
- one full-screen button with states: connecting, locked, **open**, buzzed
  (waiting for the decision), won, lost, too early, excluded, invalid link,
  revoked, reconnecting;
- `touch-action: manipulation` (no double-tap zoom delay), and the Screen Wake
  Lock API where available so a phone doesn't sleep between questions;
- no Font Awesome, no web fonts, no third-party anything (CSP `'self'`).

## Steps

Each step is one commit and leaves `make ci` green.

### 1. Server-owned buzzer lock (both modes)

- `routes.py`: `POST /api/v1/buzzers`, `POST /api/v1/buzz`, and an `award(tid)`
  helper. Seed `State("buzzers", "")` in `Controller._init()`.
- `types.ts`, `stores/game.ts`: `BuzzersEvent`, the `buzzers` key in
  `UiState`, the `buzzersOpen` getter, and the `buzzers` listener.
- `api.ts`: `setBuzzers(action)`, `buzz(tid)`.
- `HostView.vue`, `HostControls.vue`: drop the local `ref` and use the store
  and API as described above.

Offline behaviour must not change: keys 1–3, lock icon, auto-open on select,
re-open on a wrong answer (step 2 then narrows the re-open).

### 2. Lock out teams that answered wrong (both modes)

- `routes.py`: `locked_out` on `POST /api/v1/buzzers`, with `State("locked-out")`
  cleared in `question_select()` and `question_deselect()`. `/api/v1/buzz`
  ignores locked-out teams.
- A pure `utils.parse_locked_out(value, known_tids) -> list[str]` that
  validates the list against real tids, with tests.
- `types.ts`, `stores/game.ts`: `locked-out` in `UiState`, a `lockedOut`
  getter that splits it, and `locked_out` on `BuzzersEvent`.
- `HostView.vue`: replace the deep `answers` watch with the
  joined/left/all-wrong logic above, and seed `-1` in `resetAnswers()`.
- `TeamScoringPanel.vue` and `main.css`: the red panel.

This step is useful without any of the online work, and can ship on its own.

### 3. The arbiter

`ceopardy/buzzer.py`: `BuzzArbiter`, the payload builders, and the config keys
in `config.py`:

```python
"BUZZER_PORT": 5001,
"BUZZER_PUBLIC_URL": "",
"BUZZER_RTT_CAP_MS": 250,
"BUZZER_JITTER_TOLERANCE_MS": 50,
"BUZZER_EARLY_LOCKOUT_MS": 250,
"BUZZER_HUMAN_FLOOR_MS": 100,
"BUZZER_MAX_PLAYERS_PER_TEAM": 16,
```

`tests/test_buzzer.py`, with a fake clock:

- a far, faster player beats a near, slower one;
- a client claiming 0 ms gains at most the tolerance;
- an inflated RTT gains at most the cap;
- two players on one team: the team takes the lower `r` and counts once;
- stale epoch, closed and post-decision buzzes are ignored;
- an early press inside the lockout floors `r`;
- no decision before the window ends;
- a local buzz (no RTT samples) is judged on `E`, and races web buzzes
  correctly (decision 8);
- a locked-out team's buzzes are dropped, even when they are the fastest.

### 4. Buzzer links

- `model.py`: `BuzzerLink`. `utils.py`: `new_buzzer_token()` and
  `match_buzzer_token()`, with tests.
- `routes.py`: `GET /api/v1/buzzers/links` returns `{public_url, tunnel,
  links: {tid: url}}`, and `POST /api/v1/buzzers/links/<tid>` rotates and
  emits `buzzer-links`. The responses hold only URLs, and the endpoints exist
  only on `:5000`.

### 5. The buzzer server

- `ceopardy/buzzer_server.py`: `make_buzzer_wsgi(dist_dir, manifest, sio)`
  (static allow-list + headers), the `/buzz` namespace handlers (connect/auth,
  `buzz`, ping loop, presence), and `start_buzzer_server(port)`. It stores
  itself on `app.buzzer` so `routes.py` can push `team` renames and rotations,
  or finds `None` outside online mode.
- `__main__.py`: `--buzzer-port` and `--buzzer-url` on `serve`. Start the
  server only with `--online`.
- `run.py`: the same, from `CEOPARDY_ONLINE` and a new `CEOPARDY_BUZZER_URL`,
  with the reloader guard.
- `tests/test_buzzer_server.py`, with Werkzeug's test `Client` against
  `make_buzzer_wsgi` and a temporary manifest (no Flask app, no database):
  `/` returns 200 with the CSP header; `/api/v1/state`, `/host`, `/socket.io/`
  and a host chunk under `/assets/` return 404; a buzzer chunk returns 200.

### 6. Built-in ngrok tunnel

- `pyproject.toml`, `requirements.txt`: `ngrok==1.4.0`.
- `ceopardy/tunnel.py`: `find_authtoken(env, config_paths)`,
  `forward_addr(port)`, and `open_tunnel(port, domain) -> str | None`, which
  lazily imports `ngrok`, returns `listener.url()`, and turns any failure into
  `None` plus a logged reason.
- `__main__.py`: `--no-tunnel` and `--tunnel-domain` on `serve`, the
  URL-picking order from *The tunnel*, and the banner:
  - `Buzzers: https://quiet-owl.ngrok-free.app  (ngrok → 127.0.0.1:5001)`;
  - or, with no token: `Buzzers: http://127.0.0.1:5001/ (local only) — set
    NGROK_AUTHTOKEN to open a tunnel: https://dashboard.ngrok.com/get-started/your-authtoken`.
- `run.py`: the tunnel only when `CEOPARDY_TUNNEL=1`, so a plain
  `CEOPARDY_ONLINE=1 make run` never publishes a dev machine. Same reloader
  guard: a tunnel opened in the parent process would be orphaned.
- `tests/test_tunnel.py`, with no network or ngrok session:
  - `find_authtoken` prefers the environment;
  - it reads v2 and v3 config layouts and tolerates missing or unreadable
    files;
  - `forward_addr` is always `127.0.0.1:<buzzer port>`;
  - the URL-picking order: `--buzzer-url` beats the tunnel, and
    `--no-tunnel` gives none.

### 7. The buzzer page

- `vite.config.js`: `build.rollupOptions.input` for `index.html` and
  `buzzer.html`, `build.manifest: true`, and a dev proxy for `/buzz-io` →
  `127.0.0.1:5001` with `ws: true`.
- The page as described above. Confirm the built `buzzer.html` contains no
  inline script or style that the CSP would block.

### 8. Host UI

- `HostHeaderDrawer.vue`: the 📋 / 🔑 / 👤 icons on each team row and the
  status line, as in *Handing out links*. `api.ts`: `buzzerLinks()`,
  `rotateBuzzerLink(tid)`. `types.ts`: the response and the
  `buzzer-presence` / `buzzer-links` events.
- `HostView.vue`: the result line.

Question select keeps opening the buzzers in both modes (decision 5), so the
host's flow doesn't change.

### 9. Docs

- `README.md`, operators → *Online events*: a **Remote buzzers** subsection,
  written as a recipe:
  1. once: sign up at ngrok (free), then `export NGROK_AUTHTOKEN=...` in your
     shell profile, or run `ngrok config add-authtoken` if you already have
     the ngrok agent. Optionally claim your free static domain and set
     `NGROK_DOMAIN`, so links survive a restart;
  2. `ceopardy serve --online`;
  3. open the top drawer on the host, and click 📋 next to each team to copy
     its link. Send each link **only** to that team.

  Then: players click through ngrok's free-plan warning page once; the 👤
  counts show who has joined; and `--buzzer-url` for Cloudflare Tunnel or
  Tailscale Funnel instead, with **never tunnel port 5000** stated there.
- `README.md`, *Architecture*: the single-operator paragraph now names `:5001`
  as the one port designed to be exposed, and says that `--online` publishes
  it through ngrok when a token is set.
- `README.md`, developers: `CEOPARDY_ONLINE=1
  CEOPARDY_BUZZER_URL=http://localhost:5173/buzzer.html make run` for local
  work, `CEOPARDY_TUNNEL=1` for a real tunnel, and **never tunnel `:5173`**:
  Vite proxies `/api` to the host.

## Verification

Automated: `make ci`, which includes the arbiter, token, allow-list and
tunnel tests above.

Manual:

1. **Offline regression:** `make run`. Keys 1–3, the lock icon and auto-open
   on select behave as before. Two host windows stay in sync on the lock.
2. **Lock-out, offline:** select a clue, press `1`, and mark team 1 *Bad*.
   - Team 1's panel turns red in every host window, including over the white
     "selected" frame, and the buzzers re-open.
   - Pressing `1` does nothing; pressing `2` wins.
   - Mark team 2 *Bad* too, then team 3: with every team red, the buzzers stay
     closed.
   - Move team 1's slider back to *No Answer*: the red goes away, and the
     buzzers do not open.
   - Reload the host mid-clue: the sliders and red panels come back as they
     were.
   - Select the next clue: no panel is red.
   - On a daily double, nothing turns red.
3. **Online, local:** `CEOPARDY_ONLINE=1 make run`. Open the top drawer:
   each team row has 📋, 🔑 and 👤 0, and the status line warns that links are
   local only. 📋 turns into a check mark, and the clipboard holds a link
   ending in `#<token>`. Renaming a team doesn't change its link. Copy team 1's link into two
   browsers and team 2's into a third. Both team-1 pages show team 1's name.
   Any team-1 press wins for team 1; a teammate's later press is ignored.
   Mark team 1 *Bad*: both team-1 pages read "Your team already answered"
   while team 2 can buzz. Pressing `3` on the host keyboard races the web
   buzzers.
4. **Fairness:** throttle one browser (devtools, +300 ms latency). With
   players pressing on the same cue, the throttled player still wins when
   faster, and the result line shows the margins. A press before the cue shows
   "Too early" and loses the next race when the cue follows within 250 ms.
5. **Through the built-in tunnel:** `NGROK_AUTHTOKEN=… ceopardy serve
   --online`, and a phone on cellular.
   - The banner and the drawer's status line show the `ngrok-free.app` URL,
     and 📋 copies links on that host. The phone loads its link after ngrok's
     warning page, and that team's 👤 goes to 1.
   - With no token: the game still starts, and the banner and drawer explain
     how to get one.
   - With `--tunnel-domain`, restart the server: the links copied before the
     restart still work.
   - `/host`, `/api/v1/state`, `/api/v1/question/select`, `/socket.io/` and
     `/assets/<host chunk>` all 404 on the tunnel URL.
   - A wrong or missing token is refused. Swapping in another team's token is
     impossible, because the page never sees it.
   - The server log and ngrok's traffic inspector show no token in any
     request, and the authtoken is in neither the log nor the banner.
   - Rotate team 1's link: the open team-1 pages show "revoked"; the new link
     works.
   - The page's network panel shows only `/`, buzzer assets and `/buzz-io`,
     and frames carry only the events in the table above.
6. **Debug reloader:** `--debug --online` starts once, with no "address in
   use", and opens a single tunnel.
7. **Other tunnels:** `--buzzer-url https://<cloudflared URL>` with
   `cloudflared tunnel --url http://127.0.0.1:5001` opens no ngrok session,
   and 📋 copies links on the Cloudflare host.

## Risks and edge cases

- **Tuning.** Tolerance, RTT cap and window are guesses. An honest player whose
  RTT spikes by more than the tolerance mid-race gets clamped upward. The
  host's result line exposes the numbers, and the defaults live in `config.py`.
- **Mobile background tabs.** A locked phone or a backgrounded tab suspends
  the socket. The page shows "reconnecting" on resume, and the wake lock
  reduces how often it happens. The host's presence count shows who is
  actually connected.
- **Polling fallback.** A player stuck on long-polling has higher, noisier
  latency. Compensation covers it up to the cap. Prefer `websocket` first in
  the client's transports.
- **SQLite from a second thread.** `award()` runs from buzzer-server threads.
  The arbiter's lock serialises decisions, and each `award` runs in its own app
  context with Flask-SQLAlchemy's scoped session.
- **DoS through the tunnel.** Unauthenticated sockets are refused at connect,
  messages are capped at 1 KB, and each socket counts once per epoch. The
  Werkzeug threaded server is not built for a flood; ngrok's edge limits are
  the protection. An ngrok basic-auth or OAuth policy in front is optional
  defence in depth.
- **`connect-src 'self'` and `wss:`.** Current browsers treat `'self'` as
  covering same-host WebSockets. If an older Safari refuses, add the explicit
  `wss://<host>` from `--buzzer-url`.
- **Buzzer sounds beyond 3 teams.** Pre-existing (only `buzzer1-3.wav` ship),
  unchanged.
- **ngrok needs an account.** Even the free plan requires sign-up and an
  authtoken; no code can remove that step. The rest is automatic, and the
  banner links straight to the token page.
- **ngrok's free-plan warning page.** Browsers see a one-time "You are about to
  visit…" page that only a paid plan or a request header can skip, and a
  browser navigating to a link cannot set headers. The README tells players to
  expect it.
- **A new native dependency for everyone.** About 8 MB, with wheels for Linux,
  macOS and Windows. The lazy import keeps it from affecting games without
  `--online`. If it becomes a problem, moving it to an extra is a one-line
  change plus a README tweak.
- **The tunnel publishes a port as soon as the server starts.** That is the
  point of `--online` with a token set, and the only thing published is the
  token-gated buzzer port. An operator who used `--online` only for viewer
  sound, and has `NGROK_AUTHTOKEN` set for another reason, gets a tunnel they
  didn't ask for. It's harmless but surprising: the banner states it, and
  `--no-tunnel` turns it off.
- **ngrok session drops mid-game.** The SDK reconnects on its own. Players'
  pages show "reconnecting" and recover. With a static domain the URL doesn't
  change; without one, the host drawer shows the new URL and the links must
  be sent again.
- **Old DB backups contain old tokens.** Harmless, because tokens are only
  matched against the live database.
- **The lock-out changes live events too.** A team marked wrong could buzz
  again until now; after step 2 it can't. That is intended (decision 7), but
  operators used to the old behaviour should hear about it in the release
  notes. The host can always undo it by moving the slider back.
- **Lock-out follows the sliders, which are host-local.** Two host windows
  each have their own sliders, so the window that last changed one sets the
  list. That is the same last-writer-wins as every other host control today.
- **Auto-open and stream delay.** Decision 5 rests on the stream delay being
  negligible. If an event's stream lags noticeably, players see the page
  light up before the clue. The fix is a config switch to stop auto-opening,
  deferred until someone needs it.

## Deferred

- Auto-discover a separately run ngrok agent through its local API
  (`127.0.0.1:4040/api/tunnels`). The built-in tunnel makes this unnecessary
  for the common case.
- Set or change the public URL, or start or stop the tunnel, from the host UI.
- Put the tunnel behind ngrok basic auth or OAuth (`basic_auth=`,
  `oauth_provider=` in the SDK) as a second gate in front of the links. This
  costs turnkey-ness: players would need a password as well as a link.
- QR codes for the links in the host drawer.
- Per-player names on the buzzer page and in the result line.
- Per-IP rate limiting on the buzzer port.
- A config switch to stop auto-opening on question select, for events with
  noticeable stream delay.
- Authentication for the host API on `:5000`
  (`contrib/authentication-and-blueprint-api.patch`): independent of this
  work, and worth doing before anyone runs `:5000` beyond localhost.
