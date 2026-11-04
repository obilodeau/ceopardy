# Tasks

## 1. Submit button for the custom message box

- [x] 1.1 Identify the custom entry once (index of the `Custom` title, -1 when absent) and derive its message id, replacing the repeated title tests and inline id literals; verify the pencil still shows only on the `Custom` row
- [x] 1.2 Replace the `contenteditable` div with a form: single-line input bound to the custom text, paper-plane submit button, hidden submit input for Enter; verify typing and clicking submit, or pressing Enter, shows the text on the crowd screen
- [x] 1.3 Make submit show-only (trimmed text, no hide branch) and disable it with the existing `.disabled` class while the trimmed text is empty; verify an empty box shows nothing and a live message updates in place with one click
- [x] 1.4 Route the custom row's eye icon through the submit path and make presets use their own body, removing the falsy fallback chain; verify a preset after typed custom text shows the preset's text
- [x] 1.5 Focus the input when the pencil opens the box, and open the box when the custom message is the one on screen; verify by clicking the pencil and by showing the custom message
- [x] 1.6 Give `.form-edit` an explicit width with `border-box` and drop the `[contenteditable='true']` qualifier from its focus glow; verify the box fills the column and glows on focus
- [x] 1.7 Run `make ci` and verify it passes

## 2. Keep the custom text across a host reload

- [x] 2.1 Store the raw text as a `message-text` state row in `/message/show`, leaving `/message/hide` untouched; verify the row is in the full-state payload after a show
- [x] 2.2 Add `message-text` to `UiState` and the store's initial `ui_state`; verify `make frontend-type-check` passes
- [x] 2.3 Extend the drawer's watcher to fill the box from `message-text` when the custom message is live and the box is empty; verify a host reload mid-message reopens and refills the box, and an unsent draft in a second window survives a submit from the first
- [x] 2.4 Run `make ci` and verify it passes

## 3. Cleanup

- [x] 3.1 Trim comments in the drawer, route and CSS back to the why, per `AGENTS.md`; verify `make ci` still passes
