# Tasks

## 1. Parse the `[sound:]` tag

- [ ] 1.1 Add `split_question_sound(text: str) -> tuple[str | None, str]` to `ceopardy/utils.py` returning the first `[sound:<file>]` file name and the text with only that tag removed, and verify with new tests in `tests/test_utils.py` for a bare tag, a tag at the start/middle/end of text, two tags (second kept as text), and no tag (None, text unchanged)
- [ ] 1.2 Render sound clues in `question_to_html()` as a speaker icon followed by the remaining text through the usual `[utf8]`/`[fixed]`/newline handling, with no `<audio>` element; verify tests assert the icon and text are present, the tag is gone, `[fixed] Listen [sound:x.mp3]` yields `<tt>`, no `<audio`/`<video` appears, and a name like `a"b<c>.mp3` puts no `<c>` or `"` in the HTML
- [ ] 1.3 Add a `sound` field (URL-quoted `/static/game-media/<file>`) to `Controller.get_question()` for sound clues only, and verify via `make test` plus a manual `/api/v1/state` check with a `[sound:]` clue open

## 2. Broadcast clue sound with show, reveal and replay

- [ ] 2.1 Include `sound` in the `question-show` and `dailydouble-reveal` payloads in `ceopardy/api/routes.py`; verify in the browser devtools that the socket events carry it for a sound clue and omit it otherwise
- [ ] 2.2 Add a pure `validate_question_sound_request(action: object, sound: str | None, dailydouble: str) -> str` to `ceopardy/utils.py` raising `SoundProblem`, and verify tests cover valid play/stop, unknown action, missing body value, no sound clue, and unrevealed daily double
- [ ] 2.3 Add `POST /api/v1/question-sound` that uses the helper, answers 400 with `result="failure"` and an error on rejection, and emits `question-sound {"action"}` on `GAME_NS` on success; verify with `curl` against `make run` for a success and each 400 case

## 3. Play clue audio through the audio sink

- [ ] 3.1 Add `sound?: string` to `ActiveQuestion` and the show/reveal event types in `frontend/src/types.ts`, and an `activeClueSound` getter to `stores/game.ts` that is `""` while a daily double is unrevealed; verify `make frontend-type-check`
- [ ] 3.2 Add `playClue(url)` / `stopClue()` to `useSound.ts` with their own single audio handle, gated by `isAudioSink()`, restarting from the beginning on replay and swallowing load/play errors; verify `make frontend-type-check`
- [ ] 3.3 In the store, call `playClue` from the `question-show` and `dailydouble-reveal` handlers when `sound` is present, `stopClue` from `question-hide`, and handle a new `question-sound` event using `active_question.sound`; verify manually in normal mode that the clue plays once on the host only, and in `CEOPARDY_ONLINE=1` mode once on the viewer only, with the host and its embedded preview silent
- [ ] 3.4 Verify manually that reloading the viewer mid-clue in online mode shows the clue but stays silent, that a daily double sound clue plays only on reveal, that closing the clue stops it, and that a missing file is silent with no console error

## 4. Replay/Stop in the embedded viewer preview

- [ ] 4.1 Add `api.questionSound(action)` in `frontend/src/api.ts` and Replay/Stop buttons in `QuestionOverlay.vue` shown only when embedded (`window.self !== window.top`) and `game.activeClueSound` is set; verify manually with the host's footer drawer open that Replay restarts the sound on the window that is heard (viewer with `CEOPARDY_ONLINE=1`, host otherwise), Stop silences it with the clue still open, and the buttons are absent on a top-level viewer, for text clues, and for an unrevealed daily double

## 5. Documentation and CI

- [ ] 5.1 Add commented examples of `[img:]`, `[video:]` and `[sound:]` (files go in `game-media/`), including a sound clue with text, to `ceopardy/templates/data/Questions.cp` (the template `ceopardy init` copies), and verify `ceopardy init` in a temp dir writes them and the round still loads
- [ ] 5.2 Run `make format && make ci` and verify ruff, prettier, vue-tsc and pytest all pass

## Workflow follow-up

- Archive the change after the user has tested it.
