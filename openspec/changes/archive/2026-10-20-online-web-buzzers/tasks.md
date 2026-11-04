# Tasks

## 1. Server-owned buzzer lock (both modes)

- [x] 1.1 Add `POST /api/v1/buzzers` (open/close), `POST /api/v1/buzz` (keypress) and a single award path (select team, close, buzzer sound) guarded by a lock; question select opens, daily double and deselect close; verify keys 1–3, the lock icon and auto-open on select behave as before in `make run`
- [x] 1.2 Add the `buzzers` key to `UiState`, the `BuzzersEvent` listener and a `buzzersOpen` getter in `stores/game.ts`, and `setBuzzers()`/`buzz()` in `api.ts`; verify `make frontend-type-check` passes
- [x] 1.3 Drop the local lock `ref` from `HostView.vue`: the lock icon in `HostControls.vue` reads the store, the keypress handler posts `/api/v1/buzz` and no longer selects the team or plays the sound; verify two host windows stay in sync on the lock

## 2. Lock out teams that answered wrong (both modes)

- [x] 2.1 Accept `locked_out` on `POST /api/v1/buzzers`, store it in `State("locked-out")`, clear it on question select and deselect, keep buzzers closed when every team is locked out, and ignore locked-out keypresses; verify pressing a locked-out team's key does nothing
- [x] 2.2 Add `split_locked_out()` and `parse_locked_out()` to `utils.py`, validating against known tids; verify `tests/test_utils.py` covers order, duplicates, empty and bad input
- [x] 2.3 Add `locked-out` to `UiState`, a `lockedOut` getter, and `locked_out` on `BuzzersEvent`; replace the deep `answers` watch in `HostView.vue` with the joined/left logic, and seed `-1` for locked-out teams in `resetAnswers()`; verify a host reload mid-clue keeps sliders and lock-out
- [x] 2.4 Add the `team-locked-out` class to `TeamScoringPanel.vue` (not during a daily double) and the `--ceopardy-wrong` red in `main.css`, taking precedence over `.team-selected`; verify the missed team's panel turns red in every host window

## 3. The race arbiter

- [x] 3.1 Add `ceopardy/buzzer.py`: a Flask-free `BuzzArbiter` with an injectable clock (RTT samples, latency-bounded reactions, collection window, team best, epochs, early-press floor, local buzzes, lock-out, human-floor flag) and the `/buzz` payload builders
- [x] 3.2 Add the `BUZZER_*` config keys (port 5001, public URL, tunnel kind, RTT cap 250, tolerance 50, early lockout 250, human floor 100, 16 players per team) to `config.py`
- [x] 3.3 Add `tests/test_buzzer.py` with a fake clock: far faster player wins, 0 ms claim gains at most the tolerance, inflated RTT gains at most the cap, garbage reactions, teammates count once, ties, stale/closed/post-decision buzzes, window timing, early-press floor, local buzz racing web buzzes, locked-out team dropped, flagging, payload keys; verify `make test` passes

## 4. Buzzer links

- [x] 4.1 Add the `BuzzerLink` model and controller methods to get (creating missing) and rotate tokens; add `new_buzzer_token()`, `match_buzzer_token()` (constant time) and `buzzer_link()` (token in the fragment) to `utils.py`; verify the token tests in `tests/test_utils.py` pass
- [x] 4.2 Add `GET /api/v1/buzzers/links` (`public_url`, `tunnel`, `links`, `presence`) and `POST /api/v1/buzzers/links/<tid>` (rotate, revoke, emit bare `buzzer-links`) on `:5000` only, and exclude the links endpoint from CORS; verify `/api/v1/state` carries no link

## 5. The buzzer server

- [x] 5.1 Add `ceopardy/buzzer_server.py`: manifest-driven static allow-list, 503 when unbuilt, security headers on every response, origin check, and the `/buzz` namespace (token auth, per-team limit, `team`/`open`/`excluded`/`closed`/`ping`/`revoked`, presence); bind to `127.0.0.1` in daemon threads and expose it on `app.buzzer`
- [x] 5.2 Wire renames, open/close and rotation from `routes.py` to the buzzer server, and arbiter decisions back into the award path inside an app context
- [x] 5.3 Add `--buzzer-port` and `--buzzer-url` to `ceopardy serve` and `CEOPARDY_ONLINE`/`CEOPARDY_BUZZER_URL` to `run.py`, starting the server only in online mode and only in the reloader's serving process; verify `--debug --online` starts without "address in use"
- [x] 5.4 Add `tests/test_buzzer_server.py` against the WSGI app with a temporary manifest: `/` is 200 with the CSP header, buzzer chunks are 200, host routes, API, `/socket.io/`, host chunks, the manifest and `..` paths are 404, only GET/HEAD, unbuilt is 503, origin check cases; verify `make test` passes

## 6. Built-in ngrok tunnel

- [x] 6.1 Add `ngrok==1.4.0` to `pyproject.toml` and `requirements.txt`
- [x] 6.2 Add `ceopardy/tunnel.py`: `find_authtoken()` (env, then agent config v2/v3 layouts), `forward_addr()` fixed to `127.0.0.1:<buzzer port>`, `choose()`, a lazily imported `open_tunnel()` that masks the token in errors, and `setup()` that settles the public URL and returns the banner line
- [x] 6.3 Add `--no-tunnel` and `--tunnel-domain` (or `NGROK_DOMAIN`) to `ceopardy serve`, settle the URL before starting the buzzer server, and print the banner; verify a missing token or ngrok failure still starts the game
- [x] 6.4 Make `run.py` open the tunnel like `ceopardy serve` whenever a token is found, unless `CEOPARDY_BUZZER_URL` is set or `CEOPARDY_TUNNEL=0`, in the serving process only
- [x] 6.5 Add `tests/test_tunnel.py` with no network: env token wins, v2/v3 configs, missing or unreadable files, XDG paths, `forward_addr`, the choice order, `setup()` with a fake ngrok (success, failure, no token, manual URL); verify `make test` passes

## 7. The buzzer page

- [x] 7.1 Add `buzzer.html` as a second Vite input with `build.manifest: true`, and a dev proxy for `/buzz-io` to `127.0.0.1:5001` with `ws: true`
- [x] 7.2 Add `frontend/src/buzzer/main.ts` and `BuzzerApp.vue`: token from the fragment into `sessionStorage`, one button with all phases, reaction timing from `open`, early presses, wake lock, no third-party assets; verify the built `buzzer.html` has no inline script or style the CSP would block

## 8. Host UI

- [x] 8.1 Add the copy, new-link and presence icons and the status line to `HostHeaderDrawer.vue`, with `buzzerLinks()`/`rotateBuzzerLink()` in `api.ts`, the response and `buzzer-presence`/`buzzer-links`/`buzz-result` types, and store listeners; verify the clipboard holds a link ending in `#<token>`
- [x] 8.2 Add the result line to `HostView.vue`, flagged reactions marked, cleared on question show/hide; verify a throttled browser that reacts faster still wins and the margins appear

## 9. Docs and verification

- [x] 9.1 Add a *Remote buzzers* recipe to the README operators section (authtoken, `ceopardy serve --online`, copy links, ngrok warning page, `--buzzer-url` and `--no-tunnel`, never tunnel `:5000`)
- [x] 9.2 Name `:5001` as the one port designed to be exposed in the README architecture section, and document the dev workflow (`CEOPARDY_ONLINE`, `CEOPARDY_BUZZER_URL`, `CEOPARDY_TUNNEL=0`, never tunnel `:5173`)
- [x] 9.3 Run `make ci` green, and the manual checks: offline regression, lock-out offline, online locally with several browsers per team, fairness under throttling, the built-in tunnel from a phone on cellular (404s on host paths, no token in logs, rotation), and `--buzzer-url` with another tunnel
