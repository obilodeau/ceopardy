# Spec Delta

## Purpose

Defines when buzzers are open, how a buzz takes effect, and which teams may
buzz on the current clue, so every host window, keyboard buzzer and web
buzzer agrees on one server-held lock in both offline and online mode.

## ADDED Requirements

### Requirement: The server owns the buzzer lock
The server SHALL hold whether buzzers are open as part of the game state. Every host window SHALL show the same lock, and the state SHALL survive a host reload. The state is broadcast to clients whenever it changes and is included in the full game state.

#### Scenario: Two host windows agree
- **WHEN** the host opens the buzzers from one host window
- **THEN** every other host window shows the buzzers as open

#### Scenario: Host reload
- **WHEN** the host reloads the host page while buzzers are open
- **THEN** the lock icon shows the buzzers as open

### Requirement: The host can open and close buzzers manually
The host's lock control SHALL open closed buzzers and close open ones. A request with an unknown action SHALL be rejected.

#### Scenario: Unlock
- **WHEN** buzzers are closed and the host clicks the lock icon
- **THEN** buzzers open

#### Scenario: Lock
- **WHEN** buzzers are open and the host clicks the lock icon
- **THEN** buzzers close

### Requirement: Selecting a question opens the buzzers
Selecting a regular question SHALL open the buzzers and clear the lock-out list, in both modes. Selecting a daily double SHALL close the buzzers and clear the lock-out list, since only the controlling team plays. Deselecting a question SHALL close the buzzers and clear the lock-out list.

#### Scenario: Regular question
- **WHEN** the host selects a question that is not a daily double
- **THEN** buzzers open and no team is locked out

#### Scenario: Daily double
- **WHEN** the host selects a daily double
- **THEN** buzzers stay closed and no team is locked out

#### Scenario: Deselect
- **WHEN** the host deselects the active question, including after submitting answers
- **THEN** buzzers close and no team is locked out

### Requirement: A keyboard buzz is judged by the server
A keypress on the host for team N (keys 1 to the number of teams) SHALL be sent to the server, which accepts it only while buzzers are open and the team is not locked out. Otherwise it is ignored. An unknown team SHALL be rejected.

#### Scenario: Buzz while open
- **WHEN** buzzers are open and the host machine receives key `2`
- **THEN** team 2 buzzes in

#### Scenario: Buzz while closed
- **WHEN** buzzers are closed and the host machine receives key `2`
- **THEN** nothing happens

#### Scenario: Two windows, one keypress
- **WHEN** two host windows each forward the same keypress
- **THEN** the buzz is awarded at most once

### Requirement: A keyboard buzz in offline mode is awarded at once
In offline mode, an accepted keyboard buzz SHALL be awarded immediately, without a collection window.

#### Scenario: Offline keypress
- **WHEN** buzzers are open in offline mode and key `1` is pressed
- **THEN** team 1 is awarded the buzz straight away

### Requirement: A keyboard buzz in online mode races web buzzers
In online mode, an accepted keyboard buzz SHALL enter the same race as web buzzes, judged on its arrival time, so keyboard and web buzzers can be mixed at one event.

#### Scenario: Hybrid event
- **WHEN** buzzers are open in online mode and key `3` is pressed while remote players also buzz
- **THEN** the winner is decided by the web buzzer race rules, with team 3 as one of the entrants

### Requirement: Awarding a buzz
When a buzz is awarded, the server SHALL select the winning team, close the buzzers, and play that team's buzzer sound. Every host window and the viewer SHALL see the team selected; the host's keypress handler does not select the team or play the sound itself.

#### Scenario: Buzz awarded
- **WHEN** team 1 is awarded a buzz
- **THEN** team 1 becomes the selected team, buzzers close, and team 1's buzzer sound plays

### Requirement: A team marked wrong is locked out for the clue
The server SHALL keep a list of teams locked out of the current clue. A buzz from a locked-out team SHALL be ignored, whether from a keyboard or a web page. The list SHALL be cleared when a question is selected or deselected.

#### Scenario: Locked-out keypress
- **WHEN** team 1 is locked out and key `1` is pressed while buzzers are open
- **THEN** nothing happens

#### Scenario: Next clue
- **WHEN** the host selects the next question
- **THEN** no team is locked out

### Requirement: Host sliders drive the lock-out
The lock-out list SHALL be the teams whose answer slider is on *Bad*. When a team is added to it, the buzzers SHALL re-open for the remaining teams. When a team is removed from it, only the list SHALL change and the buzzers SHALL NOT open.

#### Scenario: Rebound
- **WHEN** team 1 buzzed and the host moves team 1's slider to *Bad*
- **THEN** team 1 is locked out and buzzers open for the other teams

#### Scenario: Correcting a slider
- **WHEN** the host moves a locked-out team's slider back to *No Answer*
- **THEN** that team is no longer locked out and the buzzers do not open

#### Scenario: Other sliders
- **WHEN** some team is on *Bad* and the host changes another team's slider to *Good*
- **THEN** the buzzers do not re-open

### Requirement: Buzzers stay closed when every team is locked out
When every team is locked out, the server SHALL keep the buzzers closed, whatever the request asked for.

#### Scenario: All teams wrong
- **WHEN** the host marks the last remaining team *Bad*
- **THEN** buzzers stay closed

### Requirement: Lock-out requests are validated
The server SHALL reject a lock-out list that is not a list of known team ids. Duplicates SHALL be dropped and the order kept.

#### Scenario: Unknown team
- **WHEN** the host sends a lock-out list containing `team9` in a three-team game
- **THEN** the request is rejected and the lock-out is unchanged

### Requirement: A locked-out team's panel turns red
On the host, the scoring panel of every locked-out team SHALL turn red, following the server's list rather than the local slider, so every host window shows the same teams. The red SHALL take precedence over the selected-team frame. During a daily double no panel turns red.

#### Scenario: Missed team stays selected
- **WHEN** the selected team is marked *Bad*
- **THEN** its panel is red in every host window

#### Scenario: Daily double
- **WHEN** a daily double is active
- **THEN** no panel is red

### Requirement: Sliders survive a host reload mid-clue
When the host page loads or a new clue becomes active, each locked-out team's slider SHALL start on *Bad* and every other team's on *No Answer*, so a reload neither unlocks those teams nor loses the red panels.

#### Scenario: Reload mid-clue
- **WHEN** team 1 is locked out and the host reloads the host page
- **THEN** team 1's slider is on *Bad*, its panel is red, and it is still locked out
