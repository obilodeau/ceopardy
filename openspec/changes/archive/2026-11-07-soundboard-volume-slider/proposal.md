# Proposal

## Why

The sound operator can play soundboard sounds on the stream but has no way to
make them quieter or louder. Some files are mastered much hotter than the
game's own cues, and the only fix today is editing the audio files
([#70](https://github.com/obilodeau/ceopardy/issues/70)).

## What Changes

- The soundboard page gets a volume slider, 0–100 %, defaulting to 85 %.
- Moving the slider sets the volume of soundboard sounds on the viewer,
  including sounds already playing. Game cues and the waiting music are not
  affected.
- The volume is shared: every connected soundboard page shows the same value,
  and a page that connects later starts at the current value. It resets to
  85 % when the server restarts.
- Slider drags are throttled on the page, with the trailing value always sent,
  and the server ignores volume messages beyond a per-connection rate.
- The throttle that the daily-double wager slider uses today is moved to a
  shared front-end helper, used by both sliders.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `online-soundboard`: adds a volume requirement, bounds volume messages, and
  lets the soundboard page receive the current volume besides the sound list.

## Impact

- Front end: `frontend/src/soundboard/SoundboardApp.vue` (slider),
  `frontend/src/composables/useSound.ts` (apply volume),
  `frontend/src/stores/game.ts` and `frontend/src/types.ts` (new `soundboard`
  event action), `frontend/src/components/TeamScoringPanel.vue` (use the shared
  throttle), plus a new shared throttle helper.
- Back end: `ceopardy/guest/soundboard.py` (`volume` event, current value,
  sync to pages), `ceopardy/soundboard.py` (volume parsing and payload),
  `ceopardy/api/routes.py` (`relay_soundboard` carries the volume).
- Tests: `tests/test_soundboard.py`, `tests/test_guest_server.py`.
- No new dependency, no change to install, run or dev workflow.
