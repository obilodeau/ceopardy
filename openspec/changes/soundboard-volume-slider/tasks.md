# Tasks

## 1. Shared throttle

- [ ] 1.1 Add `frontend/src/throttle.ts` exporting `throttle<T>(fn: (value: T) => void, ms: number)` with the wager slider's semantics: immediate call when idle, at most one call per `ms`, and the latest value delivered at the end of the window. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 1.2 Replace `scheduleWagerBroadcast` and its timer state in `TeamScoringPanel.vue` with `throttle(..., 100)` around `api.setWager`. Verify with `make run`: during a daily double, dragging the host's wager slider updates the viewer's wager live and the viewer ends on the value the slider stops on.

## 2. Server: volume state and relay

- [ ] 2.1 In `ceopardy/soundboard.py` add `DEFAULT_VOLUME = 85`, `parse_volume(value: object) -> int | None` (accepts in-range `int`/`float`, rounded; rejects `bool`, strings, `None`, out of range) and `volume_payload(volume: int) -> dict`. Add tests in `tests/test_soundboard.py` for valid values, `0`, `100`, `150`, `-1`, `"loud"`, `True` and `None`; `make test` passes.
- [ ] 2.2 In `ceopardy/guest/soundboard.py` keep the current volume on `SoundboardPage`, send `volume` after `sounds` on connect, and add `on_volume`: per-connection `PlayLimiter(rate=20)`, ignore invalid values, store the value, relay it, and emit `volume` to the other soundboard pages with `skip_sid`. Change the relay to `relay(action, sound_id, volume)` and pass the current volume on `play`. Update `ceopardy/api/routes.py::relay_soundboard` to put `volume` on `play` payloads and emit `{action: "volume", volume}`, and update the `SoundboardPage` wiring in `ceopardy/__init__.py` if its signature changes.
- [ ] 2.3 Update `tests/test_guest_server.py`: the connect test now expects `sounds` then `volume` 85; add tests that a valid volume is relayed and sent to other pages but not the sender, that a later connection receives the new value, that a play carries the current volume, that invalid volumes and volumes from an unconnected sid are ignored, and that a 21st volume within a second is dropped. `make test` passes.

## 3. Viewer playback

- [ ] 3.1 In `frontend/src/composables/useSound.ts` add a module-level soundboard volume (default 0.85), `setSoundboardVolume(percent: number)` that updates every playing soundboard sound, and a `percent` argument to `playSoundboard` applied before `play()`. Leave `play` and the thinking music untouched.
- [ ] 3.2 In `frontend/src/types.ts` add `volume` to the `play` variant of `SoundboardEvent` and a `{ action: "volume"; volume: number }` variant; route it in the `soundboard` handler in `frontend/src/stores/game.ts`. `make frontend-type-check` passes.

## 4. Soundboard page slider

- [ ] 4.1 In `frontend/src/soundboard/SoundboardApp.vue` add a labelled 0–100 range input with the percent shown, in the controls row next to Stop all (Stop all gives up width; Refresh stays last; the row wraps on narrow screens), disabled when not connected. It starts at 85, follows `volume` messages from the server, and emits `volume` through `throttle(..., 100)` on input. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 4.2 Add one sentence on the volume slider to the Soundboard subsection of `README.md` (it sets the volume of soundboard sounds on the viewer, not the game's sounds, starting at 85 %). Verify it matches the UI.

## 5. Integration

- [ ] 5.1 Verify in browsers with `CEOPARDY_ONLINE=1 CEOPARDY_BUZZER_URL=http://localhost:5173/buzzer.html make run`, two soundboard pages and a viewer with sound enabled. Check that:
  - Both sliders start at 85 %, and moving one moves the other.
  - Dragging while a long sound plays changes its loudness live, and 0 % silences it.
  - A buzzer or the thinking music is not affected by the slider.
  - After reloading the viewer, the next press plays at the slider's volume.
  - The browser's network panel shows roughly 10 or fewer `volume` frames per second during a drag.
- [ ] 5.2 Run `make format` and `make ci`; everything passes.
