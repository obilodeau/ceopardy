# Design

## Context

See proposal.md for motivation and specs/online-soundboard/spec.md for the behavior.
What exists today:

- `BuzzerServer` (`ceopardy/buzzer_server.py`) is a bare python-socketio app on
  `127.0.0.1:5001`, the only port tunnelled through ngrok. It serves `/` (that is,
  `buzzer.html`) plus exactly the files the Vite manifest lists for that entry, adds
  strict security headers, and runs the `/buzz` namespace on Socket.IO path `buzz-io`.
- Team secrets live in the `BuzzerLink` table. `utils.match_buzzer_token` compares in
  constant time, and `utils.buzzer_link` puts the secret in the URL fragment. The host
  fetches links from `GET /api/v1/buzzers/links`, which is excluded from the dev CORS
  rule, and replaces one with `POST /api/v1/buzzers/links/<tid>`.
- Audio: `useSound.ts` decides which window makes noise (`isAudioSink`: the top-level
  viewer when online, never the host's embedded preview). The viewer's
  `EnableSoundOverlay` gets the click browsers require. `/api/v1/sound` relays only the
  fixed `SOUND_FILES` names.
- `game-media/` in the operator's directory is served at `/static/game-media/` by
  `send_from_directory`. `ceopardy init` creates it.

## Goals / Non-Goals

**Goals:**

- Reuse the buzzer server, tunnel, security headers and link pattern rather than add a
  port.
- Keep the soundboard secret and the team secrets in separate stores, so no lookup can
  confuse them.
- Put the folder listing, name resolution and rate limiting in a Flask- and
  Socket.IO-free module so they can be unit tested.

**Non-Goals:**

- Soundboard buttons in the host UI (decided: remote link only).
- Looping, volume, per-sound stop, or a now-playing display.
- Uploading sounds through the page. Files are put in `soundboard/` on the host
  machine.
- Telling the soundboard page whether the viewer is connected or has sound enabled.
- Restoring playing sounds after a viewer reload. They are one-shot, like the buzzer
  cues.

## Decisions

### A second entry on the same server, separated by namespace and secret

`soundboard.html` becomes a third Vite input. `allowed_files` builds the allow-list from
both entries' manifest closures: `/` for `buzzer.html` as today, and `/soundboard.html`.
Shared chunks such as Vue and socket.io-client are served once. The soundboard connects
to a new `/soundboard` namespace on the same `socketio.Server` and `buzz-io` path, so
the existing ngrok tunnel and Vite dev proxy carry it unchanged.

The namespaces have separate `connect` handlers. `/buzz` checks against team tokens,
and `/soundboard` checks against the single soundboard token, so a secret valid for one
is refused by the other. Neither handler registers events from the other.

*Alternative:* a separate port and tunnel. Rejected with the user: ngrok's free plan
gives one static domain, so a second URL would change on every restart.

### The secret gets its own table

`SoundboardLink(id, token)` holds one row. `create_all()` adds it to existing
databases, as it did for `BuzzerLink`.

*Rejected:* a `BuzzerLink` row with a pseudo-tid. `get_buzzer_tokens()` returns every
row, so the soundboard secret would become a valid team buzzer.
*Rejected:* a `State` row. `get_complete_state()` goes to the viewer in
`/api/v1/state`.

### The link replaces the page name in the public URL

`utils.soundboard_link(public_url, token)` swaps the last path segment of
`BUZZER_PUBLIC_URL` (or the local `:5001` default) for `soundboard.html`. The secret
goes in the fragment, as `buzzer_link` does. `https://x.ngrok-free.app/` becomes
`https://x.ngrok-free.app/soundboard.html#…`, and the dev URL
`http://localhost:5173/buzzer.html` becomes `http://localhost:5173/soundboard.html#…`,
which Vite serves.

### Folder listing and name resolution in `ceopardy/soundboard.py`

- `list_sounds(folder) -> list[Sound]`, where `Sound(id, label)` has the file name as
  `id` and the stem as `label`. It reads `os.scandir` on the folder only, keeps regular
  files with an allowed extension that don't start with `.`, sorts by name, and returns
  `[]` when the folder is missing.
- `resolve(folder, sound_id) -> str | None` returns the id only if it equals an entry of
  a fresh `list_sounds`. This is an exact match against the listing, not path
  sanitizing, so `../x` and absolute paths cannot match.
- `PlayLimiter(rate=5, per_s=1.0, now=time.monotonic)` is a per-connection sliding
  window with an injectable clock.
- Payload helpers (`sounds_payload`, `revoked_payload`) are the only place `/soundboard`
  messages are built, mirroring `buzzer.py`.

The folder is `config["BASE_DIR"] + "soundboard"`, next to `game-media/`. It is listed
on every connect and every `refresh`, which is cheap for a handful of files and needs no
file watcher.

### `/soundboard` protocol

- Server to page: `sounds {sounds: [{id, label}]}` on connect and after `refresh`, and
  `revoked {}` before the server disconnects a replaced link.
- Page to server: `play {id}`, `stop {}`, `refresh {}`.

On `play`, the server checks the limiter, resolves the id and calls back into the main
app. On `stop`, it calls back unconditionally, since stop is idempotent. Connections are
capped at 4, refused with `ConnectionRefusedError("full")`, like the per-team player
cap.

### Main app relays to the viewer on `/game`

`start_buzzer_server` passes `on_soundboard(action, sound_id)`, wrapped in an app
context like the other callbacks. It emits `soundboard {action: "play", url}` or
`soundboard {action: "stop"}` on `/game`, and `soundboard-presence {count}` when pages
connect or leave. The `url` is `/static/soundboard/<url-quoted id>`, served on `:5000`
by a new route using `send_from_directory`, beside `/static/game-media/`. The buzzer
port never serves audio. The existing `/sound` endpoint and `SOUND_FILES` are left
alone.

### Viewer playback

`useSound.ts` gains `playSoundboard(url)` and `stopSoundboard()`, gated by
`isAudioSink()` like everything else. They keep their own set of `HTMLAudioElement`s,
separate from `thinkingAudio`, so Stop all cannot touch the thinking music. Starting a
ninth sound stops and drops the oldest, and finished sounds remove themselves on
`ended`. The store adds a `soundboard` socket handler and `soundboardPresence`.

### Host controls

`GET /api/v1/soundboard/link` returns `{link, presence}`, and
`POST /api/v1/soundboard/link` replaces the secret, has `BuzzerServer` emit `revoked`
and disconnect `/soundboard` pages, and returns the new link. Both return 400 when not
online (`app.buzzer is None`), and both are added to the CORS exclusion regex next to
`buzzers/links`. In `HostHeaderDrawer.vue`, a "Soundboard" row under the teams reuses
the copy/key/presence icons. It is fetched on drawer open like the buzzer links and
re-fetched when `soundboard-links` is broadcast on `/game` with no data.

### The soundboard page

`frontend/soundboard.html`, `src/soundboard/main.ts` and `SoundboardApp.vue` make up
the page: a status line, a grid of buttons, Stop all and Refresh. Each button gives
brief "sent" feedback, because the operator hears the stream with a delay. The
fragment-to-`sessionStorage` token handling moves from `BuzzerApp.vue` into a shared
`src/links/token.ts` that takes the storage key, and both pages use it. The page loads
no fonts, icons or third-party code, and it adds no inline script or style that the CSP
would block.

## Risks / Trade-offs

- [The link leaks, and someone plays sounds on the stream] → The host replaces it from
  the drawer, which disconnects the holder at once. Requests are capped at 5 per second
  and 8 concurrent sounds on the viewer.
- [File names are visible to anyone with the link] → Only the names in `soundboard/`,
  which the operator chose to share. The same link already lets them play those sounds.
- [A large file starts late on the viewer] → Acceptable for short stingers. The README
  recommends short MP3/OGG files. Preloading is a possible follow-up.
- [Shared Vite chunks between `buzzer.html` and `soundboard.html`] → Both are public
  pages, and `allowed_files` still serves only their manifest closures. The existing
  test that host chunks return 404 keeps guarding the boundary.
- [Viewer not connected or sound not enabled, so presses go nowhere] → The operator
  hears nothing on the stream and tells the host. The existing enable-sound prompt is
  the fix.

## Migration Plan

`create_all()` adds the `soundboard_link` table on first start. `ceopardy init`
re-run in an existing game directory adds `soundboard/` and skips everything else.
Rolling back is a code revert.
