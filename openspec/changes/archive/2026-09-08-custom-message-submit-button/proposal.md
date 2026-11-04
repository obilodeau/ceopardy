# Proposal

## Why

The host's custom message box had no control of its own ([#41](https://github.com/obilodeau/ceopardy/issues/41)).
The only way to put the typed text on the crowd screen was the eye icon on the
`Custom` row, which is a toggle: updating a message already on screen took a
hide and a show, and the crowd saw the board flash in between. An empty box
could be shown, blanking the crowd screen, and a host reload emptied the box
while the message stayed up.

## What Changes

- The custom message box becomes a form with a single-line input and a submit
  button (Enter works too). Submit always shows the message and never hides
  it, so editing a live message is one click.
- Submit is disabled while the box is empty or blank; an empty custom message
  can no longer be shown.
- Hiding stays on the row's eye icon and the global hide icon.
- Preset messages always show their own text; a preset with an empty body no
  longer borrows the custom box's text.
- Opening the box with the pencil focuses the input.
- The server keeps the raw text of the message on screen. A host that reloads
  while the custom message is up gets the box reopened and refilled, without
  overwriting a draft already being typed.

## Capabilities

### New Capabilities

- `crowd-messages`: the host showing and hiding preset and custom messages on
  the crowd screen, the custom message submit, and its persistence across a
  host reload.

### Modified Capabilities

None.

## Impact

- Host UI bottom drawer (`frontend/src/components/HostFooterDrawer.vue`) and
  the `.form-edit` styles in `frontend/src/styles/main.css`.
- `POST /message/show` now also stores a `message-text` state row; the value
  reaches the host through the existing full-state payload. `UiState` and the
  store's initial state gain the key.
- No new endpoints, events, dependencies or config. Existing `MESSAGES`
  configs keep working.
