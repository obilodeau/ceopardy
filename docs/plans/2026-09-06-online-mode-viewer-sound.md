# Plan: online mode — play sounds on the viewer instead of the host

Issue: [#40](https://github.com/obilodeau/ceopardy/issues/40)
Date: 2026-09-06

## Context

When Ceopardy is run for an *online* event, the tab that gets screen-shared is
the **viewer**, not the host. Today every sound plays on the host machine
only — the crowd watching the stream hears nothing. The issue asks for an
option that routes the buzzers, daily double, timeout and waiting music to
the viewer via Socket.IO.

Today all audio lives in one place, `frontend/src/views/HostView.vue`
(`soundUrls` at L130-138, `playSound()` at L146-154, `toggleThinking()` at
L155-164). `ViewerView.vue:3-5` documents the viewer as deliberately silent.
Two of the four sounds the issue names — **timeout** and **thinking music** —
have no server round-trip at all today; they are pure host-local clicks, so
routing them anywhere requires new plumbing.

Decisions taken:

1. The option is a **CLI flag on `ceopardy serve`** plus a `config.py` key,
   exposed read-only to the front-end. Not a host UI toggle, not a DB row.
2. In online mode the **host goes silent**; the viewer plays. Normal mode
   keeps today's behaviour exactly.
3. The viewer gets a **one-time click-through "Enable sound" overlay** to
   satisfy browser autoplay policy.

Outcome: `ceopardy serve --online` and the shared viewer tab carries the
audio, with no change to the default local-projector workflow.

## Design

### The predicate

Every sound decision reduces to one function, so there is exactly one place
to reason about it:

```ts
// true if THIS window is the one that should make noise
function isAudioSink(game): boolean {
  if (window.self !== window.top) return false;   // host's embedded viewer iframe
  return game.onlineMode ? !game.isHost : game.isHost;
}
```

The iframe guard matters: `HostFooterDrawer.vue:125` embeds `<iframe src="/">`
so the host page *contains* a live viewer. Without the guard, online mode
would make the host loud instead of silent.

### Transport: one generic `sound` event

Add a single broadcast event rather than deriving sounds from the existing
`dailydouble` / `team-select` events. Reasons:

- `timeout` and `thinking` have no existing event to derive from, so a new
  channel is needed regardless — one channel for all five is simpler than a
  mixed model.
- Deriving buzzers from `team-select` would misfire: `team-select` also fires
  from the roulette and from `/api/v1/answer`, which must stay silent.
- An explicit event keeps "which sound" a host decision, matching how the
  operator actually drives the game.

Server → client, namespace `/game`, broadcast (there are no rooms):

```json
{"name": "buzzer2", "action": "play"}
```

`action` is `"play"` or `"stop"`.

Client → server stays REST, per the house rule at `routes.py:21-24`:

```
POST /api/v1/sound  {"name": "timeout", "action": "play"}
  -> validate name against a server-side allow-list
  -> app.socketio.emit("sound", {...}, namespace=GAME_NS)
  -> jsonify(result="success")
```

**Why the backend is involved at all.** A pure host→viewer Socket.IO design
is not possible without a server-side handler: `ceopardy/__init__.py:144-152`
registers only `connect` and `disconnect`, there is no catch-all, and
Flask-SocketIO drops client-emitted events it has no handler for rather than
relaying them. The minimum would be a ~6-line `@socketio.on("sound")` relay
(`emit(..., broadcast=True, include_self=False)`; supported in the pinned
Flask-SocketIO 5.6.1). That was weighed and rejected: it would be the first
client `socket.emit()` in the codebase, against the documented
client→server-is-REST rule at `routes.py:21-24`, and it carries no server
state, so a viewer reloaded mid-break would not resume the waiting music.
A browser-only `BroadcastChannel` variant was also rejected — it needs host
and viewer in the same browser on the same machine, which rules out a second
machine, a separate profile, or an OBS browser source.

The daily double keeps its current host-side call too — but see step 5: the
DD sound moves onto this channel so a second host window and the viewer both
get it, fixing the existing quirk where it fires off the REST response
(`HostView.vue:97`) rather than the broadcast.

### Waiting music state

Thinking music is the only sound with duration, so it needs a little state:

- It must **loop** (`audio.loop = true`). Today it doesn't — the "waiting
  music" plays through once and stops silently.
- Persist it as a `State` row via `Controller.set_state("thinking", "1"|"")`
  in the `/api/v1/sound` handler, and include it in `_full_state_payload()`
  (`routes.py:112-167`). A viewer that joins or reconnects mid-break then
  starts the music instead of sitting in silence. All the other sounds are
  fire-and-forget one-shots and store nothing.

## Steps

### 1. Backend: the flag

- `ceopardy/config.py` — add `"ONLINE_MODE": False` to the `config` dict.
- `ceopardy/__main__.py` — add `--online` to the `serve` subparser, copying
  the `--debug` pattern at L93-98. In `_cmd_serve()`, set
  `config["ONLINE_MODE"] = args.online` **before** `create_app()`; the dict is
  imported at module load by `ceopardy/__init__.py:41,56`, so ordering matters.
  Extend the startup banner ("Online mode: sound plays on the viewer").
- `ceopardy/api/routes.py` — add `"ONLINE_MODE"` to the `_public_config()`
  whitelist tuple (L57-65).

### 2. Backend: the endpoint

In `ceopardy/api/routes.py`, next to `slider()` (L545-555), following house
conventions (`_controller()` helper, `request.get_json(force=True,
silent=True) or {}`, `jsonify(result="failure", error=...), 400`, type hints
per AGENTS.md):

```python
SOUND_NAMES = frozenset({"buzzer1", ..., "timeout", "reveal", "thinking", "dailydouble"})

@api_bp.route("/sound", methods=["POST"])
def sound() -> ...:
```

Validate `name` against `SOUND_NAMES` and `action` against `{"play","stop"}`;
persist the thinking flag; emit `sound` on `GAME_NS`.

Also add `"thinking"` to the seeded state keys in `Controller._init()`
(`controller.py:62-69`) and surface it in `_full_state_payload()`.

### 3. Front-end: extract the audio layer

Create `frontend/src/composables/useSound.ts` — the first composable in the
project. It owns what is currently duplicated-in-waiting inside HostView:

- the `SoundName` union and the `soundUrls` map (moved verbatim from
  `HostView.vue:15-22,130-138`),
- `playSound(name)` / `startThinking()` / `stopThinking()` with
  `audio.loop = true` on the thinking handle,
- the `isAudioSink()` gate above, so **no caller** has to think about mode,
- an `unlock()` that primes a muted `Audio` on first gesture, plus an
  `audioUnlocked` ref backed by `sessionStorage`,
- an `onBeforeUnmount` stop for the thinking handle — today
  `thinkingAudio` is module-scope and keeps playing after navigating away
  (`HostView.vue` has no unmount hook).

Drop the dead `preloaded` loop (`HostView.vue:139-144`) — it is written and
never read; keep a real preload inside the composable instead, and let it
fail quietly (see risks: most sound files are gitignored).

### 4. Front-end: config + event wiring

- `frontend/src/types.ts` — add `ONLINE_MODE?: boolean` to `AppConfig`
  (L18-26) and a `SoundEvent { name: string; action: "play" | "stop" }`
  interface in the event block (L79-140).
- `frontend/src/stores/game.ts` — add an `onlineMode` getter alongside the
  other config getters (L91-117), and register `s.on("sound", ...)` inside
  `connectSocket()` (L146-245) delegating to the composable. Mirror the
  `thinking` state key in `applyServerState()` so a reconnecting viewer
  resumes the music.
- `frontend/src/api.ts` — add `playSound(name, action)` to the `api` object
  (L50-92), using the shared `request()` wrapper.

### 5. Front-end: host emits instead of playing

In `HostView.vue`, replace the four direct `playSound` call sites with
`api.playSound(...)` calls, and let the returning broadcast decide who makes
noise. The host keeps playing in normal mode purely through `isAudioSink()`
— no branching at the call sites:

- L76 `onKeyPress` → buzzer,
- L97 `onSelectQuestion` → dailydouble (now via the broadcast, so a second
  host window and the viewer both get it),
- L127 `playTimeout` → timeout,
- L155-164 `toggleThinking` → play/stop thinking, driven by the store's
  `thinking` state rather than a local handle.

Keep `reveal` in the registry but add **no** new trigger — wiring it is a
separate pending change (`.todo/plan-wire-reveal-sound.md`).

### 6. Front-end: the unlock overlay

New `frontend/src/components/EnableSoundOverlay.vue`, rendered from
`ViewerView.vue`. Shows only when `game.onlineMode && !audioUnlocked && not
in an iframe`. A click calls `unlock()`, sets `sessionStorage`, and the
overlay disappears for the rest of the session — so it never sits on the
crowd screen during play. Update the now-wrong "the viewer is silent"
comment at `ViewerView.vue:3-5`.

### 7. Docs

`README.md` — document `ceopardy serve --online` in the operators section,
per the AGENTS.md rule that a new flag ships with its README update.

## Verification

Manual, two windows (the real test — this is UI and audio):

1. `make run`, open `/host` and `/` side by side.
2. **Default mode:** buzzer keys 1-3, the clock icon, the music icon and a
   daily double all sound on the host; the viewer stays silent; the host's
   embedded viewer iframe does not double up.
3. Restart with `--online`. The viewer shows "Enable sound"; click it once.
4. Repeat step 2 — every sound now comes from the viewer, the host is
   silent, and the overlay does not come back.
5. Toggle the music on, reload the viewer: the music resumes there (state
   restored from `/api/v1/state`).
6. Navigate host → start screen while music plays: it stops.

Automated: `make ci` (ruff, prettier, `vue-tsc`, pytest) must pass. Worth a
pytest for the one new pure function — a `validate_sound_request(name,
action)` helper in `ceopardy/utils.py` that the route calls, keeping the test
free of Flask/DB context per AGENTS.md.

## Risks and edge cases

- **Missing sound files.** `.gitignore:33-37` excludes `*.mp3`/`*.wav` under
  `ceopardy/static/sounds/` except `buzzer*.wav`, so a fresh clone 404s on
  daily-double, reveal, thinking-music and timeout. All playback must keep
  swallowing errors; the preload must not throw.
- **buzzer4+.** Only three buzzer files exist while team count is dynamic
  (`HostView.vue:73`). Pre-existing; the server allow-list should not make it
  worse — cap the buzzer names at what exists and log rather than 400.
- **The host iframe** is the main correctness trap; the `window.top` guard is
  what makes "host goes silent" true.
- **No auth.** Adding `POST /api/v1/sound` widens an already unauthenticated
  API (`__init__.py:72`); it only plays sounds, but online mode is exactly
  the scenario where the server is more likely to be reachable. Worth a note
  in the README next to the existing reverse-proxy warning.
- **Latency.** Buzzer sound now costs a REST round-trip plus a broadcast.
  On localhost this is negligible; over a LAN it may be perceptible.
