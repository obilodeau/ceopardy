# Design

## Context

The bottom drawer of the host UI lists the entries of `config["MESSAGES"]`.
The last default entry, `Custom`, has an empty body and takes its text from an
edit box opened with a pencil icon. Before this change that box was a bare
`contenteditable` div with no button; see proposal.md for the problems that
caused.

`/message/show` renders the text as `"<p>{0}</p>".format(text)`, unescaped,
and broadcasts the html and message id on the `overlay-big` socket event.
Every `State` row already reaches the host through the full-state payload, and
the store copies unknown keys into `ui_state`.

## Goals / Non-Goals

**Goals:**

- A submit control visually tied to the box, valid whether or not the custom
  message is already up.
- No way to show an empty custom message.
- The box survives a host reload while the custom message is on screen.

**Non-Goals:**

- Multiline messages.
- Changing how hosts can type HTML into a message.
- Live sync of the box between two open host windows.
- Changing how the custom entry is identified in `MESSAGES`.

## Decisions

**Submit always shows, never hides.** It means "put this on the screen", so
editing a live message is a single click with no board flash. Hiding stays on
the row's eye icon and the global eye-slash. Nothing about the button depends
on what is displayed except its tooltip ("Show this message" vs. "Update the
message on screen"). Alternative considered: make the button a toggle like the
eye; rejected because that reproduces the two-click update.

**Same shape as the team-name editor.** A `<form @submit.prevent>`, an input,
a centered `form-icon form-click` icon button (paper plane, `fa-2x`, between
two `form-expand` spacers) and a hidden `<input type="submit">` so Enter
submits. The two drawers read the same. The empty case reuses the existing
`.disabled` class (opacity, no pointer events), so it needs no new CSS or copy.

**Single-line input, not a textarea.** The server wraps the text in one
`<p>`, so a typed newline would silently collapse on the crowd screen.
Multiline needs a backend change and a decision on escaping (see Deferred).

**The text is trimmed before it is sent**, and a whitespace-only box counts as
empty.

**One code path shows the custom message.** The row's eye icon, when the
custom message is not live, delegates to the same submit function, so it
obeys the same empty-box rule. The custom entry is found once (index of the
entry titled `Custom`, -1 when the operator removed it) instead of a title
test and an inline `message${idx + 1}` repeated in three places.

**The falsy-chain fix.** Showing a message used `msg?.text || customText ||
""`, so any preset with an empty body silently borrowed the custom text. It now
branches on whether the row is the custom entry: custom uses the box, presets
use their own body, even if empty.

**Focus on open.** The pencil focuses the input after the box renders, so the
host can type straight away.

**`.form-edit` CSS.** The class had exactly one user, the replaced div. As an
input it needs an explicit width (`calc(100% - 20px)` with `border-box`, to
fill the column inside its 10px side margins) and its focus glow was selected
as `.form-edit[contenteditable='true']`, which would have stopped matching;
the qualifier is dropped. The generic `[contenteditable='true']` rules keep
serving the team-name fields.

**Persist the raw text server-side.** `/message/show` stores the text as a
`message-text` state row, for presets too: it is simply the text behind the
overlay that is up, costs one row, and keeps the backend from re-deriving
which `MESSAGES` entry is custom. `/message/hide` leaves it alone. Nothing
else is needed to deliver it; `message-text` is added to `UiState` and the
store's initial state so it is typed.

**Reseed from that state, guarded.** A watcher on the current message id and
`message-text` runs immediately and on change. When the custom message is the
one on screen it opens the box and, only if the box is empty, fills it from
`message-text`. It never closes the box (that stays the pencil's job) and the
empty-draft guard keeps it from overwriting a draft. A real input with
`v-model` is what makes programmatic seeding safe; writing into the old
`contenteditable` would have moved the caret, which is why persistence was
done on top of the form change.

### Divergences from the plan

- The plan initialized the box's open state once from "custom is live"; the
  implementation does it in the watcher, so the box also opens when the
  custom message goes live later.
- The plan's width was `100%`; the implementation uses `calc(100% - 20px)` to
  account for the existing side margins.
- The plan expected a second host window to pick up submitted text live. The
  `overlay-big` event carries only the html and id, so the text is restored
  on load, not live; no new event was added.

## Risks / Trade-offs

- [`State.name` is `db.String(10)` and `message-text` is 12 characters] →
  Harmless on SQLite, which does not enforce `VARCHAR` length; other keys
  (`container-footer`, `overlay-question`) already exceed it. Widening the
  column is a schema change left for its own commit.
- [The custom entry is still identified by `title === "Custom"`] → An operator
  who renames it loses the edit box, same as before. A `custom: true` flag
  would break existing configs, so it was left alone.
- [A second host window holds the `message-text` it loaded] → When another
  window shows the custom message, this window opens its box and, if empty,
  seeds it from its possibly stale copy. Acceptable for a rare setup; a reload
  brings it current.
- [Wrapping the box in a `<form>` inserts a non-flex element in the drawer's
  flex column] → Part of the manual pass: check the drawer above and below the
  1230px breakpoint, where `.form-header` and `.form-text` switch to fixed
  sizes.
- [No component test harness] → Verified with `make ci` and a manual pass
  (host and crowd views side by side).

## Deferred

- Multiline custom messages: needs `/message/show` to stop being a single
  `<p>`, and a decision on escaping host input. Today it is not escaped, so a
  host can deliberately type HTML; escaping would take that away.
- Refreshing `docs/images/host.png` for the new button, at the next screenshot
  pass. `README.md` needed no change.
