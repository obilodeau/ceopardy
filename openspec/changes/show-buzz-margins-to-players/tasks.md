# Tasks

## 1. Standing and the closing payload

- [ ] 1.1 In `ceopardy/buzzer.py` add `standing(decision: Decision, tid: str) -> tuple[int, int | None] | None` (1-based place; whole-ms margin ahead of the runner-up for the winner, `None` when it raced alone; margin behind the winner for others; `None` for a team not entered) and extend `closed_payload(won, place=None, margin_ms=None)` to always return `{"won", "place", "margin_ms"}`. In `tests/test_buzzer.py` update the payload-keys test and add tests for winner, runner-up, third, sole entrant, a tie (`+0`), a team not entered, and a keyboard winner from `buzz_local`; `make test` passes.

## 2. Carry the decision to the pages

- [ ] 2.1 Change `BuzzersPage.set_open` in `ceopardy/guest/buzzers.py` to take `decision: Decision | None` instead of `winner`, sending each player `closed_payload` with `won` and, from `standing`, its team's place and margin. In `ceopardy/api/routes.py` make `_award_buzz(tid, decision=None)` build `result_payload` itself and pass the decision through `_set_buzzers(False, decision=...)`; `award_race` passes the decision. Verify the offline keyboard path (`_award_buzz(tid)`) still works with `make run` without `--online`.
- [ ] 2.2 In `tests/test_guest_server.py` add a test that connects players on two teams, calls `set_open(False, [], decision)` with a recorded `emit`, and checks each sid gets `closed` with its own team's `won`, `place` and `margin_ms` and no other keys; and that `set_open(False, [])` sends `won: null` with no place or margin. `make test` passes.

## 3. Buzzer page and host line

- [ ] 3.1 Add `frontend/src/ordinal.ts` exporting `ordinal(n: number): string` (1st, 2nd, 3rd, 4th, 11th–13th, 21st…). `make frontend-type-check` passes.
- [ ] 3.2 In `frontend/src/buzzer/BuzzerApp.vue` type `closed` as `{ won: boolean | null; place: number | null; margin_ms: number | null }`, keep a `margin` ref (`"8 ms ahead"` for a winner with a margin, `"2nd · +8 ms"` for an entrant that lost, otherwise empty) cleared on `open`, `excluded` and a `closed` without a winner, and build the place with `ordinal`, and render it in a smaller `<p class="margin">` under the status, moving `role="status" aria-live="assertive"` from `.status` to a wrapper around both paragraphs so screen readers announce the margin with the result. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 3.3 In `frontend/src/views/HostView.vue` add a `place` to each `buzzResult` entry and render it as `<span class="buzz-place">` before the text; in `frontend/src/styles/main.css` style `.buzz-place` smaller and dimmer than the line and keep the ` · ` separator only between entries (scope the `span + span::before` rule so it doesn't fire on the place span). Update the comment above `buzzResult`. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 3.4 Add one sentence to the Remote buzzers section of `README.md`: after each race, players see their team's place and how many milliseconds separated it from the winner. Verify it matches the page.

## 4. Integration

- [ ] 4.1 Verify with `CEOPARDY_ONLINE=1 CEOPARDY_GUEST_URL=http://localhost:5173/buzzer.html make run`, three buzzer pages on three teams and the host. Check that:
  - The winner's page shows `N ms ahead` and the others `2nd · +N ms` / `3rd · +N ms`, consistent (±1 ms) with the host's result line, which shows `1st`, `2nd`, `3rd` in a muted style before each team, with ` · ` only between entries and the line no wider than before plus the labels.
  - A team that didn't buzz shows only "Another team was faster."
  - A lone buzz shows "You're in! Answer now." with no margin line.
  - Selecting the next question clears the line; locking the buzzers without a winner shows none.
  - A keyboard buzz on the host that wins shows the web teams their place behind it.
- [ ] 4.2 Run `make format` and `make ci`; everything passes.
