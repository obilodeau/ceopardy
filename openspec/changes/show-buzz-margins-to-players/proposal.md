# Proposal

## Why

After a web buzzer race, players only learn whether their team won. They
can't tell a photo finish from a blowout, which is half the fun and the first
thing a losing team asks the host about
([#60](https://github.com/obilodeau/ceopardy/issues/60)).

## What Changes

- Deciding the race and reporting margins become separate jobs. The race is
  unchanged: same collection window, same latency compensation, and the
  closing message still says only whether the team won.
- A new `standing` message tells a team's buzzer pages its place and margin
  in whole milliseconds: the winner how far ahead of the runner-up it was,
  the others how far behind the winner. It is sent once per team: at the
  decision for each team that buzzed in the window, then on a team's first
  buzz after the decision, until buzzers open again. Later presses from the
  same team send nothing.
- A buzz after the decision is judged like any other but cannot win. Places
  already sent never change, so a late team takes the next place.
- The winner's page reads "You're in! Answer now." with a line such as
  `8 ms ahead`. Another entrant's page reads "Another team was faster." with
  a line such as `2nd · +8 ms`.
- A team that never buzzes, a locked-out team, and a race the host closed
  without a winner show no numbers, as today.
- The host's result line gains a small, dimmed place before each team, such
  as `1st Team 2 212 ms · 2nd Team 1 +48 ms`, and grows as late teams buzz.
- Pages still never receive another team's name or reaction time. Margins
  come from the same judged reactions as the host's result line, so the two
  always agree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `buzzer-race`: buzzes after the decision count for standings only; each
  team's pages are told their place and margin once; the host's result line
  shows places and late teams.
- `remote-buzzers`: the buzzer page may receive its own team's standing and
  shows it under the won and lost states.

## Impact

- Back end: `ceopardy/buzzer.py` (post-decision phase in `BuzzArbiter`,
  `standing`, `standing_payload`), `ceopardy/guest/buzzers.py` (sends
  standings, reports late entries), `ceopardy/api/routes.py` (`award_race`
  reports whether it awarded; re-sends `buzz-result` for late teams). The
  award path (`_award_buzz`, `_set_buzzers`, `closed`) is unchanged.
- Front end: `frontend/src/buzzer/BuzzerApp.vue`,
  `frontend/src/views/HostView.vue` and `frontend/src/styles/main.css` (place
  labels), plus a shared `frontend/src/ordinal.ts`.
- Tests: `tests/test_buzzer.py`, `tests/test_guest_server.py`.
- `README.md`: one sentence in Remote buzzers saying players see how close
  the race was.
- No new dependency, no change to install, run or dev workflow.
