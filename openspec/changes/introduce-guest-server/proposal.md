# Proposal

## Why

The internet-facing server on port `5001` is named after its first tenant, the
buzzers, but it now also serves the soundboard, and a drawing canvas for Final
Jeopardy may follow. Its flags, settings and code all say "buzzer", which
misdescribes what the port is: the one low-risk surface for people who are not
the host. Renaming it to the **guest** server, the counterpart of the host,
says what it is and gives later pages an obvious home.

## What Changes

- The listener on `5001` becomes the **guest port**, serving **guest pages**
  (today the buzzer page and the soundboard). Its rules (bound to
  `127.0.0.1`, an exact allow-list of files, locked-down headers, known
  origins only, the only port the tunnel reaches) move into a capability of
  their own, which every guest page relies on.
- **BREAKING** `ceopardy serve` flags: `--buzzer-port` becomes `--guest-port`
  and `--buzzer-url` becomes `--guest-url`. The old flags are removed, not
  aliased.
- **BREAKING** dev environment variable: `CEOPARDY_BUZZER_URL` becomes
  `CEOPARDY_GUEST_URL`.
- **BREAKING** guest pages connect on the Socket.IO path `/guest-io` instead
  of `/buzz-io`. A buzzer or soundboard page left open from before the
  upgrade must be reloaded.
- The start-up banner and the host's top drawer say "Guest pages" where they
  said "Buzzers", and the 503 for an unbuilt front-end names the guest pages.
- Internally, the server is split into a guest server (files, headers,
  origins, socket, lifecycle) and one module per guest page with its own
  namespace, so a new page is one module and one allow-list entry. The
  buzzer race and soundboard rules modules are unchanged.
- Settings that are about the port are renamed (`GUEST_PORT`,
  `GUEST_PUBLIC_URL`, `GUEST_TUNNEL`). Settings about buzzing itself keep
  their `BUZZER_` names.
- `README.md` uses the new names.

## Capabilities

### New Capabilities

- `guest-port`: The internet-facing listener for non-host participants: what
  it binds to and serves, its response headers and origin checks, how its
  public URL and tunnel are chosen and shown, and how the dev server starts
  it.

### Modified Capabilities

- `remote-buzzers`: The listener, URL and tunnel requirements move to
  `guest-port`. The remaining requirements that named "the buzzer port" now
  name the guest port.
- `online-soundboard`: Requirements that named "the buzzer port" now name
  the guest port. This capability is introduced by `add-online-soundboard`,
  which must be archived before this change.

## Impact

- **Backend:** `ceopardy/buzzer_server.py` is replaced by a `ceopardy/guest/`
  package. `ceopardy/__init__.py`, `ceopardy/__main__.py`, `ceopardy/config.py`,
  `ceopardy/tunnel.py`, `ceopardy/api/routes.py` and `run.py` follow the new
  names.
- **Frontend:** the buzzer and soundboard pages' socket path, the Vite dev
  proxy, and the drawer's labels.
- **Operators and developers:** the renamed flags and environment variable.
  There is no data migration. The REST API and the `/game` events are
  unchanged.
- **Tests:** `tests/test_buzzer_server.py` becomes `tests/test_guest_server.py`.
- **No new dependencies.**
