# Proposal

## Why

Online events (`ceopardy serve --online`) have remote players with no USB
buzzer plugged into the host machine ([#42](https://github.com/obilodeau/ceopardy/issues/42)).
They need a buzzer they can open in a browser, and the race has to be fair
without exposing the host's controls, which today all sit unauthenticated on
`:5000`.

## What Changes

- The buzzer lock moves from the host's browser to the server, in both modes.
  Keyboard buzzers go through the server, which awards the buzz.
- A team marked wrong is locked out for the rest of the clue, in both modes,
  and its scoring panel turns red on the host. Previously a wrong team could
  buzz again on the rebound.
- In online mode, each team gets a secret capability link to a buzzer page.
  Any number of players can share a team's link. The host copies, rotates and
  watches presence for links from the top drawer.
- The buzzer page is served from a separate listener on its own port
  (default `5001`) that serves only that page and the buzzer socket. It is
  the only port meant to be reachable from the internet.
- Ceopardy opens an ngrok tunnel to that port itself when an ngrok authtoken
  is available. `--buzzer-url` accepts any other tunnel; `--no-tunnel` turns
  it off. New `serve` flags: `--buzzer-port`, `--buzzer-url`, `--no-tunnel`,
  `--tunnel-domain`.
- The server judges web races on each player's reaction time, corrected for
  latency and bounded so a modified client gains little. The host sees a
  per-team result line after each race.
- New dependency: `ngrok` (official Python SDK), loaded only for online games.

## Capabilities

### New Capabilities

- `buzzers`: the server-owned buzzer lock, keyboard buzzers, when buzzers open
  and close, and the wrong-answer lock-out with its red panel, in both modes.
- `remote-buzzers`: the players' buzzer page, per-team links and rotation, the
  isolated player listener and what it exposes, presence, and how the public
  URL and tunnel are chosen.
- `buzzer-race`: how a web buzzer race is judged: latency compensation and its
  bounds, the collection window, teams, epochs, early presses, flagging, and
  the host's result line.

### Modified Capabilities

None.

## Impact

- Backend: new buzzer arbiter, buzzer server and tunnel modules; new
  `/api/v1/buzzers`, `/api/v1/buzz` and `/api/v1/buzzers/links` endpoints; new
  `buzzers` and `locked-out` state rows; a new `BuzzerLink` table (created on
  existing databases by `create_all()`, rotated with the database each game).
- CLI: new `serve` flags; `make run` honours `CEOPARDY_ONLINE`,
  `CEOPARDY_BUZZER_URL` and `CEOPARDY_TUNNEL=0`.
- Frontend: a second Vite entry (`buzzer.html`), Vite manifest enabled, a dev
  proxy for `/buzz-io`; host lock icon, keypress handling, sliders, red panel,
  top-drawer link controls and result line.
- Dependencies: `ngrok==1.4.0` (native wheel, about 8 MB).
- Behaviour change for live events: the team that missed can no longer buzz
  on the rebound.
- README: Remote buzzers section, architecture note on `:5001`, dev workflow.
