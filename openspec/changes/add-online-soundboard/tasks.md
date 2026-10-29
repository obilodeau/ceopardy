# Tasks

## 1. Pure rules

- [ ] 1.1 Create `ceopardy/soundboard.py` with `Sound`, `list_sounds(folder)`, `resolve(folder, sound_id)`, `PlayLimiter` (injectable clock) and the `/soundboard` payload helpers, all type-hinted and free of Flask and Socket.IO. Verify the module imports neither.
- [ ] 1.2 Add `tests/test_soundboard.py`. Listing keeps only the five extensions, skips dotfiles and subfolders, sorts by name, labels by stem, and returns `[]` for a missing folder. `resolve` accepts a listed name and rejects `../data/Questions.cp`, `/etc/passwd`, `sub/x.mp3`, a removed file and non-strings. The limiter allows 5 in a second and refuses the 6th until the window moves. `make test` passes.
- [ ] 1.3 Add `soundboard_link(public_url, token)` to `ceopardy/utils.py`, with cases in `tests/test_utils.py` for the ngrok root URL, the local `:5001` default, and the Vite `…/buzzer.html` URL. Check that the token is always in the fragment. `make test` passes.

## 2. Secret and folder

- [ ] 2.1 Add the `SoundboardLink(id, token)` model, and `get_soundboard_token()` (created on first call) and `rotate_soundboard_token()` to the controller. Verify that starting against an existing `ceopardy.db` adds the `soundboard_link` table and leaves the other tables intact, and that `get_buzzer_tokens()` never returns the soundboard secret.
- [ ] 2.2 Make `ceopardy init` create `soundboard/` the same way it creates `game-media/`, and add `/soundboard/` to `.gitignore`. Verify with `ceopardy init` in an empty temporary directory, then a second run that reports it as skipped.

## 3. Buzzer server

- [ ] 3.1 Generalize `allowed_files` to serve `/` from `buzzer.html` and `/soundboard.html` from its own manifest closure. Extend `tests/test_buzzer_server.py`: the fake manifest gains a soundboard entry, `/soundboard.html` and its chunk return 200 with the security headers, and `/static/soundboard/x.mp3`, `/soundboard/x.mp3` and host chunks return 404. `make test` passes.
- [ ] 3.2 Add the `/soundboard` namespace to `BuzzerServer`. Connect checks the soundboard token and caps connections at 4. It handles `play`, `stop` and `refresh` through `ceopardy/soundboard.py`, adds `revoke_soundboard()`, and reports presence. Constructor callbacks provide the token, the folder and `on_soundboard`.
- [ ] 3.3 Test the namespace with a recorder in place of `sio.emit`. A team token is refused on `/soundboard` and the soundboard token is refused on `/buzz`. Connect sends only `sounds`. An unlisted id or a 6th play within a second does not reach `on_soundboard`. `stop` always does, and revoke emits `revoked` then disconnects. `make test` passes.

## 4. Host API and relay

- [ ] 4.1 In `ceopardy/__init__.py`, add the `/static/soundboard/<path:filename>` route from the operator's `soundboard/` folder, and wire `token`, `folder`, `on_soundboard` and presence into `start_buzzer_server`. The relay emits `soundboard` and `soundboard-presence` on `/game`. Extend the CORS exclusion to `soundboard/link`.
- [ ] 4.2 Add `GET` and `POST /api/v1/soundboard/link` to `ceopardy/api/routes.py`, each returning 400 when not online. The POST rotates, revokes and emits `soundboard-links` with no data.
- [ ] 4.3 Verify with `curl` against `CEOPARDY_ONLINE=1 make run` that the link endpoint works online and returns 400 offline, rotation changes the token, `/api/v1/state` holds no soundboard secret, and `/static/soundboard/<file>` serves a file on `:5000` but not `:5001`.

## 5. Soundboard page

- [ ] 5.1 Move the fragment-to-`sessionStorage` token handling from `BuzzerApp.vue` into `frontend/src/links/token.ts`, parameterized by storage key, and use it from the buzzer page. Verify that the buzzer still connects from a link and after a reload.
- [ ] 5.2 Add `frontend/soundboard.html`, `src/soundboard/main.ts` and `SoundboardApp.vue`. The page shows a status line (connecting, invalid, full, revoked, no sounds), one button per sound with brief "sent" feedback, Stop all and Refresh. Register the entry in `vite.config.js`. `make frontend-lint` and `make frontend-type-check` pass.

## 6. Viewer playback and host drawer

- [ ] 6.1 Add `playSoundboard(url)` and `stopSoundboard()` to `useSound.ts`, gated by `isAudioSink()`, with their own set of `Audio` objects capped at 8 (the oldest is stopped) and cleanup on `ended`. Add the `soundboard` and `soundboard-presence` handlers and `soundboardPresence` to `stores/game.ts`, and the types to `types.ts`.
- [ ] 6.2 Add the API calls to `api.ts` and the Soundboard row (copy, replace, presence) to `HostHeaderDrawer.vue`, shown only when `game.onlineMode`. It is fetched on drawer open and when `soundboard-links` arrives.
- [ ] 6.3 Verify in browsers with `CEOPARDY_ONLINE=1 CEOPARDY_BUZZER_URL=http://localhost:5173/buzzer.html make run` and two files in `soundboard/`. Check that:
  - A press plays on the viewer only (not the host or its preview), two presses overlap, and Stop all leaves the thinking music on.
  - Nothing plays before the viewer's enable-sound click.
  - Replacing the link shows "no longer valid" on the page.
  - The host row counts connected pages.
  - The console shows no CSP violation on the built page at `:5001/soundboard.html`.

## 7. Documentation

- [ ] 7.1 In `README.md`, add a "Soundboard" subsection under the online sections. It covers putting short audio files in `soundboard/`, copying the link from the top drawer and sending it only to the sound operator, the key icon to replace it, and that sounds play on the shared viewer tab. Mention `soundboard/` next to `data/` and `game-media/` in the `ceopardy init` description. Verify that the steps match the UI.

## 8. Integration

- [ ] 8.1 With the built wheel (`make build`, `pipx install --force dist/ceopardy-*.whl`, then `ceopardy init` and `ceopardy serve --online` through ngrok), open the soundboard link from another device and play, overlap and stop sounds while the viewer tab is shared. Confirm that a team buzzer link opened at `/soundboard.html` is refused.
- [ ] 8.2 Run `make format` and `make ci`; everything passes.
