# Design

## Context

A soundboard press travels: soundboard page → `play` on the guest server's
`/soundboard` namespace → `SoundboardPage.on_play` → `relay("play", id)` →
`routes.relay_soundboard` → `soundboard` broadcast on `/game` → the viewer's
store → `useSound().playSoundboard(url)`. Stop all takes the same path with
`relay("stop", None)`. Viewer-side soundboard audio lives in `useSound.ts`'s
`soundboardAudio` list, kept apart from the thinking music.

The daily-double wager slider in `TeamScoringPanel.vue` already throttles its
broadcasts with a hand-rolled leading-edge + trailing-edge timer (100 ms). The
issue asks for the same limit on the new slider and for that code to be shared.

## Goals / Non-Goals

**Goals:**

- One volume for all soundboard sounds, applied live on the viewer.
- Reuse the existing relay path; no new endpoint, no new namespace.
- One throttle implementation for both sliders.

**Non-Goals:**

- Per-sound volume, or a volume control for game cues or the thinking music.
- Persisting the volume across server restarts.
- A volume control on the host page.

## Decisions

**The guest server owns the volume.** `SoundboardPage` holds the current value
(starting at `DEFAULT_VOLUME = 85`) under its existing lock. It already knows
every soundboard connection, so it can send the value on connect and fan out
changes to the other pages with `skip_sid`. Storing it in the game database via
`Controller.set_state` was considered; it would survive restarts, but the
relay runs from guest threads and the spec only asks for a fresh 85 % on start,
so the extra write per slider step is not worth it.

**Volume rides on the existing `soundboard` broadcast.** The relay becomes
`relay(action, sound_id, volume)`. `relay_soundboard` emits
`{action: "play", url, volume}` for a press and `{action: "volume", volume}` for
a slider change; `stop` is unchanged. Putting the volume on every play is what
makes a reloaded viewer correct without adding the volume to the game state,
which would also leak a guest-port detail into `/api/v1/state`.

**Wire format is an integer percent.** The page sends `volume` with
`{volume: <0–100>}`. `soundboard.parse_volume(value) -> int | None` accepts an
`int` or `float` in range (rounded), and rejects `bool`, strings, `None` and
out-of-range numbers. The viewer divides by 100 for `HTMLAudioElement.volume`.
`soundboard.volume_payload(volume)` builds the `{volume}` message pages receive,
next to `sounds_payload`.

**Server-side bound reuses `PlayLimiter`.** Each soundboard connection gets a
second limiter, `PlayLimiter(rate=20)`, for volume changes. Twenty per second
is twice what a throttled page sends, so an honest page never hits it.

**Viewer applies volume in `useSound`.** A module-level `soundboardVolume`
(0–1) is set by `setSoundboardVolume(percent)`, which also updates every element
in `soundboardAudio`. `playSoundboard(url, percent)` sets the volume on the new
element before `play()`. The store's `soundboard` handler routes the new
`volume` action; `SoundboardEvent` in `types.ts` gains that variant and the
`volume` field on `play`.

**Shared throttle lives in `frontend/src/throttle.ts`.** It exports
`throttle<T>(fn: (value: T) => void, ms: number): (value: T) => void` with the
wager slider's exact semantics: call immediately when idle, then at most once
per `ms`, always delivering the latest value at the end of the window.
`TeamScoringPanel.vue` replaces `scheduleWagerBroadcast` with
`throttle((v: number) => api.setWager(v).catch(() => {}), 100)`. The soundboard
page uses the same helper at 100 ms to emit `volume`. A composable was
considered, but there is no reactive state or lifecycle to manage, so a plain
function fits better, the same way `api.ts` and `socket.ts` sit at the top of
`src/`.

**Slider UI.** A labelled `<input type="range" min="0" max="100" step="1">`
with the current percent shown next to it, disabled while not connected. It sits
in the controls row next to Stop all, taking space from that button, which no
longer needs the whole row width; Refresh stays at the end. On narrow screens
the row wraps so the slider keeps a usable width. A `volume` message from the
server sets the slider's value.

## Risks / Trade-offs

- [Two operators drag at once and fight] → Last write wins and each page
  follows the other; the cap of four pages keeps this a corner case.
- [A remote `volume` message arrives mid-drag and makes the thumb jump] → The
  server skips the sender, so only another operator's change can do this.
- [Volume resets to 85 % if the server restarts mid-show] → Accepted in the
  spec; the operator sees 85 % on reconnect and can move it again.
- [iOS and iPadOS Safari ignore `HTMLMediaElement.volume`, so a viewer tab
  on those devices always plays at full volume] → Accepted: the viewer is a
  desktop tab being screen-shared, and only the soundboard page, which merely
  sends the value, is expected on a phone. If an iOS viewer is ever needed,
  route the soundboard elements through a Web Audio `GainNode`, whose context
  is resumed in the enable-sound click.
- [Refactoring the wager throttle changes its behavior] → The helper keeps the
  same leading + trailing semantics and interval; covered by a manual check of
  the viewer's live wager during a daily double.
