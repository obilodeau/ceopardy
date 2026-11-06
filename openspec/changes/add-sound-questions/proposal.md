# Proposal

## Why

Issue #62: question files can show a picture (`[img:file]`) or a video
(`[video:file]`), but there is no way to make a clue that is a sound, such as
"name that tune" or "identify this voice". A video file works around it
poorly, and it plays on every window that renders the clue (host, viewer, and
the host's embedded viewer preview), so in online mode the host hears it and
in normal mode it plays twice.

## What Changes

- New question-file tag `[sound:<file>]`, modelled on `[img:<file>]`: `<file>`
  is resolved under the game's `game-media/` folder, served from
  `/static/game-media/<file>`. The tag can sit anywhere on the question's
  line; the rest of the line is the clue's text.
- A sound clue shows a speaker icon followed by its text (if any) on the
  viewer and the host.
- The sound plays once, automatically, when the clue is shown (or when a
  daily double's clue is revealed), and only on the window that plays the
  game's sounds — the host in normal mode, the viewer in online mode, never
  the embedded preview — following the existing game-sound rules.
- The viewer preview embedded in the host page shows Replay and Stop
  buttons on a sound clue. They are broadcast through the server so they
  reach the window that is heard. The top-level viewer the audience sees
  shows no controls.
- The sound stops when the clue closes.
- A client that loads or reconnects while a sound clue is open does not
  start the sound on its own; the host uses Replay.

Out of scope: changing how `[video:]` plays.

## Capabilities

### New Capabilities
- `question-sound`: sound clues in question files — the `[sound:]` tag, how
  the clue and its text are displayed, when and where its audio plays, and
  the Replay/Stop controls in the embedded viewer preview.

### Modified Capabilities

None. Which window plays is reused unchanged from `game-sound`.

## Impact

- `ceopardy/utils.py` (`question_to_html`): parse `[sound:]`.
- `ceopardy/api/routes.py`: new `POST /api/v1/question-sound` endpoint
  broadcasting a `question-sound` event on the game namespace.
- Frontend: `useSound.ts` (question-sound playback through the audio sink),
  `stores/game.ts` (event handlers and a getter for the active clue's sound
  URL), `QuestionOverlay.vue` (Replay/Stop in the embedded preview),
  `api.ts`, `types.ts`.
- `ceopardy/templates/data/Questions.cp`: document the tag.
- Tests in `tests/test_utils.py`.
