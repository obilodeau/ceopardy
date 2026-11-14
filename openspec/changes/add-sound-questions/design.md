# Design

## Context

`question_to_html()` in `ceopardy/utils.py` turns `[img:f]` and `[video:f]`
into raw `<img>`/`<video>` markup pointing at `/static/game-media/f`. The
result is injected with `v-html` in three places: the viewer's
`QuestionOverlay`, the host's clue box in `HostView`, and the viewer iframe
embedded in the host's footer drawer. Anything that autoplays from that
markup therefore plays in every window, which is the wrong behaviour for
audio (see proposal.md - Why).

Audio already has one owner: `useSound.ts`, whose `isAudioSink()` picks the
window that is heard. The store's socket handlers call `useSound()`
directly for one-shot cues (`sound`, `soundboard` events).

## Goals / Non-Goals

**Goals:**
- Route clue audio through `useSound` so the `game-sound` sink rules apply
  without duplicating them.
- Keep the `[sound:]` tag a sibling of `[img:]` in the parser, while letting
  the rest of the line be ordinary clue text.

**Non-Goals:**
- Fixing `[video:]` playing in every window.
- Preloading or caching clue audio.

## Decisions

### The clue's sound URL travels as data, not markup
`Controller.get_question()` gains a `sound` field: the URL-quoted
`/static/game-media/<file>` for a sound clue, absent otherwise. It is
included in `question-show`, `dailydouble-reveal`, and the state's
`active_question`, and typed on `ActiveQuestion` in `frontend/src/types.ts`.
`question_to_html()` renders a sound clue as a static speaker icon
(`<i class="fa-solid fa-volume-high">` in a sized wrapper) followed by the
remaining text, with no `<audio>` element.

A small helper in `utils.py`,
`split_question_sound(text: str) -> tuple[str | None, str]`, uses
`re.search(r"\[sound:([^\]]*)\]", text)` and returns the first tag's file
name and the text with only that tag removed and stripped. Both callers
share it. `question_to_html()` calls it before its existing handling and
passes the remaining text through the usual `[utf8]`/`[fixed]`/newline path,
so `[fixed] [sound:x]` and `\n` keep working. The split happens on the raw
text, before `html.escape`. The file name never appears in the HTML; it only
goes, through `urllib.parse.quote`, into the `sound` field.

*Alternative:* emit `<audio data-src>` in the HTML and parse it on the
client. Rejected: every `v-html` site would need to avoid autoplay, and the
client would be scraping markup the server could just send as a field.

### Playback is triggered by events, never by state
The store's `question-show` and `dailydouble-reveal` handlers call
`useSound().playClue(url)` when the payload has `sound`; `question-hide`
calls `stopClue()`. Because a page load only applies `/api/v1/state`, a
client joining mid-clue never autoplays, which is the spec's join rule, with
no extra flag. For a daily double, `dailydouble` carries no text, so the
sound naturally waits for `dailydouble-reveal`.

`playClue()` keeps a single module-level `HTMLAudioElement` (separate from
`thinkingAudio` and the soundboard list so their stops don't touch it),
replaces any previous clue audio, checks `isAudioSink()`, and swallows
errors like `play()` so a missing file is silent.

*Alternative:* a watcher on `active_question.sound` in `App.vue` like
`isThinking`. Rejected: it fires on initial load and so would autoplay on
reload, and it cannot express Replay of the same URL.

### Replay/Stop is a separate endpoint
`POST /api/v1/question-sound {"action": "play"|"stop"}` checks the action
against `SOUND_ACTIONS`, that the active question has a `sound`, and that
it is not an unrevealed daily double (`dailydouble` state `enabled`), then
emits `question-sound {"action"}` on `GAME_NS`. The client resolves the URL
from its own `active_question.sound`. Validation goes in a pure helper in
`utils.py` that raises `SoundProblem`, mirroring `validate_sound_request`,
so it is unit-testable without Flask.

*Alternative:* extend `/api/v1/sound` with a `question` name. Rejected: that
endpoint's names are a fixed registry the `game-sound` spec enumerates.

### Replay/Stop live in the embedded viewer preview
`QuestionOverlay.vue` shows Replay (`fa-rotate-left`) and Stop (`fa-stop`)
buttons under the clue when the page is embedded
(`window.self !== window.top`, the check `isAudioSink()` and
`EnableSoundOverlay` already use) and `game.activeClueSound` is non-empty.
`activeClueSound` is a new store getter returning `active_question.sound`, or
`""` while a daily double is unrevealed. The buttons call
`api.questionSound("play" | "stop")`. The preview iframe loads `/` from the
host's own origin, so it reaches `/api/v1/question-sound` with no new
routing, and it never plays the sound itself because `isAudioSink()` is
false in an iframe.

The host's own clue box gets no controls; the preview is the one place to
replay.

*Alternative:* buttons in `HostView`'s clue box. Rejected at the user's
request in favour of the preview, which shows the clue as the audience sees
it. *Alternative:* buttons on the top-level viewer too. Rejected: the
audience would see them.

## Risks / Trade-offs

- [Online viewer that never clicked "enable sound" may be blocked by the
  autoplay policy] → same gamble as the existing one-shot cues; the host can
  Replay once the viewer is unlocked.
- [Replay is reachable only while the host's footer drawer is open, since
  the preview lives there] → accepted; opening the drawer is one click and
  the auto-play covers the common case.
- [Waiting music and a sound clue overlap if the host leaves music on] →
  accepted; the host controls both.
- [`[dbl][sound:x]` without a space is mangled by the existing
  `lstrip("[dbl]")`] → documented form uses a space, as other tags do.
