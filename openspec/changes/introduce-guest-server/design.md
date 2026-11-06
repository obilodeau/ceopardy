# Design

## Context

See proposal.md for why. Today `ceopardy/buzzer_server.py` holds everything
on port `5001` in one class, `BuzzerServer`: the HTTP allow-list built from the
Vite manifest, the security headers, the origin check, the `socketio.Server`,
the `/buzz` namespace with its arbiter and ping loop, and, since
`add-online-soundboard`, the `/soundboard` namespace. The main app keeps it in
`app.buzzer`, and the routes call buzzer and soundboard methods on it directly.

The pure rules modules, `ceopardy/buzzer.py` (the race) and
`ceopardy/soundboard.py` (the folder and rate limit), have no Flask or
Socket.IO and are not part of this change.

## Goals / Non-Goals

**Goals:**

- One name, "guest", for the port, the server, its settings, flags and
  socket path.
- Adding a guest page means adding one module and listing it, without
  touching the HTTP or security code.
- Every existing behavior and test case carries over unchanged, apart from
  the names in the specs.

**Non-Goals:**

- Aliases for the old flags, environment variable, settings or socket path.
- The drawing canvas itself.
- Renaming the `/buzz` namespace, the buzzer page, the `BUZZER_` race
  settings, or anything about how buzzers work.
- Changing the REST API or the `/game` events.

## Decisions

### "Guest" as the name

Guests are the counterpart of the host, which the code, UI and README already
name. The word also says how much they are trusted: guests get a few pages
and a socket, nothing else.

*Alternatives:* "remote" (says where people are, not what they may do),
"companion" (party-game jargon, says nothing about trust), "public"
(suggests no authentication, which is wrong), "studio" (sounds like the
host's control room).

### A `ceopardy/guest/` package: one server, one module per page

```
ceopardy/guest/__init__.py     GuestPage, the base for a page's namespace
ceopardy/guest/server.py       GuestServer: files, headers, origins, socket, serve()
ceopardy/guest/buzzers.py      BuzzersPage: /buzz, the arbiter, the ping loop
ceopardy/guest/soundboard.py   SoundboardPage: /soundboard
```

`GuestPage` subclasses python-socketio's class-based `socketio.Namespace`.
Each page declares the URLs it serves (`{"/": "buzzer.html"}`,
`{"/soundboard.html": "soundboard.html"}`) and may start background work
from `start()`. `GuestServer(buzzers, soundboard, public_url)` takes each
page by name, registers each namespace on one `socketio.Server`, builds the
allow-list from the pages' entries and the Vite manifest, and starts each
page when it serves. A new page is one more parameter.

Every `on_<event>` method of a page is an event any connected guest can
send, so callbacks into the game are stored under other names (`relay`,
not `on_play`).

The main app keeps the server in `app.guest`, and the routes reach a page
through it: `app.guest.buzzers.set_open(...)`,
`app.guest.soundboard.revoke()`. A page that isn't running (offline) is
still `app.guest is None`, as today.

*Alternatives:* keep one class and rename it (it grows a section per page,
and the soundboard already made it hard to read); one server per page
(each would need its own port, and ngrok's free plan gives one static
domain).

The socket glue is `ceopardy.guest.soundboard` while the rules stay in
`ceopardy.soundboard`, and likewise for the buzzers. The package name tells
them apart, and keeping the rules modules where they are leaves their tests
and imports alone.

### Settings, flags and paths

| Before | After |
| --- | --- |
| `--buzzer-port`, `BUZZER_PORT` | `--guest-port`, `GUEST_PORT` |
| `--buzzer-url`, `BUZZER_PUBLIC_URL` | `--guest-url`, `GUEST_PUBLIC_URL` |
| `BUZZER_TUNNEL` | `GUEST_TUNNEL` |
| `CEOPARDY_BUZZER_URL` | `CEOPARDY_GUEST_URL` |
| Socket.IO path `/buzz-io` | `/guest-io` |
| `start_buzzer_server()`, `app.buzzer` | `start_guest_server()`, `app.guest` |
| banner `Buzzers: …` | `Guest pages: …` |
| drawer `Buzzers: …` | removed; the copy icons give complete links |

`BUZZER_MAX_PLAYERS_PER_TEAM` and the `BUZZER_*_MS` race settings keep their
names: they are about buzzing, not about the port. `--no-tunnel`,
`--tunnel-domain`, `NGROK_*` and `CEOPARDY_TUNNEL` already say nothing about
buzzers.

The old names are removed, not aliased, as the user decided. argparse
rejects an old flag with an error naming it, which is enough of a pointer.

### The guest server binds its own socket

werkzeug's `make_server` catches a busy port itself, prints its own message
and exits, so the "Try --buzzer-port" message never appeared. `serve()` now
binds the socket and hands it to werkzeug, so the error reaches the caller,
which names `--guest-port`.

### URLs and links stay the same

The buzzer page stays at `/` and the soundboard at `/soundboard.html`, and
the tokens are untouched, so links handed out before the upgrade keep
working once the open pages reload.

## Risks / Trade-offs

- [A page open across the upgrade still polls `/buzz-io` and gets 404s] →
  It shows "reconnecting" until it is reloaded. The release notes say to
  reload buzzer and soundboard pages.
- [Operators' scripts use `--buzzer-port` or `--buzzer-url`] → The command
  fails at once with argparse's error, and the README shows the new flags.
- [Two modules named `soundboard`] → Imports always use the full
  `ceopardy.guest.soundboard` or `ceopardy.soundboard` path.
- [This branch sits on `add-online-soundboard`] → It merges after that PR.
  The `online-soundboard` delta can only be archived after that change.

## Migration Plan

Nothing in the database or the game directory changes. Archive
`add-online-soundboard` before this change, since this change modifies two
of its requirements. Rolling back is a code revert.
