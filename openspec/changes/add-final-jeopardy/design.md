# Design

## Context

See proposal.md for motivation and specs/ for the behavior. What exists today:

- `parse_gamefile` reads `final: [Category] clue`, and `setup_questions`
  stores it as a `Question` with `final=True`, `row=0`, `col=0`, score 0.
  `GameState.in_final` exists but nothing sets it. `/finish` does nothing
  when a final question exists.
- Online mode starts `BuzzerServer` (`ceopardy/buzzer_server.py`): a bare
  python-socketio app on `127.0.0.1:5001` that serves only the buzzer page's
  manifest-listed files, with a strict CSP and `max_http_buffer_size=1024`.
  Players join a room per team after `match_buzzer_token`, and
  `app.buzzer is not None` is how the main app knows it is online.
- Game-wide flags live in the `State` key/value table. Keys must stay at 10
  characters or fewer (`docs/todo-next-major.md`).
- `Answer.score_attributed` already carries a Daily Double's wager, and team
  scores are sums of `response × score_attributed`.
- The board payloads (`_questions_payload`) iterate every question, so the
  final one already leaks in as `c0q0`, which the boards happen to ignore.

## Goals / Non-Goals

**Goals:**

- Keep everything players reach on the existing buzzer port and link check.
  The canvas adds events to `/buzz`; it adds no HTTP route, no upload, and no
  widening of the CSP.
- Put the canvas rules (validation, caps, open/closed, undo, clear) in a
  Flask- and Socket.IO-free module, like `BuzzArbiter`, so they can be unit
  tested.
- Never hold a team's drawings on `/game` or in `/api/v1/state` before that
  team is revealed.

**Non-Goals:**

- Final Jeopardy offline (decided: online only).
- A server-enforced countdown. The host locks the answers, cued by the
  thinking music.
- Handwriting recognition or a typed wager field. The host reads the wager.
- An eraser, shapes, or text tool. Undo and clear are enough.
- Moderating what teams draw. The host previews every drawing before
  revealing it.

## Decisions

### Phase lives in `State`, game state in `Game`

`State("final")` holds `category`, `clue`, or `locked`, and
`State("final-team")` holds the revealed tid; both keys are 10 characters or
fewer. `Game.state` is `in_final` for the whole round and `finished` at the
end. The allowed transitions are a pure function in `utils`
(`next_final_phase(current, requested) -> bool`) so the order is tested
without Flask.

*Alternative:* a new `Game.final_phase` column. Rejected: `create_all()`
never alters an existing table, and the project has no migrations.

### Strokes are vectors of bounded integers, never images

A stroke segment is
`{canvas: "wager"|"answer", id: int, color: int, width: int, points: [x0, y0, x1, y1, ...]}`
on a fixed logical surface of 1200 × 800 (3:2), with palette and width
indices into fixed lists shared by server and page. Both the buzzer page and
the viewer redraw from these numbers with one shared module
(`frontend/src/canvas/strokes.ts`).

- *Why not PNG/data URLs:* an image upload means a large message on the
  internet-facing port, image parsing, and content the viewer would display
  without being able to check it. Bounded integers are trivially validated
  and can only ever render as lines.
- *Why a fixed logical surface:* phones are portrait and the viewer is
  landscape. The page letterboxes the 3:2 surface and scales it, so a drawing
  looks the same everywhere.

### Segments fit the existing 1 KiB message cap

The page sends the stroke in progress every ~50 ms as a segment of at most 32
points. The server appends a segment to the stroke with the same
`(sid, id)` or starts a new one, then relays the validated segment to the
team room with `skip_sid` set to the sender. 32 points of 4-digit integers
plus framing is about 400 bytes, so `max_http_buffer_size` stays at 1024.

*Alternative:* send whole strokes on pointer-up. Rejected: teammates would
not see a stroke until it is finished, and a long stroke would need a larger
cap.

### The canvas board is in memory and saved at phase boundaries

A `CanvasBoard` (new `ceopardy/canvas.py`) owned by `BuzzerServer` keeps, per
`(tid, canvas)`, an ordered list of strokes with their owner sid. It enforces
the caps (32 points per segment, 20,000 points and 2,000 strokes per canvas)
and which canvas is open. It is saved to a new `Drawing(tid, canvas, strokes)`
table, with strokes as JSON `Text`, at two moments: the wager canvases when
the clue is revealed, and the answer canvases when the answers are locked.
At startup, `BuzzerServer` loads saved drawings back into the board.

*Alternative:* write to the database on every segment. Rejected: commits
would run from buzzer-server threads up to 20 times a second per player, and
the host and viewer only need drawings once they are locked.

### Undo removes the sender's own last stroke

Each stroke records the sid that drew it, and undo removes that sid's most
recent stroke on the canvas. After a reconnect the player has a new sid, so
older strokes can only be cleared, not undone. That is acceptable for a short
round.

### `/buzz` protocol additions

Server to page:

- `final {phase, category}`, where `phase` is `null` outside the round. Sent
  on connect and on every phase change.
- `drawing {canvas, strokes}`, the team's full canvas. Sent on connect, and
  on undo or clear.
- `stroke {canvas, id, color, width, points}`, a teammate's segment.
- `canvas-full {canvas}`, sent only to the sender.

Page to server: `stroke`, `undo {canvas}`, `clear {canvas}`. The existing
payload helpers in `buzzer.py` get siblings in `canvas.py`, which are the only
place these dictionaries are built. The clue text and scores are never
included.

### Host and viewer endpoints

On `/api/v1`:

- `POST /finish` starts the round when online with a final question, ends the
  game when offline or without one, and ends it from `locked` during the
  round. Any other phase is a 400.
- `POST /final/phase {phase}` moves to `clue` or `locked` and validates with
  `next_final_phase`.
- `POST /final/reveal {tid}` is accepted only in `locked`.
- `POST /final/judge {tid, response, wager}` stores an `Answer` on the final
  question with `score_attributed = wager`, replacing an earlier one.
- `GET /final/drawings` is host-only. Like `/buzzers/links`, the viewer never
  calls it, and it is excluded from the dev CORS rule.

On `/game`: `final {phase, category, clue?}` and
`final-reveal {tid, wager, answer}`. In `/api/v1/state`, a `final` object
carries the phase, category, the clue once revealed, the revealed tid and
only that team's drawings, and the judgments. This is what restores a
reloaded viewer.

### Wager bound uses the score before the final

`final_wager_max(score) = max(score, 0)`, a pure function in `utils`. The
score is computed without the final question's answers, so re-judging does
not move the bound. `get_teams_score_by_tid` gains a flag that excludes
final answers, and the same filter drops `c0q0` from the board payloads.

### Buzzers are closed for the whole round

`_set_buzzers` refuses to open while `Game.state` is `in_final`, so
`/buzzers` and `/buzz` inherit the rule, and entering the final round closes
them. The arbiter is untouched.

### Frontend placement

- **Buzzer page:** `BuzzerApp.vue` switches on `final.phase` between the
  existing button and a new `FinalCanvas.vue` in `frontend/src/buzzer/`,
  driven by pointer events and with palette, width, undo and clear controls.
  The page has no extra dependency and no inline styles or scripts that the
  CSP would block.
- **Host:** `HostView.vue` shows a new `HostFinalPanel.vue` in place of the
  board while `in_final`. The panel has the phase buttons, each team's
  drawings (fetched from `/final/drawings` from `locked` on), a Reveal button
  per team, and a judge form with right/wrong/none plus a wager bounded by
  `final_wager_max`. `onFinish` stays on `/host` when the round starts.
- **Viewer:** a new `FinalOverlay.vue` shows the category, the clue, or the
  revealed team's drawings by phase.
- **Store:** new `final` state with getters in `stores/game.ts`, and types in
  `types.ts`.

## Risks / Trade-offs

- [Server restart during `category` or `clue` loses unsaved strokes] → The
  wager is saved at the clue reveal, and the answer phase is short. The host
  can ask teams to redraw. This is documented in the README.
- [A team draws something offensive and it reaches the stream] → The host
  previews every drawing from `locked` on, and only an explicit Reveal sends
  one to the viewer.
- [A modified client floods strokes] → Per-message point cap, per-canvas
  point and stroke caps, the 1 KiB message cap, and at most 16 players per
  team bound memory and relay fan-out. Per-IP rate limiting stays deferred, as
  in the buzzer plan.
- [A shared Vite chunk between the buzzer and main entries gets served on
  `:5001`] → `allowed_files` already serves exactly the buzzer entry's
  manifest closure. `strokes.ts` holds nothing secret, and the existing test
  that host chunks return 404 keeps guarding the boundary.
- [Resuming a finished game keeps the final answers in the score] → Resume
  sets `in_round` and clears the `final` phase. The final answers and saved
  drawings stay so a mis-click is recoverable. Finishing again restarts the
  round at `category`, and the saved drawings are reloaded into the board.
  This is a judgment call recorded here rather than specified.

## Migration Plan

`create_all()` adds the `drawing` table to existing databases. There are no
changes to existing columns and no change to round files, since `final:` is
already parsed. Rolling back is a code revert; the extra table is harmless.
