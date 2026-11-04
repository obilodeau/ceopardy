# Tasks

## 1. Back-end: online mode flag

- [x] 1.1 Add `ONLINE_MODE: False` to `ceopardy/config.py` and whitelist it in `_public_config()`; verify `/api/v1/state` reports `config.ONLINE_MODE`
- [x] 1.2 Add `--online` to `ceopardy serve`, set `config["ONLINE_MODE"]` before `create_app()`, and print an "Online: ON" banner line; verify with `ceopardy serve --online`
- [x] 1.3 Read `CEOPARDY_ONLINE` in `run.py` for `make run`; verify `CEOPARDY_ONLINE=1 make run` reports online mode

## 2. Back-end: sound endpoint and registry

- [x] 2.1 Add `SoundProblem`, the `SOUND_FILES` registry, `list_sounds()` and `validate_sound_request()` to `ceopardy/utils.py`; verify with new pytest cases for accepted pairs, rejected names (`buzzer4`, paths, wrong case) and rejected actions
- [x] 2.2 Add `POST /api/v1/sound`: validate, persist the `thinking` state for the waiting music, emit `sound` on `/game`, answer 400 on invalid input; verify with `make test` and a manual request
- [x] 2.3 Serve the registry as `sounds` in `/api/v1/state`; verify with pytest that every listed sound is under `/static/sounds/` and accepted by the validator

## 3. Front-end: shared audio layer

- [x] 3.1 Create `frontend/src/composables/useSound.ts` with the audio-sink predicate (iframe guard, then mode vs. host/viewer), one-shot playback, looping waiting music and error swallowing; verify `make frontend-type-check`
- [x] 3.2 Add `onlineMode`, `isThinking` and `sounds` to the game store and types, handle the `sound` socket event (mirror `thinking` into state, play the rest); verify `make frontend-type-check`
- [x] 3.3 Watch `isThinking` in `App.vue` to start or stop the waiting music and stop it on unmount; verify a reloaded client resumes the music
- [x] 3.4 Add `api.sound(name, action)` and make the host send buzzer, daily-double, timeout and music cues through it instead of playing locally; drop the host's own sound map and unused preload loop; verify default mode still sounds on the host only

## 4. Front-end: viewer unlock

- [x] 4.1 Add `EnableSoundOverlay.vue` to the viewer, shown only in online mode, outside an iframe, until clicked; the click plays a muted inline clip and records the unlock in `sessionStorage`; verify it appears once per tab and not in the host preview
- [x] 4.2 Restyle the overlay as a neutral system notice rather than Jeopardy chrome; verify visually on the viewer
- [x] 4.3 Update the viewer's "the viewer is silent" comment to describe online mode

## 5. Docs and verification

- [x] 5.1 Document `ceopardy serve --online`, the enable-sound click and sharing the tab with audio in `README.md`, and `CEOPARDY_ONLINE=1 make run` in the developer section
- [x] 5.2 Manual two-window check: default mode sounds on the host only with no double play from the preview; `--online` sounds on the viewer only after one unlock click; waiting music loops and resumes after a viewer reload
- [x] 5.3 Run `make ci` and verify ruff, prettier, `vue-tsc` and pytest pass
