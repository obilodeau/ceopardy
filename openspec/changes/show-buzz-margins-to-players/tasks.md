# Tasks

## 1. Arbiter: standings and late entries

- [ ] 1.1 In `ceopardy/buzzer.py` add `standing(decision: Decision, tid: str) -> tuple[int, int | None] | None` (1-based place; whole-ms margin ahead of the second entry for the winner, `None` when alone; margin behind the winner for others, floored at 0; `None` for a team not entered) and `standing_payload(place, margin_ms)` returning `{"place", "margin_ms"}`. Leave `closed_payload` as is. In `tests/test_buzzer.py` add `standing` to the payload-keys test and add tests for winner, runner-up, third, sole entrant, a tie (`+0`), a team not entered, and a keyboard winner from `buzz_local`; `make test` passes.
- [ ] 1.2 In `BuzzArbiter`, keep the `Decision` from `decide()` until `open()` or `close(keep_result=False)`. While kept, a `buzz()` with its epoch from a team not yet entered and not locked out is judged as usual, appended to the entries and not recorded as an early press; other presses while closed stay early presses. `buzz()` returns a `BuzzOutcome` with `delay` or `late` (the updated `Decision`). Add tests: a late buzz is appended with the next place; a second late press from the same team or a teammate adds nothing and counts as early; a late buzz after `open()` or `close(keep_result=False)` doesn't count; `close(keep_result=True)` keeps the result; a late buzz with a reaction below the winner's gets margin 0. `make test` passes.

## 2. Send standings from the buzzer page server

- [ ] 2.1 In `ceopardy/guest/buzzers.py`, make `on_decision` return whether the race was awarded and, when it was, send `standing` to each entered team's room after `_decide`. In `on_buzz`, on a `late` outcome send `standing` to the new team's room and, when the winner had been alone, to the winner's room, then call a new `on_late(decision)` callback. `set_open(False, ..., winner)` closes the arbiter with `keep_result=winner is not None`. In `ceopardy/api/routes.py` make `award_race` return whether it awarded and wire `on_late` to emit `buzz-result` with `result_payload(decision)` on `/game`. `_award_buzz` and `_set_buzzers` are unchanged.
- [ ] 2.2 In `tests/test_guest_server.py` add tests with a recorded `emit` and players on three teams: after a decision each entered team's room gets `standing` with its own place and margin and no other keys, and the team that didn't buzz gets none; a dropped award (`on_decision` returning False) sends no standing; a late buzz sends `standing` to its team and, after a sole winner, to the winner, and calls `on_late`; a repeated press sends nothing. `make test` passes.

## 3. Buzzer page and host line

- [ ] 3.1 Add `frontend/src/ordinal.ts` exporting `ordinal(n: number): string` (1st, 2nd, 3rd, 4th, 11th–13th, 21st…). `make frontend-type-check` passes.
- [ ] 3.2 In `frontend/src/buzzer/BuzzerApp.vue` handle `standing` typed as `{ place: number; margin_ms: number | null }`, setting a `margin` ref (`"8 ms ahead"` for place 1 with a margin, `"2nd · +8 ms"` for a higher place, otherwise empty, the place built with `ordinal`), cleared on `open`, `excluded` and a `closed` without a winner. Render it in a smaller `<p class="margin">` under the status, moving `role="status" aria-live="assertive"` from `.status` to a wrapper around both paragraphs so screen readers announce the margin. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 3.3 In `frontend/src/views/HostView.vue` add a `place` to each `buzzResult` entry and render it as `<span class="buzz-place">` before the text; in `frontend/src/styles/main.css` style `.buzz-place` smaller and dimmer than the line and keep the ` · ` separator only between entries (scope the `span + span::before` rule so it doesn't fire on the place span). Update the comment above `buzzResult`. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 3.4 Add one sentence to the Remote buzzers section of `README.md`: after each race, players see their team's place and how many milliseconds separated it from the winner, even if they buzz after the winner was picked. Verify it matches the page.

## 4. Integration

- [ ] 4.1 Verify with `CEOPARDY_ONLINE=1 CEOPARDY_GUEST_URL=http://localhost:5173/buzzer.html make run`, three buzzer pages on three teams and the host. Check that:
  - Two teams buzzing in the window: the winner's page shows `N ms ahead` and the other `2nd · +N ms`, consistent (±1 ms) with the host's line, which shows `1st`, `2nd` in a muted style with ` · ` only between entries.
  - The third team buzzing a second later gets `3rd · +N ms`, and the host's line gains `3rd` at the end. Pressing again changes nothing.
  - A lone buzz shows "You're in! Answer now." with no margin line, then `N ms ahead` once another team buzzes.
  - A team that never buzzes shows only "Another team was faster."
  - Selecting the next question clears the line; locking the buzzers without a winner shows none, and a press after that shows "too early", not a standing.
  - A keyboard buzz on the host that wins shows the web teams their place behind it.
  - Offline (`make run` without online mode), keyboard buzzing still awards as before.
- [ ] 4.2 Run `make format` and `make ci`; everything passes.
