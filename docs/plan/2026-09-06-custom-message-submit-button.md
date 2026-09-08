# Give custom messages a submit button

Implementation plan for [obilodeau/ceopardy#41](https://github.com/obilodeau/ceopardy/issues/41)
("Custom messages need a submit button").

## Problem

The bottom drawer of the host UI lists the messages from `config["MESSAGES"]`.
The last of them, `Custom`, has an empty body and gets its text from an edit
box the host opens with a pencil icon
([HostFooterDrawer.vue](frontend/src/components/HostFooterDrawer.vue)). There is
no control that commits what the host typed:

- The edit box is a bare `contenteditable` div with **no button of its own**.
  The only thing that pushes the text to the crowd screen is the eye icon on
  the `Custom` *row above it*, which is not visually tied to the box.
- That eye icon is a **toggle**: `toggleMessage()` hides the message when it is
  already the active one. So editing the text of a message that is currently on
  screen does nothing, and the only way to update it is eye (hide) → eye
  (show) — two clicks, with the crowd seeing the board flash in between.
- Showing `Custom` with an empty box posts `<p></p>`, which blanks the crowd
  screen with an empty overlay and no indication anything is wrong.
- `customText` is tracked with `@input` on a div that *also* renders
  `<span>{{ customText }}</span>`. Nothing seeds `customText` today, so this is
  latent rather than broken — but any programmatic write to it moves the
  caret, which is exactly what Phase 2 needs to do.
- The text lives only in that component's `ref`. Reload the host page and the
  box is empty while the crowd screen still shows the message. This is the
  `{# TODO restore content here on reload #}` from the pre-Vue template
  (`git show d8c8aab^:templates/host.html`, line 291), carried across the
  rewrite.

## Approach

Make the edit box a real form with a real submit, in the shape the host UI
already uses for team names in
[HostHeaderDrawer.vue](frontend/src/components/HostHeaderDrawer.vue): a
`<form @submit.prevent>`, a text input, a `form-icon form-click` icon button,
and a hidden `<input type="submit">` so Enter works.

Two properties matter for the fix to actually solve the reported problem:

- **Submit always shows, never hides.** It is "put this on the screen", valid
  both when the custom message is off and when it is already up — that is what
  makes live editing a single click.
- **Hiding stays where it is**, on the row's eye icon and the global
  eye-slash. Submit is not a toggle; nothing about the button's appearance
  depends on what is currently displayed.

A single-line `<input>` rather than a textarea: `/message/show` renders
`"<p>{0}</p>".format(text)`, so a typed newline would silently collapse on the
crowd screen. Multiline is a backend change (escaping + `\n` → `<br>`) and a
separate decision — see *Deferred*.

Phase 2 then closes the reload TODO, in its own commit, by persisting the raw
message text server-side like every other piece of host state.

## Changes

### Phase 1 — the submit button (front-end only)

#### `frontend/src/components/HostFooterDrawer.vue`

**Script**

- Add a `customIdx` computed: `game.messages.findIndex(m => m.title === "Custom")`,
  and a `customMid` computed returning `message${customIdx + 1}` (`""` when
  there is no `Custom` entry — an operator can edit `MESSAGES` in their config).
  Both replace the `m.title === 'Custom'` string test and the inline
  `message${idx + 1}` template literals that are currently repeated in three
  places.
- Add `canSubmit`: `customIdx >= 0 && customText.trim().length > 0`.
- Add `showCustom()`:

  ```ts
  async function showCustom(): Promise<void> {
    if (!canSubmit.value) return;
    await api.showMessage(customMid.value, customText.value.trim());
  }
  ```

  No hide branch, no toggle — that is the whole point of the button.
- Fix `toggleMessage()` to branch on the message rather than on a falsy chain:
  the current `msg?.text || customText.value || ""` means *any* preset with an
  empty body would silently borrow the custom text. Use `customText` when
  `idx === customIdx`, `msg.text` otherwise, and delegate the custom case to
  `showCustom()` so there is one code path that shows a custom message.
- `toggleCustom()` also focuses the input when it opens (a `ref` on the input
  plus `nextTick`), so the pencil click leaves the host ready to type.

**Template**

- Replace the `contenteditable` div with a form, keeping the `form-edit` box
  look:

  ```vue
  <form v-if="customEditing" @submit.prevent="showCustom">
    <input
      ref="customInput"
      v-model="customText"
      class="form-color form-edit form-no-form form-text"
      autocomplete="off"
      placeholder="Type a message for the crowd screen"
    />
    <div class="form-row form-color">
      <div class="form-expand" />
      <div
        class="form-icon form-click"
        :class="{ disabled: !canSubmit }"
        :title="
          currentMessage === customMid
            ? 'Update the message on screen'
            : 'Show this message'
        "
        @click="showCustom"
      >
        <i class="fa-solid fa-paper-plane fa-2x" />
      </div>
      <div class="form-expand" />
    </div>
    <input type="submit" style="display: none" />
  </form>
  ```

  `fa-2x` + centering between two `form-expand` spacers is the team-name Save
  button's exact layout, so the two drawers read the same. `.disabled` already
  exists in [main.css](frontend/src/styles/main.css) (opacity + `pointer-events:
  none`), so the empty-box case needs no new CSS and no new copy — the button
  is visibly inert until there is something to send.
- Auto-open the box when the custom message is the active one, so a host who
  reloads mid-message lands on an editable box rather than a hidden one:
  initialize `customEditing` from `currentMessage === customMid`.
- Show the pencil on the row via `idx === customIdx` instead of the title test.

#### `frontend/src/styles/main.css`

Two edits, both safe: `.form-edit` has exactly one user in the whole
front-end, the div being replaced.

- `.form-edit` (line 233) sets `margin-left`/`margin-right: 10px` and no width.
  As an `<input>` inside a form it needs `width: 100%` and `box-sizing:
  border-box` to fill the drawer column the way the block-level div did.
- The focus glow at lines 274-275 is selected as
  `.form-edit[contenteditable='true']:active, …:focus`, which stops matching
  the moment the box becomes an input — the box would lose its focus ring
  entirely. Drop the `[contenteditable='true']` qualifier from that rule so it
  reads `.form-edit:active, .form-edit:focus`. The generic
  `[contenteditable='true']` colour rules above it (lines 258-272) go on
  applying to the team-name fields, which are separate elements.

### Phase 2 — survive a host reload (separate commit)

#### `ceopardy/api/routes.py`

In `message_show()`, alongside the two existing `set_state` calls:

```python
controller.set_state("message-text", text)
```

Unconditional, for presets too — it is simply "the text behind the overlay
that is currently up", it costs one row, and it avoids the back-end having to
re-derive which entry in `MESSAGES` is the custom one.

`message_hide()` is left alone on purpose: the host's draft should survive
hiding the message, the same way it survives while the drawer is closed.

`get_complete_state()` already returns every `State` row, `_full_state_payload()`
already ships it as `state`, and `applyServerState()` already copies unknown
keys into `ui_state` (the `UiState` index signature covers it) — so nothing
else on either side needs to change to make the value reach the host.

#### `frontend/src/components/HostFooterDrawer.vue`

Seed the box from that state, once, when the custom message is the live one:

```ts
watch(
  () => [game.ui_state.message, game.ui_state["message-text"]] as const,
  ([mid, text]) => {
    if (mid && mid === customMid.value && !customText.value) {
      customText.value = text ?? "";
    }
  },
  { immediate: true },
);
```

The `!customText.value` guard is what keeps this from fighting the host: a
second host window submitting a message must not overwrite an unsent draft in
this one. `v-model` on a real input also means seeding it cannot move the caret
the way writing into the `contenteditable` div would have — which is why this
phase is worth doing only on top of Phase 1.

#### `frontend/src/types.ts`

Add `"message-text": string` to `UiState` and to the store's `ui_state` initial
state, so the key is typed rather than reaching through the index signature.

## Testing

No test harness exists for Vue components (no vitest; `tests/` is pure-Python
utility tests per `AGENTS.md`), and the Phase 2 back-end change is a route that
needs an app context. So: `make ci` for lint/format/type-check/pytest, plus a
manual pass with `make run`, the host UI in one window and the crowd view in
another.

| step | expected |
| --- | --- |
| open pencil, box empty | submit greyed out, clicking it does nothing |
| type text, click submit | message appears on the crowd screen |
| edit text, click submit again | crowd text updates in place, no flash of the board |
| press Enter in the input | same as clicking submit |
| clear the input to empty | submit greys out again; message already on screen stays up |
| click the row's eye while shown | message hides (unchanged behaviour) |
| click the row's eye while hidden | message shows with the box's text (unchanged) |
| global eye-slash | hides (unchanged) |
| show a preset, then a custom | preset text not replaced by custom text (the falsy-chain fix) |
| reload the host mid-custom-message | box re-seeded, drawer editing open *(Phase 2)* |
| two host windows, submit in one | other window's box picks up the text if its draft is empty *(Phase 2)* |
| second window with an unsent draft | draft survives the other window's submit *(Phase 2)* |

## Commit sequence

1. **Add a submit button to the host's custom message box** — Phase 1: the
   form, the button, the `customIdx`/`customMid`/`canSubmit` computeds, the
   `toggleMessage` fallback fix, the `.form-edit` width.
2. **Persist the displayed message text across host reloads** — Phase 2: the
   `set_state("message-text", …)` line, the seeding watcher, the type additions.

Phase 2 is droppable on its own if only the button is wanted.

## Deferred

- **Multiline custom messages.** Needs `/message/show` to stop being
  `"<p>{0}</p>".format(text)`. Doing it properly means deciding whether host
  input is escaped — today it is not, so a host can deliberately type HTML, and
  escaping would take that away. Separate issue.
- **A screenshot refresh for `docs/images/host.png`.** The drawer gains a
  button, so the README screenshot drifts slightly. Not worth a re-shoot for
  one icon; worth folding into the next screenshot pass.
- `README.md` needs no change: the bottom drawer is described as "functions to
  display a custom message on the board", which stays true, and no command,
  port or default behaviour moves.

## Risks and notes

- **`State.name` is `db.String(10)`** ([model.py:145](ceopardy/model.py#L145))
  and `message-text` is 12 characters. Pre-existing and harmless: SQLite does
  not enforce `VARCHAR` lengths, and `container-footer` / `overlay-question`
  (16 each) have been stored through that column for as long as the drawers
  have existed. Not fixed here — widening the column is a schema change that
  wants its own commit.
- **Layout.** The box currently sits inside a `div.form-expand` in a flex
  column; wrapping it in a `<form>` inserts a non-flex element in that chain.
  Check the drawer both below and above the `min-width: 1230px` breakpoint
  ([main.css:781](frontend/src/styles/main.css#L781)), which bumps
  `.form-header` and `.form-text` to fixed pixel sizes, before committing.
- **`m.title === "Custom"` remains the way the custom entry is identified**,
  now in one computed instead of three inline tests. An operator who renames
  the entry in their config still loses the edit box — same as today, and
  changing the contract (a `custom: true` flag in `MESSAGES`) would break
  existing operator configs. Left alone deliberately.
