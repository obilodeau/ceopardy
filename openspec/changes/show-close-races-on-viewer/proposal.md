# Proposal

## Why

A photo finish is the most exciting moment of a buzzer race, but only the
host and the teams' own buzzer pages see the margins. The audience watching
the crowd screen (the viewer) sees only which team got the buzz, so a
2 ms win looks the same as a blowout.

## What Changes

- When a race is decided, each team in second or third place that is within
  the close-race threshold of the winner shows its margin, such as `+8 ms`,
  on its own team card on the viewer, under the team name. The winner, which
  becomes the team in control and keeps the thick white frame that marks it,
  shows no margin. The frame itself doesn't change.
- The margin flashes in when the race is decided and fades out when the host
  returns to the game board or the buzzers unlock again, whichever comes
  first.
- It works for every race, keyboard and web, offline and online.
- Only teams in the race when it is decided count. A team that buzzes after
  the winner is picked never shows a margin, and the host's result line
  growing with late teams doesn't change the cards.
- A new setting, `BUZZER_CLOSE_RACE_MS` (500 ms by default), sets how close
  counts as close.
- The host's result line and the buzzer pages don't change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `buzzer-race`: new requirements for the close margins on the viewer's team
  cards, and the close-race threshold joins the configurable race tuning
  values.

## Impact

- Back end: `ceopardy/config.py` (`BUZZER_CLOSE_RACE_MS`),
  `ceopardy/buzzer.py` (which entries are close, in `result_payload`),
  `ceopardy/api/routes.py` (marks close entries only at the decision).
- Front end: `frontend/src/stores/game.ts` (close margins and when they
  clear), `frontend/src/components/TeamPanelViewer.vue`,
  `frontend/src/types.ts`, `frontend/src/styles/main.css`.
- Tests: `tests/test_buzzer.py`.
- `README.md`: one sentence saying the crowd screen shows close margins.
- No new dependency, no change to install, run or dev workflow.
