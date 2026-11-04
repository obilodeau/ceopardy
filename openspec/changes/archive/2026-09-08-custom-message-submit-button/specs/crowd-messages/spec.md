# Spec Delta

## Purpose

Lets the host put a preset or custom message on the crowd screen over the
board, update it, and take it down again, from the host UI's message drawer.

## ADDED Requirements

### Requirement: Host toggles messages from the message list
The host UI SHALL list every configured message with a show/hide control. Activating it on a message that is not on screen SHALL show that message on the crowd screen; activating it on the message currently on screen SHALL hide it. A separate hide-all control SHALL hide whatever message is up.

#### Scenario: Show a message from its row
- **WHEN** no message is on screen and the host activates a preset's show control
- **THEN** the crowd screen shows that preset's text over the board

#### Scenario: Hide the message from its row
- **WHEN** a message is on screen and the host activates that message's control
- **THEN** the message is hidden and the crowd screen shows the board

#### Scenario: Hide all
- **WHEN** a message is on screen and the host activates the hide-all control
- **THEN** the message is hidden

### Requirement: Preset messages show their own text
A preset message SHALL always be shown with its own configured text, even when that text is empty. It MUST NOT take the text typed in the custom message box.

#### Scenario: Preset after custom text was typed
- **WHEN** the custom box holds text and the host shows a preset
- **THEN** the crowd screen shows the preset's configured text, not the custom text

### Requirement: Custom message box
When the configuration has a message titled `Custom`, its row SHALL offer an edit control that opens and closes a single-line text box for the custom message. Opening the box SHALL place the keyboard focus in it. When no such message is configured, no box SHALL be offered.

#### Scenario: Open the box
- **WHEN** the host activates the edit control on the custom row
- **THEN** the text box appears with keyboard focus

#### Scenario: Close the box
- **WHEN** the box is open and the host activates the edit control again
- **THEN** the box closes

#### Scenario: No custom entry configured
- **WHEN** the operator's message configuration has no entry titled `Custom`
- **THEN** no row offers an edit control and no box is shown

### Requirement: Submit shows the custom message
The custom box SHALL have a submit button, and pressing Enter in the box SHALL do the same. Submitting SHALL show the box's text, with surrounding whitespace trimmed, as the custom message on the crowd screen. Submit MUST always show and never hide: when the custom message is already up, submitting SHALL replace its text in place without hiding it first.

#### Scenario: Submit with the custom message off
- **WHEN** the host types text and clicks submit
- **THEN** the crowd screen shows that text

#### Scenario: Update a live custom message
- **WHEN** the custom message is on screen and the host edits the text and clicks submit
- **THEN** the crowd screen text updates in place, without the board showing in between

#### Scenario: Enter submits
- **WHEN** the host presses Enter in the box
- **THEN** the result is the same as clicking submit

#### Scenario: Show the custom message from its row
- **WHEN** the custom message is not on screen, the box holds text, and the host activates the custom row's show control
- **THEN** the crowd screen shows the box's text

### Requirement: An empty custom message cannot be shown
Submit SHALL be visibly disabled and inert while the custom box is empty or holds only whitespace. Showing the custom message from its row with an empty box SHALL do nothing. Emptying the box MUST NOT hide a message already on screen.

#### Scenario: Empty box
- **WHEN** the box is empty and the host clicks submit
- **THEN** the button appears disabled and nothing changes on the crowd screen

#### Scenario: Row show control with an empty box
- **WHEN** the custom message is not on screen, the box is empty, and the host activates the custom row's show control
- **THEN** nothing is shown

#### Scenario: Clear the box while the message is up
- **WHEN** the custom message is on screen and the host clears the box
- **THEN** submit becomes disabled and the message stays on screen

### Requirement: Custom message survives a host reload
The server SHALL keep the text of the message last shown. When the host UI loads while the custom message is on screen, it SHALL open the custom box and fill it with that text. This SHALL only ever open the box, and it MUST NOT overwrite text the host has already typed in it. Hiding a message MUST NOT clear the host's draft.

#### Scenario: Reload mid-message
- **WHEN** the custom message is on screen and the host reloads the host page
- **THEN** the custom box is open and holds the text on screen

#### Scenario: Draft kept when another window submits
- **WHEN** two host windows are open, one has an unsent draft in its box, and the other submits a custom message
- **THEN** the draft in the first window is unchanged

#### Scenario: Draft kept across a hide
- **WHEN** the box holds text and the host hides the custom message
- **THEN** the box still holds the same text
