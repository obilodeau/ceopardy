# Proposal

## Why

After a web buzzer race, players only learn whether their team won. They
can't tell a photo finish from a blowout, which is half the fun and the first
thing a losing team asks the host about
([#60](https://github.com/obilodeau/ceopardy/issues/60)).

## What Changes

- When a race is decided, each buzzer page of a team that entered it is told
  its team's place and its margin in whole milliseconds: the winner how far
  ahead of the runner-up it was, the others how far behind the winner.
- The winner's page reads "You're in! Answer now." with a line such as
  `8 ms ahead`. Another entrant's page reads "Another team was faster." with
  a line such as `2nd · +8 ms`.
- A sole entrant, a team that did not buzz, a locked-out team, and a race the
  host closed without a winner show no numbers, as today.
- The host's result line gains a small, dimmed place before each team, such
  as `1st Team 2 212 ms · 2nd Team 1 +48 ms`, so the host reads the same
  places the players see. The line keeps its size and position.
- Pages still never receive another team's name or reaction time. The margin
  is computed from the same judged reactions as the host's result line, so the
  two always agree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `buzzer-race`: the race result announcement tells each entered team's pages
  their place and margin, not only whether they won; the host's result line
  shows each team's place.
- `remote-buzzers`: the buzzer page may receive its own team's place and margin
  with the closing message, and shows them under the won and lost states.

## Impact

- Back end: `ceopardy/buzzer.py` (place and margin from a `Decision`,
  `closed_payload`), `ceopardy/guest/buzzers.py` (`set_open` takes the
  decision), `ceopardy/api/routes.py` (`_award_buzz` and `_set_buzzers` pass
  the decision through).
- Front end: `frontend/src/buzzer/BuzzerApp.vue`,
  `frontend/src/views/HostView.vue` and `frontend/src/styles/main.css` (place
  labels), plus a shared `frontend/src/ordinal.ts`.
- Tests: `tests/test_buzzer.py`, `tests/test_guest_server.py`.
- `README.md`: one sentence in Remote buzzers saying players see how close
  the race was.
- No new dependency, no change to install, run or dev workflow.
