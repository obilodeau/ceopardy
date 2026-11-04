# Proposal

## Why

During an online event the tab that gets screen-shared is the viewer, but
every sound played on the host machine only, so the remote audience heard no
buzzers, daily double, timeout or waiting music (issue #40). The waiting
music also played through once and then stopped silently.

## What Changes

- New `ceopardy serve --online` flag (and `CEOPARDY_ONLINE=1` for
  `make run`) that moves all sound from the host to the viewer. Without it
  the host plays sound exactly as before.
- New `POST /api/v1/sound` endpoint: the host asks the server to broadcast a
  sound cue to every client, and each client decides whether it is the one
  that makes noise.
- The sound registry (name to URL) is owned by the back-end and served in
  `/api/v1/state`, together with the online-mode flag and the waiting-music
  on/off state.
- Waiting music loops, and a client that joins or reloads mid-break resumes
  it.
- In online mode the viewer shows a one-time "enable sound" overlay to
  satisfy browser autoplay policy.
- The host's embedded viewer preview never plays sound.
- README documents online mode.

## Capabilities

### New Capabilities

- `game-sound`: which sounds the game plays, which window plays them in
  normal and online mode, the autoplay unlock on the viewer, waiting-music
  looping and resume, and validation of sound requests.

### Modified Capabilities

None.

## Impact

- Back-end: `ceopardy/__main__.py`, `ceopardy/config.py`,
  `ceopardy/api/routes.py`, `ceopardy/utils.py`, `ceopardy/exceptions.py`,
  `run.py`; new pytest coverage in `tests/test_utils.py`.
- Front-end: new `useSound` composable and `EnableSoundOverlay` component;
  changes to `App.vue`, `HostView.vue`, `ViewerView.vue`, `stores/game.ts`,
  `api.ts`, `types.ts`.
- API: new unauthenticated `POST /api/v1/sound`; new `sound` Socket.IO event
  on `/game`; `/api/v1/state` gains `sounds`, `config.ONLINE_MODE` and the
  `thinking` state key.
- Sound cues now cost a REST round-trip plus a broadcast instead of playing
  locally.
