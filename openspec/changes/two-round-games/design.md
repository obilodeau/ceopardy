# Design

## Context

A game is one `Game` row, the `Team` rows, the `Question` rows loaded from a
single round file, and the `Answer` rows the host submits. Questions are
addressed by `(col, row)` alone (`c3q2`), so a second board in the same
database would collide with the first. Scores are summed over every `Answer`
with no reference to a round file, which already gives the right total once
both rounds' answers are kept.

The database is created with `db.create_all()`, which adds missing tables but
never alters existing ones. There is no migration tooling. `Game` already
stores `schema_version` (currently 1), which nothing reads yet.

The maintainer chose two things for this change: both rounds' questions and
answers stay in the live database, which is a breaking schema change, and
clue values are the same in both rounds.

## Goals / Non-Goals

**Goals:**
- Round-scoped board queries, so `c3q2` always means the current round's
  clue.
- Old databases are detected and moved aside, never misread or half-upgraded.
- One-round games behave exactly as they do now.

**Non-Goals:**
- Final Jeopardy. `/finish` still treats a round file's `final:` line as the
  unimplemented no-op it is today, and only in the last round.
- Doubled round-2 values or per-round score ticks.
- More than two rounds. The model stores a count, so allowing more later only
  means loosening the validation and the UI wording.
- Migrating old databases in place.

## Decisions

### Schema: round on `Question`, round state on `Game`

Add `Question.round` (int), `Game.rounds` (number of rounds, 1 or 2) and
`Game.round` (current round), and bump `SCHEMA_VERSION` to 2. Answers stay
attached to questions, so they inherit the round.

Alternative considered: keep schema 1, snapshot round-1 totals into a new
carry-over table and delete round 1's rows. It avoids the breaking change but
loses round 1's per-clue record from the live database and makes resuming
round 1 impossible. The maintainer prefers the breaking change.

While the schema breaks anyway, also widen `State.name` from `String(10)` to
`String(32)` and drop that item from `docs/todo-next-major.md`. That
document parks the change until old databases are declared unsupported,
which this change does.

### A `between_rounds` game state

Add `GameState.between_rounds`. `is_game_in_progress()` keeps returning true
only for `in_round` and `in_final`, so the router's existing guard already
sends the host from `/host` to `/start` between rounds.

Alternative considered: reuse `finished` and compare `round < rounds`. Every
reader of `finished` (start screen, resume, store getters) would then have to
make that comparison, so we use an explicit state instead.

### Every board query filters on the current round

Every `Question` lookup in `Controller` adds `Question.round == game.round`:
`get_categories`, `get_question`, `get_answer`, `answer_normal`,
`answer_dailydouble`, `_get_questions_status`, `get_good_answer_team` and
`is_final_question`. A small helper returns the current round so the filter
is written the same way everywhere. `get_teams_score` and
`get_teams_score_by_tid` stay unfiltered: summing across rounds is the
carry-over, and the daily double range reads them, so it is cumulative too.

### Loading a round is one function used for both rounds

Pull the board-loading body out of `setup_questions` into a function taking
the round file and the round number. `setup_questions` (new game, round 1)
and `start_next_round` both call it. It parses the whole round file and its
questions before adding anything to the session. A category missing from
`Questions.cp` currently raises a bare `KeyError` partway through the adds.
It becomes a `GamefileParsingError`, and the session is rolled back on any
failure, so a bad round 2 file leaves round 1 intact and the game between
rounds.

`start_next_round` refuses unless the state is `between_rounds`. Otherwise
it loads round `round + 1`, sets `Game.round`, `Game.round_filename` and
`in_round`, and clears the team in control.

### API

- `POST /init {"action": "new", "name", "rounds"}`: `rounds` is optional and
  defaults to 1. It is validated with a pure helper in `utils` before any
  backup is taken. An invalid count returns 400.
- `POST /init {"action": "next-round", "name"}`: returns 400 when not between
  rounds and 500 on a parse failure, the same as `new`. It reuses `/init`'s
  existing tail (the "game is being set up" message, cleared question, state
  broadcast), which is what a new round needs too.
- `POST /finish`: when `round < rounds`, end the round. Clear the question and
  daily double, close the buzzers, set the overlay to an end-of-round message
  and the state to `between_rounds`. Otherwise keep today's behavior.
- `resume`: move `between_rounds` or `finished` back to `in_round` without
  changing `Game.round`. Between rounds that resumes round 1, after the game
  that resumes the last round.
- The state payload gains top-level `round` and `rounds`.

### Frontend

- Store: `round` and `rounds` state, plus getters `isBetweenRounds` and
  `hasNextRound` (`round < rounds`), so components don't repeat the
  comparison.
- `StartView`: a one/two rounds choice next to *New Game*'s file list,
  passed as `rounds`. Between rounds it also shows *Start Round 2* with its
  own file list, and *Resume Round N* is shown for `between_rounds` as well
  as `finished`.
- `HostView.onFinish`: the confirmation text depends on `hasNextRound`.
- The viewer needs no change: the end-of-round message arrives as
  `overlay-big`, like the end-of-game one.

### Outdated database detection runs before SQLAlchemy opens the file

A pure function in `utils` takes the database path and the expected version.
It reads `game.schema_version` with the standard `sqlite3` module. If the
version differs, it renames the file to
`ceopardy_<timestamp>_schema-v<N>.db` and returns the new path. If the file
is missing, has no `game` table or has no row, it leaves the file alone.
`create_app()` calls it before `db.create_all()` and logs the backup path.
The function needs no Flask app, so it can be tested on temporary SQLite
files. The timestamp format is shared with `db_backup_and_create_new`.

Alternative considered: refuse to start and tell the operator to move the
file. Each game has its own directory and old games are finished, so moving
the file aside loses nothing and saves a manual step.

### Templates

Add `templates/data/2nd.round` (Category6–Category10) and those categories
to `templates/data/Questions.cp`, so a fresh `ceopardy init` can play a
two-round game straight away.

## Risks / Trade-offs

- [An operator upgrades in the middle of an event, with a game in progress
  on schema 1] → The game is moved aside, not lost. The README upgrade note
  says to finish games before upgrading, and the release notes flag the
  break.
- [A missed `Question` query keeps reading both rounds, for example a clue
  from round 1 shows up on round 2's board] → The decision above lists every
  query, and a task checks for unfiltered `Question` queries in the
  controller before testing by hand.
- [The host picks the same file for round 2] → That is allowed: it is the
  operator's call, and nothing breaks because the rounds are separate rows.
- [`GameState` is stored as an enum string whose column length came from the
  old longest name] → Fresh schema-2 databases are created with the new
  length, and old ones are moved aside.

## Migration Plan

1. Release as a breaking version. The release notes say that `ceopardy.db`
   from earlier versions is moved aside on first start.
2. On first start in an existing game directory, the old database becomes
   `ceopardy_<timestamp>_schema-v1.db`, and the start screen offers a new
   game.
3. To roll back, install the previous release and rename the backup to
   `ceopardy.db`.
