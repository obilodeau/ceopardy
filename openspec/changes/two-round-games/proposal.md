# Proposal

## Why

A real Jeopardy game is two rounds played by the same teams, with scores
carrying over (issue #59). Ceopardy only plays one round file per game, so a
two-round event today means two separate games and adding the scores up by
hand.

## What Changes

- When starting a new game, the host chooses between a one-round and a
  two-round game, then picks the first round file as today.
- In a two-round game, the host's finish control ends round 1 instead of the
  game. The crowd screen announces the end of the round, and the host picks
  the round 2 file from the start screen.
- Round 2 loads a fresh board from the chosen round file. Teams, team names,
  buzzer and soundboard links stay as they are, and scores keep accumulating
  from round 1. Clue values are the same in both rounds.
- Finishing round 2 (or the only round of a one-round game) ends the game as
  today. Resume works on the round just finished, including a round 1 ended
  by mistake.
- `ceopardy init` also scaffolds a `data/2nd.round` example and the matching
  categories in `data/Questions.cp`.
- **BREAKING**: the database schema gains the round each question belongs to
  and the game's round count. Databases from earlier versions can't be read;
  on startup Ceopardy moves an outdated `ceopardy.db` aside as a timestamped
  backup and starts a fresh one.

## Capabilities

### New Capabilities
- `game-rounds`: how a game is set up as one or two rounds, how the host
  moves from one round to the next, and how teams and scores carry across
  rounds.

### Modified Capabilities

None.

## Impact

- `ceopardy/model.py`: `Question.round`, `Game.rounds` and `Game.round`, new
  `GameState.between_rounds`, `SCHEMA_VERSION` 1 → 2.
- `ceopardy/__init__.py`: outdated-schema check and backup before
  `db.create_all()`.
- `ceopardy/controller.py`: question queries scoped to the current round;
  new round setup and end-of-round transitions.
- `ceopardy/api/routes.py`: `/init` takes a round count and a `next-round`
  action; `/finish` ends a round or the game; the state payload reports the
  round.
- Frontend: start view (round-count choice, round 2 picker, resume between
  rounds), host finish confirmation, store/types for the round fields.
- `ceopardy/templates/data/`: new `2nd.round`, extended `Questions.cp`.
- `README.md`: two-round games and the schema upgrade note in the operator
  section.
