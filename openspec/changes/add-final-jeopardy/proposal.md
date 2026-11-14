# Proposal

## Why

Round files can already declare a `final: [category] clue` line, and the game
model has an `in_final` state, but nothing plays it: clicking "Finish the
game" on a round with a final question does nothing at all (the `TODO` in
`/finish`). Online events now give every team a secret buzzer link on a port
built to face the internet ([#58](https://github.com/obilodeau/ceopardy/issues/58)),
which is the missing piece for a Final Jeopardy where remote teams write their
wager and answer by hand.

## What Changes

- In online mode, "Finish the game" on a round with a final question starts a
  Final Jeopardy round instead of ending the game. The host steps it through:
  show the category, reveal the clue, lock the answers, reveal each team's
  wager and answer in turn and judge it, then end the game.
- Each team's buzzer page turns into a paint canvas for the round, reached
  through the same secret link, port and security headers as the buzzer. All
  players on a team share one live canvas. There are two canvases per team: a
  wager canvas, open while the category is shown and locked when the clue is
  revealed, and an answer canvas, open from the clue reveal until the host
  locks answers.
- The wager is written by hand; the host reads it and types the amount when
  judging. The amount is bounded by the team's score, never below zero.
- Drawings stay secret until the host reveals that team: the viewer (the
  screen-shared tab) and the other teams never receive them before then.
- The final result is scored like a Daily Double: plus or minus the wager.
- Offline (no `--online`), "Finish the game" ends the game whether or not the
  round has a final question. This fixes the current no-op.
- The README's online section documents the Final Jeopardy flow and the
  `final:` line in round files.

## Capabilities

### New Capabilities

- `final-jeopardy`: The Final Jeopardy round. It covers how the round starts
  and the host-driven phases, what the viewer shows in each phase, wager
  bounds, scoring, and how the game ends.
- `player-canvas`: The shared drawing surface players reach through their
  team's buzzer link. It covers who may draw and when, how strokes are
  shared within a team, size limits, and what the canvas page may receive.

### Modified Capabilities

None. `openspec/specs/` is empty; the existing buzzer behavior is not yet
specified and is reused unchanged.

## Impact

- **Backend**: `ceopardy/api/routes.py` (`/finish` and new final-round
  endpoints), `ceopardy/controller.py` (final state, judging, scoring),
  `ceopardy/model.py` (a new table for team drawings), and
  `ceopardy/buzzer_server.py` (canvas events on the `/buzz` namespace).
  Drawing validation goes in a new Flask-free module so it can be unit
  tested.
- **Frontend**: the buzzer page (`frontend/src/buzzer/`) gains a canvas mode,
  the host view gains a Final Jeopardy panel, and the viewer gains category,
  clue and per-team reveal screens. Stroke rendering is shared by the buzzer
  page and the viewer.
- **Protocol**: new events on `/buzz` (players) and `/game` (host and
  viewer). Strokes are sent in small segments, so the `/buzz` 1 KiB message
  cap stays as is.
- **Database**: one new table, added by `create_all()` with no migration.
  Existing databases keep working.
- **Docs**: the README's online-event and round-file sections.
- **No new dependencies.**
