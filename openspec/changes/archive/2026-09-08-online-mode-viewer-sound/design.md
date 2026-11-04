# Design

## Context

Before this change all audio lived in the host view: a local name-to-URL
map, a `playSound()` helper and a module-scope handle for the waiting music.
The viewer was documented as deliberately silent. Timeout and waiting music
had no server round-trip at all; they were host-local clicks, so routing them
anywhere needed new plumbing. The daily-double sound fired off the host's
REST response, so a second host window never heard it.

The host page embeds a live viewer in an iframe (the footer drawer preview),
so "the viewer" is not only the crowd-facing tab.

The house rule is that client-to-server traffic is REST and server-to-client
traffic is Socket.IO broadcasts on `/game` (no rooms). The back-end
registered only `connect` and `disconnect` handlers.

## Goals / Non-Goals

**Goals:**

- One switch, chosen when the server starts, that moves every sound to the
  viewer.
- Normal mode behaves exactly as before.
- One place that decides whether a window makes noise, so no call site
  branches on mode.

**Non-Goals:**

- A host UI toggle or a DB-stored setting for the mode.
- Wiring a trigger for the `reveal` sound. It stays in the registry; wiring
  it is a separate pending change.
- Authentication on the new endpoint.

## Decisions

### Mode is a CLI flag exposed read-only to clients

`ceopardy serve --online` sets `ONLINE_MODE` in the config dict, which
`_public_config()` whitelists into `/api/v1/state`. It must be set before
`create_app()` so the first state a client fetches already advertises it.
`run.py` reads `CEOPARDY_ONLINE` because `make run` takes no arguments.
Rejected: a host UI toggle or a `State` row. The mode is a property of the
event, not something to flip mid-game.

### In online mode the host goes silent

Playing on both would double the audio for an operator who is also
listening to the stream. The viewer is the only sink.

### The audio-sink predicate

Every sound decision goes through one client-side predicate:

- inside an iframe: never a sink (the host's embedded preview);
- otherwise: online mode → viewers are sinks; normal mode → hosts are sinks.

The iframe guard is the main correctness trap. Without it the embedded
preview would make the host loud in online mode, and would play everything
twice in normal mode.

### Transport: one generic `sound` broadcast fed by REST

The host calls `POST /api/v1/sound {name, action}`; the server validates it
and emits `sound {name, action}` on `/game` to every client. `action` is
`play` or `stop`.

Rejected alternatives:

- **Deriving sounds from existing events** (`dailydouble`, `team-select`).
  Timeout and waiting music have no event to derive from, so a new channel
  was needed regardless, and one channel for all sounds is simpler than a
  mixed model. `team-select` also fires from the roulette and from answer
  scoring, which must stay silent. An explicit event keeps "which sound" a
  host decision.
- **A Socket.IO relay** (`@socketio.on("sound")` re-emitting with
  `broadcast=True, include_self=False`). Flask-SocketIO drops client events
  with no handler, so a pure host-to-viewer emit is impossible without one.
  The relay would have been the first client `socket.emit()` in the codebase,
  against the REST rule, and it holds no server state, so a reloaded viewer
  could not resume the music.
- **BroadcastChannel** between tabs. Requires host and viewer in the same
  browser profile on the same machine, ruling out a second machine or an OBS
  browser source.

The daily-double sound moved onto this channel too, fixing the quirk where
only the host window that made the request heard it.

### Sound registry served by the back-end

A single `SOUND_FILES` map (logical name → file under
`ceopardy/static/sounds/`) in `ceopardy/utils.py` drives both endpoint
validation and, via a `sounds` map in `/api/v1/state`, client playback.
Adding a sound is a back-end-only edit. Names and filenames stay an explicit
map rather than a directory listing because several differ (`dailydouble`,
`thinking`). Rejected: keeping a second copy in TypeScript with a "keep in
sync" comment, which is what the first implementation did.

Validation is a pure `validate_sound_request()` helper raising
`SoundProblem`, so pytest covers it without a Flask or DB context.

### Waiting-music state

The waiting music is the only sound with duration, so it is the only one the
server remembers: the endpoint writes a `thinking` `State` row (`"1"` or
`""`), which reaches clients through the normal state payload. Clients
mirror the `sound` event for `thinking` into the store instead of playing it
directly, and an app-level watcher on that store flag starts or stops the
looping audio. That single path covers the toggle, a client joining
mid-break, and a reconnect. The host's music button sends `play` or `stop`
from the store flag rather than tracking a local audio handle. One-shot
sounds store nothing.

### Autoplay unlock

The viewer in online mode may never have been clicked, so browsers would
block its audio. A full-screen overlay asks for one click, which plays a
muted inline silent WAV (not a real sound file, since most are gitignored)
and records the unlock in `sessionStorage`. It is styled as a neutral
system notice, not Jeopardy chrome, because it is for the operator during
setup and must never sit on the crowd screen during play. The host needs no
overlay: the operator always clicks before the first sound.

## Divergences from the original plan

- The plan kept the sound list in the front-end composable, mirrored by a
  server allow-list. The registry moved to the back-end and is served in
  `/api/v1/state`.
- The plan suggested capping buzzer names and logging rather than returning
  400. Unknown names, including `buzzer4`, get a 400; teams beyond three
  simply have no buzzer sound.
- The plan seeded `thinking` in `Controller._init()`. It is not seeded;
  `set_state()` creates the row on first use, and a missing key reads as off.
- The plan kept a real preload in the composable. There is no preload; each
  cue creates its `Audio` on demand and swallows load errors.
- The plan put the waiting-music stop in a host-view unmount hook. The music
  is driven from `App.vue` and follows server state, so it stops when the
  host turns it off or the app unmounts, not on navigation between views.
- The plan named the client call `api.playSound`; it is `api.sound`.
- `CEOPARDY_ONLINE` for `make run` was added; the plan only covered the CLI
  flag.
- The plan's README note on the unauthenticated endpoint was not added; the
  existing "no authentication, put a reverse proxy in front" warning covers
  it.

## Risks / Trade-offs

- [Most sound files are gitignored for licensing, so a fresh clone 404s on
  all but the buzzers] → every playback path swallows load and play errors;
  unlock uses an inline clip.
- [Only three buzzer files exist while the team count is configurable] →
  pre-existing; extra teams get no buzzer sound.
- [The embedded preview could make noise] → the iframe guard in the sink
  predicate and on the overlay.
- [`POST /api/v1/sound` widens an unauthenticated API, and online mode is
  when the server is more likely to be reachable] → it only plays sounds from
  a fixed list; the README already warns against exposing the server without
  a reverse proxy.
- [Buzzer sound now costs a REST round-trip plus a broadcast] → negligible on
  localhost; may be perceptible over a LAN.
