# Proposal

## Why

In person, a separate computer with a sound board feeds the venue console. Online, the
only audio the audience hears is the viewer tab being shared to Discord or Meet, and the
only sounds it can play are Ceopardy's fixed cues
([#61](https://github.com/obilodeau/ceopardy/issues/61)). The person running sounds is
usually not the host and not at the host's machine, so they need a remote way to play
sounds through that tab.

## What Changes

- A **remote soundboard page** with its own secret link, served by the existing players'
  server on the buzzer port, so it rides the same ngrok tunnel. It is isolated from the
  buzzers: it has its own page, its own Socket.IO namespace and its own secret. A buzzer
  link cannot reach the soundboard, and the soundboard link cannot buzz.
- The soundboard lists the audio files in a new **`soundboard/` folder** in the game
  directory, one button per file, named after the file. A **Stop all** button cuts every
  soundboard sound. Sounds can overlap. There is no loop or volume control.
- Pressing a button plays the sound **on the viewer only**, the tab being shared. The
  host and the soundboard page play nothing.
- From the top drawer, the host can **copy the soundboard link, replace it** (which
  disconnects whoever holds the old one), and see how many soundboard pages are
  connected.
- The feature exists only under `--online`. Offline, there is no soundboard page, link
  or drawer row.
- `ceopardy init` creates the empty `soundboard/` folder. The README documents the
  folder and the link.

## Capabilities

### New Capabilities

- `online-soundboard`: Remote playback of operator-supplied sounds on the viewer during
  online games. It covers the folder, the secret link and its isolation from the
  buzzers, what the remote page can see and do, playback on the viewer, and the host's
  link controls.

### Modified Capabilities

None. `openspec/specs/` is empty.

## Impact

- **Backend**: `ceopardy/buzzer_server.py` (a second page and the `/soundboard`
  namespace), a new Flask-free module with the folder listing and payloads,
  `ceopardy/model.py` (a table for the soundboard secret), `ceopardy/controller.py`,
  `ceopardy/api/routes.py` (link endpoints, `/game` events), `ceopardy/__init__.py`
  (serving `soundboard/` files to the viewer, CORS exclusion), and `ceopardy/__main__.py`
  (`init`).
- **Frontend**: a new `soundboard.html` Vite entry with its own small app, the viewer's
  audio layer (`useSound.ts`), the store, and `HostHeaderDrawer.vue`.
- **Database**: one new table, added by `create_all()` with no migration.
- **Ops**: no new port and no new tunnel. `.gitignore` ignores `/soundboard/`.
- **No new dependencies.**
