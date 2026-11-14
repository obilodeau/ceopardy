# Tasks

## 1. Close entries on the server

- [ ] 1.1 In `ceopardy/config.py` add `BUZZER_CLOSE_RACE_MS: 500` next to the other buzzer settings, with a one-line comment. In `ceopardy/buzzer.py` add `close_entries(decision: Decision, threshold_ms: float) -> list[str]` (tids of the second and third entries whose margin behind the winner, rounded to whole ms, is at most the threshold) and give `result_payload` a `close: list[str]` argument, defaulting to empty, sent as `"close"`. In `tests/test_buzzer.py` add tests for a photo finish naming both, only the runner-up close, nothing close, a sole entrant, a tie at `+0`, a margin exactly at the threshold, and a fourth entry that is close but never named; `make test` passes.
- [ ] 1.2 In `ceopardy/api/routes.py` make `_decide` pass `close_entries(decision, config["BUZZER_CLOSE_RACE_MS"])` to `result_payload`, and leave `_publish_late` sending the default empty list. Verify with a scratch-directory offline run: two keypresses 20 ms apart give a `buzz-result` with `close: ["team…"]`, and a late keypress re-emits it with `close: []`. `make test` passes.

## 2. Margins on the viewer's team cards

- [ ] 2.1 In `frontend/src/types.ts` add `close: string[]` to `BuzzResultEvent`. In `frontend/src/stores/game.ts` add `closeMargins: Record<string, number>`: set it from a `buzz-result` with a non-empty `close` (reaction minus the winner's, rounded, floored at 0), leave it alone on an empty `close`, and empty it on `question-hide` and on `buzzers` with `open: true`, never touching the team in control. Add a `closeMarginOf(tid)` getter. `make frontend-type-check` passes.
- [ ] 2.2 In `frontend/src/components/TeamPanelViewer.vue` render `+N ms` from `closeMarginOf` in a `<p class="close-margin">` under the team name, inside a `<Transition name="close-margin">`, and make the name box stack its children so the name stays centered without a margin. In `frontend/src/styles/main.css` style `.close-margin` in the board's sans-serif font and gold, smaller than the name, with the scores' text shadow; give it a flash-in animation (a glow pulsing two or three times within about a second) and a fade-out of about half a second. `make frontend-lint` and `make frontend-type-check` pass.
- [ ] 2.3 Add one sentence to `README.md` where buzzing is described: on the crowd screen, the teams that came within `BUZZER_CLOSE_RACE_MS` of the winner show their margin on their card until the host returns to the board or the buzzers unlock. Verify it matches the app.

## 3. Integration

- [ ] 3.1 Build the frontend and, in a scratch directory with a headless browser on the viewer (screenshots of the cards), check that:
  - Offline, keys `2` then `1` 20 ms apart: team 1's card flashes in `+20 ms` under its name, in a different font from the name; team 2, now in control, keeps its white frame and shows no margin.
  - Keys 700 ms apart show no margin.
  - A late keypress after a close race leaves the margins as they are and adds none.
  - Marking the answer *Good* keeps the margins; returning to the board fades them out while the team in control keeps its frame; marking the winner *Bad* (buzzers re-open) fades them out.
  - Online, two web players buzzing within the threshold show the runner-up's margin.
  - The host's embedded viewer shows the same margins.
- [ ] 3.2 Run `make format` and `make ci`; everything passes.
