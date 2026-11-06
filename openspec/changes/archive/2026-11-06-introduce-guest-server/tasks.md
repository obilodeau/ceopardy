# Tasks

## 1. Guest package

- [x] 1.1 Create `ceopardy/guest/__init__.py` with `GuestPage` and `ceopardy/guest/server.py` with `GuestServer`, moving the allow-list, static app, security headers and origin check from `buzzer_server.py`. The allow-list is built from the pages' URL-to-entry maps, and the 503 names the guest pages. Verify with `ruff check`.
- [x] 1.2 Move the `/buzz` namespace, arbiter and ping loop into `ceopardy/guest/buzzers.py` (`BuzzersPage`) and the `/soundboard` namespace into `ceopardy/guest/soundboard.py` (`SoundboardPage`). Delete `ceopardy/buzzer_server.py`. Verify that `git grep buzzer_server` finds only planning artifacts.
- [x] 1.3 Rename `tests/test_buzzer_server.py` to `tests/test_guest_server.py` and port every case to the new classes, keeping each assertion. Add a case where a `POST /` returns 404 and the 503 text names the guest pages. `make test` passes with at least as many tests as before.

## 2. Settings, flags and wiring

- [x] 2.1 Rename `BUZZER_PORT`, `BUZZER_PUBLIC_URL` and `BUZZER_TUNNEL` to `GUEST_*` in `config.py`, `tunnel.py`, `api/routes.py` and `tests/test_tunnel.py`. Replace `app.buzzer` with `app.guest` and route calls through `app.guest.buzzers` and `app.guest.soundboard`. `make test` passes.
- [x] 2.2 Rename `start_buzzer_server` to `start_guest_server`, the flags to `--guest-port` and `--guest-url`, `CEOPARDY_BUZZER_URL` to `CEOPARDY_GUEST_URL` in `run.py`, and the banner line to `Guest pages:`. Verify that `ceopardy serve --help` lists the new flags and `--buzzer-port` is rejected.
- [x] 2.3 Change the Socket.IO path to `guest-io` in the server, both pages and the Vite proxy, and remove the drawer's `Buzzers:` URL line, keeping the local-only warning. `make frontend-lint` and `make frontend-type-check` pass.

## 3. Documentation

- [x] 3.1 Update `README.md` (architecture, remote buzzers, soundboard, dev workflow) and code comments to say guest port, `--guest-url` and `CEOPARDY_GUEST_URL`. Verify that `git grep -i -E "buzzer.port|buzzer-url|buzzer-port|CEOPARDY_BUZZER_URL|buzz-io"` outside `openspec/` finds nothing.

## 4. Integration

- [x] 4.1 With `CEOPARDY_ONLINE=1 CEOPARDY_GUEST_URL=http://localhost:5173/buzzer.html make run`, check in a browser that a team link buzzes and reconnects after a reload, the soundboard plays on the viewer and its link can be replaced, and the drawer shows no URL line. On the built pages at `:5001`, check there are no CSP errors and that a host path returns 404.
- [x] 4.2 Check that `ceopardy serve --online --no-tunnel --guest-port 6001` serves the buzzer page on `:6001`, and that with `:6001` already taken it exits with a message suggesting `--guest-port`.
- [x] 4.3 Run `make format` and `make ci`; everything passes.

## Workflow follow-up

- Archive `add-online-soundboard` before archiving this change.
