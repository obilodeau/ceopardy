# Tasks

## 1. Pure rules

- [ ] 1.1 Add `next_final_phase(current, requested) -> bool` and `final_wager_max(score) -> int` to `ceopardy/utils.py`, with type hints. Verify with new cases in `tests/test_utils.py`: every allowed transition, skipping and going backwards rejected, and the bound for positive, zero and negative scores. `make test` passes.
- [ ] 1.2 Create `ceopardy/canvas.py` with `CanvasBoard`: per `(tid, canvas)` stroke lists with owner sid, `open(canvas)` and `close_all()`, `add_segment`, `undo`, `clear`, `strokes`, `load` and `snapshot`, and the `/buzz` payload helpers (`final_payload`, `drawing_payload`, `stroke_payload`, `canvas_full_payload`). It holds the shared palette and width lists and the caps (32 points per segment, 20,000 points and 2,000 strokes per canvas, a 1200 × 800 surface). Verify that the module imports no Flask or Socket.IO.
- [ ] 1.3 Add `tests/test_canvas.py` covering: valid segments appended to the right stroke, segments to a closed canvas dropped, out-of-range, non-integer, boolean and NaN coordinates dropped, unknown color or width dropped, odd-length point lists dropped, the point and stroke caps reported as full, undo removing only the sender's last stroke, clear emptying the canvas, teams isolated from each other, and `snapshot`/`load` round-tripping. `make test` passes.

## 2. Data and controller

- [ ] 2.1 Add a `Drawing(tid, canvas, strokes)` model to `ceopardy/model.py` (strokes as JSON `Text`, unique on `(tid, canvas)`). Verify that starting the server against an existing `ceopardy.db` creates the `drawing` table and leaves the other tables intact (`sqlite3 ceopardy.db .schema`).
- [ ] 2.2 In `ceopardy/controller.py`, add `get_final_question`, `start_final`, `set_final_phase`, `answer_final(tid, response, wager)` (bounded by `final_wager_max` on the score without final answers, replacing an earlier judgment), `get_final_judgments`, `save_drawings` and `load_drawings`. Add an `include_final` flag to `get_teams_score_by_tid`. `resume_game` clears `State("final")` and `State("final-team")`. Verify by exercising them through the API in 3.4.
- [ ] 2.3 Exclude the final question from `get_questions_status_for_viewer` and `get_questions_status_for_host`. Verify that `GET /api/v1/state` on a round with a `final:` line has no `c0q0` key in `questions`.

## 3. Host API

- [ ] 3.1 Rework `POST /finish` in `ceopardy/api/routes.py`. It starts the round when `app.buzzer` is set and a final question exists, ends the game when offline or without a final question, ends it from `locked`, and returns 400 in any other final phase. Starting closes the buzzers, clears the clue and Daily Double, emits `final` on `/game` and pushes the phase to `/buzz`.
- [ ] 3.2 Add `POST /final/phase`, `POST /final/reveal`, `POST /final/judge` and `GET /final/drawings`. Exclude `/final/drawings` from the CORS rule next to `/buzzers/links`. The clue reveal saves the wager canvases, and the lock saves the answer canvases. A reveal emits `final-reveal` with only that team's drawings, and a judgment emits a board update.
- [ ] 3.3 Add the `final` object to `_full_state_payload`, containing the phase, category, the clue only from `clue` on, the revealed tid with only that team's drawings, and the judgments. Make `_set_buzzers` refuse to open while `in_final`, so `/buzzers` with `open` returns a failure.
- [ ] 3.4 Verify 2.2–3.3 end to end with `curl` against `CEOPARDY_ONLINE=1 make run` on a round file with a `final:` line. Check that phase skips return 400, the wager above the pre-final score is rejected, re-judging replaces the score, `/api/v1/state` holds no unrevealed team's strokes, and offline `/finish` ends the game.

## 4. Buzzer server

- [ ] 4.1 Give `BuzzerServer` a `CanvasBoard` and handlers for `stroke`, `undo` and `clear` on `/buzz`. A valid segment is relayed to the team room with `skip_sid`. Undo and clear send the full `drawing` to the room. A canvas past its cap sends `canvas-full` to the sender only. On connect, the page gets `final` and both `drawing` payloads when a round is on.
- [ ] 4.2 Add `set_final(phase, category)`, which opens or closes canvases and emits `final` to every player, `snapshot(canvas)` for saving, and loading of saved drawings when the server starts. Wire them from `start_buzzer_server` and the routes in section 3.
- [ ] 4.3 Extend `tests/test_buzzer_server.py`, using a recorder in place of `sio.emit`. Check that a stroke from a Team 1 sid is relayed to room `team1` only, a stroke before the round is dropped, and connect during `clue` sends `final` and both drawings. Check that no `/buzz` payload contains clue text or scores. The existing test that host chunks return 404 still passes. `make test` passes.

## 5. Shared stroke rendering and the buzzer page

- [ ] 5.1 Add `frontend/src/canvas/strokes.ts` with the palette, widths, surface size, the `Stroke`/`StrokeSegment` types and `drawStrokes(ctx, strokes, scale)`. Verify that `make frontend-type-check` passes.
- [ ] 5.2 Add `frontend/src/buzzer/FinalCanvas.vue`, a letterboxed 3:2 canvas driven by pointer events that sends segments of at most 32 points every ~50 ms. It draws teammates' segments live, has palette, width, undo and clear controls, shows read-only and full states, and has no inline style or script blocked by the CSP. Show it from `BuzzerApp.vue` when `final.phase` is set: the wager canvas in `category`, and the answer canvas (with the wager read-only) in `clue` and `locked`.
- [ ] 5.3 Verify the built page (`npm run build`, then `:5001`) with two browsers on Team 1's link and one on Team 2's. Teammates see each other's strokes live, Team 2 sees none, a reload restores the drawing, strokes after lock are refused, and the browser console shows no CSP violation.

## 6. Host panel

- [ ] 6.1 Add the `final` state, the `final` and `final-reveal` socket handlers and getters (`isFinal`, `finalPhase`) to `frontend/src/stores/game.ts`, add the types to `types.ts`, and add the `api.ts` calls for the endpoints in section 3.
- [ ] 6.2 Add `frontend/src/components/HostFinalPanel.vue` and show it in place of `HostBoard` in `HostView.vue` while `in_final`. It has Reveal clue, Lock answers and End game buttons enabled by phase. From `locked` on, it shows each team's drawings from `/final/drawings`, a Reveal button per team, and a judge form (right/wrong/none, and a wager input bounded to `max(pre-final score, 0)`). Keep `onFinish` on `/host` when the round starts, and update its confirmation text.
- [ ] 6.3 Verify in the browser that the host can run the whole round, a host reload in each phase restores the panel, an out-of-range wager shows the server's error, and `make frontend-lint` and `make frontend-type-check` pass.

## 7. Viewer

- [ ] 7.1 Add `frontend/src/components/FinalOverlay.vue` to `ViewerView.vue`. It shows "Final Jeopardy" with the category in `category`, the clue in `clue` and `locked`, and the revealed team's name with its wager and answer drawings after a reveal. Scores update on judgment, and the existing end-of-game message shows once finished.
- [ ] 7.2 Verify in the browser that a viewer reload in each phase restores the right screen, and that the viewer's network log (state fetch and `/game` frames) never contains an unrevealed team's strokes.

## 8. Documentation

- [ ] 8.1 Update `README.md`. Document the `final: [Category] clue` round-file line in the operator section. Add a short Final Jeopardy subsection under the online sections covering the host's steps, and that teams use the same link and write their wager by hand. Note that offline "Game over" ends the game, and that strokes not yet locked are lost on a server restart. Remove the "finalize game doesn't work" line from `TODO`. Verify the documented steps match the UI.

## 9. Integration

- [ ] 9.1 Play a full online game with three teams on separate browsers through the built wheel (`make build` and `pipx install --force dist/ceopardy-*.whl`, then `ceopardy serve --online`). Run board clues, then the final round, judge every team, and end the game. Check the final scores against the expected sums.
- [ ] 9.2 Run `make format` and `make ci`; everything passes.
