# Tasks

## 1. Schema and outdated-database handling

- [ ] 1.1 In `ceopardy/model.py`, bump `SCHEMA_VERSION` to 2, add `Question.round`, `Game.rounds` and `Game.round` (a new `Game` is 1 of 1), add `GameState.between_rounds`, and widen `State.name` to `String(32)`. Remove the `State.name` item from `docs/todo-next-major.md`. Verify that a fresh `make run` creates a `ceopardy.db` whose `game` and `question` tables have the new columns (`sqlite3 ceopardy.db .schema`).
- [ ] 1.2 In `ceopardy/utils.py`, add `move_aside_outdated_db(db_path: str, schema_version: int) -> str | None`. It uses `sqlite3` to read `game.schema_version`; on a mismatch it renames the file to `ceopardy_<timestamp>_schema-v<N>.db` and returns the new path. It leaves a missing file, a database with no `game` table and an empty `game` table alone. Share the timestamp format with `Controller.db_backup_and_create_new`. In `tests/test_utils.py`, add tests on `tmp_path` SQLite files for v1 (moved), the current version (kept), no file, and no `game` table. `make test` passes.
- [ ] 1.3 Call it from `create_app()` in `ceopardy/__init__.py` before `db.create_all()`, and log the backup path at warning level. Verify by hand: start `ceopardy serve` in a directory holding a `ceopardy.db` from the previous release. The file is renamed, the path is printed, and the start screen offers only *New Game*.

## 2. Round-scoped controller

- [ ] 2.1 In `ceopardy/controller.py`, add a current-round helper and filter every `Question` lookup on it: `get_categories`, `get_question`, `get_answer`, `answer_normal`, `answer_dailydouble`, `_get_questions_status`, `get_good_answer_team` and `is_final_question`. Leave the score sums unfiltered. Verify that `grep -n "Question\.\(query\|row\|col\)\|query(Question" ceopardy/controller.py` shows no unscoped board lookup.
- [ ] 2.2 Extract board loading from `setup_questions` into a function taking the round file and the round number. It parses everything before adding rows, raises `GamefileParsingError` for a category missing from `Questions.cp`, and rolls the session back on failure. `setup_questions` keeps its behavior for round 1. Verify that a one-round game still loads `1st.round` with `make run`.
- [ ] 2.3 Add `Controller.setup_rounds(rounds: int)`, `end_round()` (to `between_rounds`) and `start_next_round(round_file: str)`. `start_next_round` raises `GameProblem` unless the game is between rounds, loads round `round + 1`, updates `Game.round` and `round_filename`, sets `in_round`, and clears the team in control. Make `resume_game` accept `between_rounds` as well as `finished` without changing `Game.round`. Verify through the API in task 3.4.
- [ ] 2.4 In `ceopardy/utils.py`, add `parse_round_count(value: object) -> int`. It returns 1 for `None`, returns 1 or 2 for those ints, and raises `GameProblem` for anything else, including `bool`, strings and 3. Add tests in `tests/test_utils.py`; `make test` passes.

## 3. API

- [ ] 3.1 Have `/init` `new` validate `rounds` with `parse_round_count` before backing up the current game, return 400 on an invalid count, and call `setup_rounds`.
- [ ] 3.2 Add the `/init` action `next-round` with `name`. It returns 400 when the game is not between rounds and 500 on a parse error, and otherwise shares the existing tail (setup message, cleared question, state broadcast).
- [ ] 3.3 Have `/finish` end the round when `round < rounds`: clear the question and daily double, close the buzzers with an empty lock-out, set `overlay-big` and `overlay-question` to an end-of-round message, call `end_round`, and emit the same `dailydouble-wager`, `question-hide` and `overlay-big` events as the end of the game. Otherwise keep today's behavior. Add top-level `round` and `rounds` to `_full_state_payload`.
- [ ] 3.4 Verify with `make run` and `curl` against `/api/v1`:
  - `new` with `rounds: 3` returns 400 and leaves the game unchanged.
  - A two-round game reports `round: 1, rounds: 2`.
  - `next-round` during round 1 returns 400.
  - After `finish`, `game_state` is `between_rounds`.
  - `next-round` with a file naming an unknown category returns 500 and the round 1 board is unchanged.
  - `next-round` with `2nd.round` shows the new categories, no answered clues and the round 1 scores.
  - `resume` between rounds brings back round 1's board.

## 4. Frontend

- [ ] 4.1 In `frontend/src/types.ts`, add `between_rounds` to `GameState` and `round`/`rounds` to `ServerState`. Add `rounds` to `InitPayload` and the `next-round` action, and add an `api` helper if it reads better than a bare `init`. In `frontend/src/stores/game.ts`, add `round`/`rounds` state applied from the server, plus `isBetweenRounds` and `hasNextRound` getters. `make frontend-type-check` passes.
- [ ] 4.2 In `frontend/src/views/StartView.vue`, add a one/two rounds choice (default one) to the *New Game* file list, sent as `rounds`. Between rounds, show *Start Round 2* with its own file list, which calls `next-round` and goes to the host page. Show *Resume Round N* when the game is between rounds or finished.
- [ ] 4.3 In `frontend/src/views/HostView.vue`, base `onFinish`'s confirmation on `hasNextRound` ("End round 1? You'll pick the round 2 file next." versus today's text). `make frontend-lint` and `make frontend-type-check` pass.

## 5. Templates and docs

- [ ] 5.1 Add `ceopardy/templates/data/2nd.round` (Category6 to Category10) and those categories, with five placeholder clues each, to `ceopardy/templates/data/Questions.cp`. Verify that `ceopardy init` in an empty directory writes both round files and that each loads as a round.
- [ ] 5.2 Update the operator section of `README.md`. Mention `data/2nd.round` in the init step, add a short paragraph on two-round games (choose on *New Game*, finish ends round 1, pick the round 2 file, scores carry over), and note that a `ceopardy.db` from an earlier version is moved aside on first start, so games should be finished before upgrading. Check the wording against the UI.

## 6. Integration

- [ ] 6.1 With `make run`, play a two-round game with the host and viewer open: score some clues in round 1, including a daily double, then finish. Check that:
  - The viewer shows the end-of-round message, and `/host` redirects to the start screen.
  - Round 2 starts from `2nd.round` with the totals carried over.
  - A round 2 daily double's maximum wager is the cumulative score.
  - Finishing round 2 shows the end-of-game message.
  - Resume brings back round 2.
  - A one-round game still behaves as before.
- [ ] 6.2 In online mode (`CEOPARDY_ONLINE=1 make run`), check that a buzzer page and the soundboard page connected in round 1 still work in round 2 without new links.
- [ ] 6.3 Run `make format` and `make ci`; everything passes.
