# Proposal

## Why

After a buzzer race, players only learn whether their team won. They can't
tell a photo finish from a blowout, which is half the fun and the first thing
a losing team asks the host about
([#60](https://github.com/obilodeau/ceopardy/issues/60)). Physical buzzers
(keyboard presses on the host) race too, but offline they skip the race
entirely: the first press is awarded and nobody learns by how much.

## What Changes

- The buzzer race runs in both modes, for keyboard and web buzzers alike.
  Latency compensation and the collection window apply only to web players:
  when no web player is in the race, which is always the case offline, the
  first buzz wins at once, as today.
- Deciding the race and reporting margins become separate jobs. The decision
  is unchanged, and the closing message to buzzer pages still says only
  whether the team won.
- Each team that enters a race is given its place and margin in whole
  milliseconds once: the winner how far ahead of the runner-up it was, the
  others how far behind the winner. Teams in the race get it when the buzz
  is awarded; a team's first buzz after the decision, from a page or the
  keyboard, gets it then and takes the next place. Places already given never
  change. Further presses from the same team change nothing.
- The host's result line shows after every race, offline too, with a small,
  dimmed place before each team, such as
  `1st Team 2 212 ms · 2nd Team 1 +48 ms`, and grows as late teams buzz.
- Online, a new `standing` message tells a team's buzzer pages its place and
  margin. The winner's page reads "You're in! Answer now." with a line such
  as `8 ms ahead`; another entrant's page reads "Another team was faster."
  with a line such as `2nd · +8 ms`. Pages still never receive another
  team's name or reaction time.
- The host forwards keypresses even while buzzers are closed, so the server
  can count a late keyboard buzz.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `buzzers`: keyboard buzzes go through the race in both modes; a keypress
  after the decision counts for the result.
- `buzzer-race`: the race covers keyboard buzzers offline too, with no
  window when no web player is in it; buzzes after the decision count for
  standings only; each team is given its standing once; the host's result
  line shows places and late teams in both modes.
- `remote-buzzers`: the buzzer page may receive its own team's standing and
  shows it under the won and lost states.

## Impact

- Back end: `ceopardy/buzzer.py` (zero window without web players,
  post-decision phase, `standing`, `standing_payload`), `ceopardy/__init__.py`
  (the arbiter is created for both modes and handed to the buzzer page in
  online mode), `ceopardy/guest/buzzers.py` (no longer owns the arbiter or
  its timer; sends cues and standings), `ceopardy/api/routes.py` (opens,
  closes and decides the race; keyboard buzzes always go through it).
- Front end: `frontend/src/views/HostView.vue` (forwards keypresses while
  closed; place labels), `frontend/src/buzzer/BuzzerApp.vue`,
  `frontend/src/styles/main.css`, plus a shared `frontend/src/ordinal.ts`.
- Tests: `tests/test_buzzer.py`, `tests/test_guest_server.py`.
- `README.md`: one sentence saying the host and players see how close each
  race was.
- No new dependency, no change to install, run or dev workflow.
